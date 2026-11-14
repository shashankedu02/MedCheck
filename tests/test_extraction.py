"""Field-extraction tests (milestone M4). Pure text: no OCR involved."""
from __future__ import annotations

import pytest

from medcheck.dataset import load_dataset
from medcheck.extraction import PassFields, extract_from_lines, reconcile_batch, reconcile_date
from medcheck.models import FieldState
from medcheck.normalization import batch_key


@pytest.mark.parametrize("line,expected", [
    ("B.No.: TG261185  Mfg: 05/2026", "TG261185"),
    ("Batch No. TG261185 Exp 04/2028", "TG261185"),
    ("BATCH NO: ABC123", "ABC123"),
    ("B. No. 25010040", "25010040"),
    ("Batch Number : 0l25038", "0l25038"),
    ("LOT: A1B2C3", "A1B2C3"),
    ("Lot No XY-7788", "XY-7788"),
    ("B.NO.GTF2327C,", "GTF2327C,"),
    ("Batch BKBP O2601 Mfg 05/2026", "BKBP O2601"),
])
def test_batch_label_formats(line, expected):
    assert extract_from_lines([line]).batch_candidates == (expected,)


def test_label_alone_takes_value_from_next_line():
    assert extract_from_lines(["Batch No.", "TG261185"]).batch_candidates == ("TG261185",)


def test_raw_value_preserved_not_corrected():
    (raw,) = extract_from_lines(["B.No. 0l25038"]).batch_candidates
    assert raw == "0l25038"  # lowercase L kept; never mapped to 1 or I


def test_no_label_means_no_batch():
    assert extract_from_lines(["Paracetamol Tablets IP 500 mg", "TG261185"]).batch_candidates == ()


def test_implausible_values_rejected():
    for line in ("Batch No. -", "B.No. ab", "Batch No: PARACETAMOL", "Batch No. 12"):
        assert extract_from_lines([line]).batch_candidates == (), line


@pytest.mark.parametrize("line,exp,mfg", [
    ("Mfg: 05/2026 Exp: 04/2028", "04/2028", "05/2026"),
    ("MFD. 05-26  EXP. 04-28", "04-28", "05-26"),
    ("Mfg Date: MAY 2026  Expiry Date: APR 2028", "APR 2028", "MAY 2026"),
    ("EXP 2028-04", "2028-04", None),
    ("Use before 04/2028", "04/2028", None),
])
def test_date_labels(line, exp, mfg):
    f = extract_from_lines([line])
    assert (f.expiry_candidates[0] if f.expiry_candidates else None) == exp
    assert (f.mfg_candidates[0] if f.mfg_candidates else None) == mfg


def test_manufactured_by_is_not_a_date():
    f = extract_from_lines(["Mfd. by: Hind Pharma, Bhopal"])
    assert f.mfg_candidates == () and f.expiry_candidates == ()


def test_exp_and_mfg_not_swapped():
    f = extract_from_lines(["Exp 04/2028", "Mfg 05/2026"])
    assert f.expiry_candidates == ("04/2028",) and f.mfg_candidates == ("05/2026",)


# ---- reconciliation ----
def pf(*batches):
    return PassFields(tuple(batches), (), ())


def test_agreeing_passes_are_read():
    r = reconcile_batch([pf("TG261185"), pf("TG-261185"), pf()])
    assert r.state is FieldState.READ and r.key.key == "TG261185"


def test_disagreeing_passes_are_ambiguous_and_never_pick_a_winner():
    r = reconcile_batch([pf("TG261185"), pf("TG261185"), pf("TG26118S")])
    assert r.state is FieldState.AMBIGUOUS and r.key is None and "TG26118S" in r.readings


def test_confusable_disagreement_is_ambiguous():
    assert reconcile_batch([pf("BKBP02601"), pf("BKBPO2601")]).state is FieldState.AMBIGUOUS


def test_single_pass_is_not_enough_by_default():
    assert reconcile_batch([pf("TG261185"), pf(), pf()]).state is FieldState.AMBIGUOUS
    assert reconcile_batch([pf("TG261185")], min_agree=1).state is FieldState.READ


def test_two_batches_on_one_pass_are_ambiguous():
    assert reconcile_batch([pf("TG261185", "AB123456"), pf("TG261185", "AB123456")]).state is FieldState.AMBIGUOUS


def test_nothing_found():
    assert reconcile_batch([pf(), pf()]).state is FieldState.NOT_FOUND


def test_date_reconciliation():
    assert reconcile_date([("04/2028",), ("04-2028",)]).state is FieldState.READ
    assert reconcile_date([("04/2028",), ("05/2028",)]).state is FieldState.AMBIGUOUS
    assert reconcile_date([(), ()]).state is FieldState.NOT_FOUND


# ---- dataset-wide: every real batch format survives a "Batch No." line ----
def test_every_dataset_batch_round_trips_through_extraction():
    failures = []
    for r in load_dataset().records:
        (got,) = extract_from_lines([f"Batch No. {r.batch_number}  Mfg {r.manufacturing_date}"]).batch_candidates or (None,)
        if got is None or batch_key(got).key != batch_key(r.batch_number).key:
            failures.append((r.serial, r.batch_number, got))
    # Known, deliberate limitation: 2-character batches (serials 24 '49' and 26 '38') are below
    # MIN_BATCH_KEY_LENGTH, so they are never extracted and always end as "Unable to verify".
    assert [f[0] for f in failures] == [24, 26], failures
    assert all(len(batch_key(f[1]).key) < 3 for f in failures)
