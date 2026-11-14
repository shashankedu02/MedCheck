"""V2 parser and the known-bad RapidOCR readings from docs/OCR_INVESTIGATION.md.

Pure text/matching tests (no OCR engine). The central safety property: a wrong batch reading must never
turn into "No alert found" when the true batch is on the list; it must abstain.
"""
from __future__ import annotations

import pytest

from medcheck.dataset import Dataset, DatasetRecord
from medcheck.decision import decide
from medcheck.extraction import PassFields, extract, extract_from_lines, reconcile_batch
from medcheck.matching import DatasetIndex, match_batch
from medcheck.models import ExpiryAssessment, ExpiryOutcome, FieldState, MatchOutcome, Status
from medcheck.normalization import batch_key
from medcheck.ocr import OCRPass


# ---- glue-aware parsing: RapidOCR drops spaces, so the next label is glued to the value ----
@pytest.mark.parametrize("line,expected", [
    ("B.NO.HLAS0019MFG.JUL.2025 EXP.JUN.2028", "HLAS0019"),
    ("B.NO.5BA1617MFD", "5BA1617"),
    ("BNO.5BA1447MFD.JUN25EXPMAY27", "5BA1447"),
    ("B.NO.:25S3GCA146M.R", "25S3GCA146"),
    ("B.NO.:25S3GCA146M.R.P.RS.:252.00", "25S3GCA146"),
    ("B.NO.CP50097 MFD", "CP50097"),
    ("B.NO.18261604A8PERBLISTER", "18261604A8"),  # the extra 8 is an OCR misread; see misread tests below
    ("B.NO.BEC1106", "BEC1106"),
    ("B.No.TG261185  Mfg 05/2026", "TG261185"),
])
def test_glued_labels_are_cut_not_kept(line, expected):
    assert extract_from_lines([line]).batch_candidates == (expected,)


@pytest.mark.parametrize("line", [
    "B.NO.MFG.04-2026",        # only a label follows
    "B.NO.EXP.03-2028",
    "B.NO.MFD",
    "B.No.:",
    "MFG.04-2026 EXP.03-2028",  # no batch label at all
    "B.NO.PER BLISTER",
])
def test_label_words_are_never_taken_as_a_batch(line):
    assert extract_from_lines([line]).batch_candidates == ()


def test_value_on_the_next_line_is_supported_and_glue_is_cut_there_too():
    assert extract_from_lines(["B.No.", "SIN552"]).batch_candidates == ("SIN552",)
    assert extract_from_lines(["B.No.", "5BA1617MFD"]).batch_candidates == ("5BA1617",)


def test_glued_dates_are_found():
    pf = extract_from_lines(["B.NO.HLAS0019MFG.JUL.2025 EXP.JUN.2028"])
    assert pf.mfg_candidates == ("JUL.2025",) and pf.expiry_candidates == ("JUN.2028",)


def test_raw_strings_stay_raw():
    (raw,) = extract_from_lines(["B.No. 0l25038"]).batch_candidates
    assert raw == "0l25038"  # never mapped to 0125038 / OI25038
    (raw,) = extract_from_lines(["B.NO.GTF2327C,"]).batch_candidates
    assert raw == "GTF2327C,"


# ---- known wrong readings (true batch -> what the engine actually returned) ----
TRUE_BATCHES = ["HLAS0019", "5BA1617", "BEC1106", "5BA1447", "25S3GCA146", "CP50097", "18261604A", "INA26003"]
KNOWN_WRONG = [
    ("HLAS0019", "HLAS50019"),
    ("5BA1447", "5BA13A7"),
    ("5BA1447", "5BA1A7"),
    ("5BA1447", "5BA1AA7"),
    ("INA26003", "INA26083"),
    ("18261604A", "18261604K8"),
    ("18261604A", "18261604A8"),
]


def _dataset() -> Dataset:
    recs = tuple(
        DatasetRecord(i + 1, f"Testol {i} Tablets IP 10 mg", b, "01/2025", "01/2028", "Test Pharma Ltd", "NSQ",
                      "Test", "Lab", "AUG-2026")
        for i, b in enumerate(TRUE_BATCHES)
    )
    return Dataset(recs, "AUG-2026", "test", "0" * 64, {})


@pytest.fixture(scope="module")
def index():
    return DatasetIndex.build(_dataset())


@pytest.mark.parametrize("true,wrong", KNOWN_WRONG)
def test_known_misread_of_a_listed_batch_abstains_never_no_alert(index, true, wrong):
    m = match_batch(index, batch_key(wrong), "Testol Tablets IP")
    assert m.outcome is not MatchOutcome.NO_MATCH, (true, wrong, m)
    assert m.outcome is not MatchOutcome.CONFIRMED  # a similar batch is never proof
    d = decide(system_failure=None, batch_state=FieldState.READ, match=m,
               expiry=ExpiryAssessment(ExpiryOutcome.NOT_READ), dataset_period="AUG-2026")
    assert d.status is Status.UNABLE_TO_VERIFY


def test_exact_true_batches_still_resolve(index):
    for b in TRUE_BATCHES:
        m = match_batch(index, batch_key(b), "")
        assert m.outcome is MatchOutcome.UNCORROBORATED  # exact, but no product text: never an alert on batch alone


# ---- strict agreement across passes ----
def _pf(src, *cands):
    return PassFields(tuple(cands), (), (), src)


def test_conflicting_readings_across_engines_are_ambiguous_and_keep_provenance():
    b = reconcile_batch([_pf("rapidocr:full_rot0", "HLAS50019"), _pf("rapidocr:crop_rot0", "HLAS0019")])
    assert b.state is FieldState.AMBIGUOUS and b.key is None
    assert ("HLAS50019", "rapidocr:full_rot0") in b.reading_sources and ("HLAS0019", "rapidocr:crop_rot0") in b.reading_sources


def test_single_pass_is_not_enough_and_two_agreeing_passes_are():
    assert reconcile_batch([_pf("rapidocr:full_rot0", "BEC1106")]).state is FieldState.AMBIGUOUS
    b = reconcile_batch([_pf("rapidocr:full_rot0", "BEC1106"), _pf("tesseract:gray", "BEC1106")])
    assert b.state is FieldState.READ and b.raw == "BEC1106"
    assert {s for _r, s in b.reading_sources} == {"rapidocr:full_rot0", "tesseract:gray"}


def test_a_tesseract_misread_conflicts_with_rapidocr_instead_of_being_outvoted():
    b = reconcile_batch([_pf("rapidocr:full_rot0", "BEC1106"), _pf("rapidocr:crop_rot0", "BEC1106"), _pf("tesseract:clahe", "BEC11O6")])
    assert b.state is FieldState.AMBIGUOUS  # O/0: different keys, never silently merged


def test_extract_records_engines_and_sources():
    passes = [OCRPass("full_rot0", 0, ("B.NO.BEC1106 MFG.04-2026",), (), engine="rapidocr", source="full_rot0"),
              OCRPass("crop_rot0", 0, ("B.NO.BEC1106",), (), engine="rapidocr", source="crop_rot0"),
              OCRPass("gray", 6, ("B.No.BEC1106",), ())]
    ex = extract(passes)
    assert ex.engines == ("rapidocr", "tesseract")
    assert ex.batch.state is FieldState.READ and len(ex.batch.reading_sources) >= 3
    assert any(s == "tesseract:gray" for _r, s in ex.batch.reading_sources)


def test_engine_scores_are_never_read_by_extraction_matching_decision_or_pipeline():
    """OCR confidence is not proof of identity: no decision-path module may touch word confidence."""
    import inspect
    import re

    import medcheck.decision as d
    import medcheck.extraction as e
    import medcheck.matching as m
    import medcheck.pipeline as p
    for mod in (d, e, m, p):
        assert not re.search(r"\.confidence|score_cutoff.*confidence", inspect.getsource(mod)), mod.__name__


def test_old_glued_form_cannot_reach_matching():
    # the 20-character glued reading that the old extractor produced is cut by the parser
    (raw,) = extract_from_lines(["B.NO.18261604A8PERBLISTER"]).batch_candidates
    assert batch_key(raw).key == "18261604A8"


# ---- guards found by the first real-photo run (T023: "30 deg C. Protect", T019: block cut by the frame) ----
@pytest.mark.parametrize("line", [
    "Trade Mark of the B.NO. 30°C.Protect",     # sentence fragment after a stray label
    "B.NO. 30�C.Protect from light",            # OCR replacement character
    "B.No.: Sitagliptin Phosphate Monohydrate",       # words, no batch
    "Batch No. Protected1",                           # 9-letter run: a word, not a batch
    "B.No.: AB12éCD",                            # character never seen in a listed batch
])
def test_sentence_fragments_and_garbage_are_not_batches(line):
    assert extract_from_lines([line]).batch_candidates == ()


def test_real_looking_batches_with_up_to_five_letters_still_pass():
    for line, want in [("B.No.: ABCDE1234", "ABCDE1234"), ("B.No.: BKBP O2601", "BKBP O2601"), ("B.No. 0l25038", "0l25038")]:
        assert extract_from_lines([line]).batch_candidates == (want,)


def test_every_listed_batch_passes_the_guards():
    from medcheck.dataset import load_dataset

    for r in load_dataset().records:
        if len(batch_key(r.batch_number).key) >= 3:
            assert extract_from_lines([f"B.No.: {r.batch_number}"]).batch_candidates, r.serial


def test_a_line_touching_the_image_edge_is_not_used_as_a_batch():
    cut = OCRPass("v", 0, ("B.No.: SIH1166A", "Sitagliptin tablets"), (), engine="rapidocr", source="crop_rot90", edge_lines=(0,))
    ok = OCRPass("v", 0, ("B.No.: SIH1166A", "Sitagliptin tablets"), (), engine="rapidocr", source="crop_rot0")
    ex = extract([cut, cut])
    assert ex.batch.state is FieldState.NOT_FOUND and "cut off" in ex.batch.reason
    assert ex.edge_ignored == ("SIH1166A",) and "Sitagliptin" in ex.product_text  # still usable as product text
    assert extract([ok, ok]).batch.state is FieldState.READ  # same text away from the edge is fine
    one_cut = extract([cut, ok])
    assert one_cut.batch.state is FieldState.AMBIGUOUS  # a single uncut pass is not enough
