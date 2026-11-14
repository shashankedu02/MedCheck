"""V2 pipeline: RapidOCR-first cascade, provenance, strict agreement, misread safety, offline operation.

A scripted stub engine replaces RapidOCR so cascade rules are tested deterministically; one test runs
the real RapidOCR with all network access blocked. Images are synthetic (plain white) and prove behaviour
only; they are not an accuracy evaluation.
"""
from __future__ import annotations

import socket

import pytest
from PIL import Image

from medcheck.models import FieldState, Status, SystemFailure
from medcheck.ocr import OCREngineUnavailable, OCRPass
from medcheck.pipeline import MedCheckPipeline
from tests.helpers import encode
from tests.test_v2_parser_and_misreads import _dataset

PHOTO = encode(Image.new("RGB", (500, 400), "white"), "PNG")  # plain: no pack region is detected
ZX = "B.No.: ZX99001Q"  # a batch that is not in the dataset


class StubRapid:
    version = "stub-rapid 0"

    def __init__(self, script):
        self.script, self.calls = script, []

    def run(self, rgb, source):
        self.calls.append(source)
        lines = self.script(source) if callable(self.script) else self.script.get(source, ())
        return OCRPass(source, 0, tuple(lines), (), engine="rapidocr", source=source)


def pipe_with(script, dataset=None):
    stub = StubRapid(script)
    if dataset is None:
        return MedCheckPipeline.load(rapid_engine=stub, tesseract_engine=None), stub
    return MedCheckPipeline(dataset, rapid_engine=stub, tesseract_engine=None), stub


V1, V2 = "full_rot0", "full_x1.3"


def test_two_agreeing_views_give_a_result_with_provenance_and_the_batch_checked():
    p, stub = pipe_with({V1: [ZX, "Paracetamol Tablets IP 500 mg"], V2: [ZX]})
    r = p.check(PHOTO)
    assert stub.calls == [V1, V2]  # no rotation retries when a batch was found
    assert r.decision.status is Status.NO_ALERT_FOUND
    assert "Batch checked: ZX99001Q" in r.decision.explanation and r.decision.batch_as_read == "ZX99001Q"
    assert r.engines == ("rapidocr",) and r.engine_version == "stub-rapid 0"
    assert {"rapidocr:full_rot0", "rapidocr:full_x1.3"} <= set(r.variants_used)
    assert {s for _r, s in r.extraction.batch.reading_sources} == {"rapidocr:full_rot0", "rapidocr:full_x1.3"}


def test_rotations_are_tried_only_when_no_batch_label_was_found():
    p, stub = pipe_with({"full_rot180": [ZX], "full_rot180_x1.3": [ZX]})
    r = p.check(PHOTO)
    assert stub.calls == [V1, V2, "full_rot90", "full_rot180", "full_rot270", "full_rot180_x1.3"]
    assert r.extraction.batch.state is FieldState.READ
    assert {s for _r, s in r.extraction.batch.reading_sources} == {"rapidocr:full_rot180", "rapidocr:full_rot180_x1.3"}


def test_a_batch_read_in_one_rotation_only_is_not_enough():
    p, stub = pipe_with({"full_rot180": [ZX]})  # the confirmation pass finds nothing
    r = p.check(PHOTO)
    assert r.extraction.batch.state is FieldState.AMBIGUOUS
    assert r.decision.status is Status.UNABLE_TO_VERIFY and "batch_ambiguous" == r.decision.reason_code


def test_no_rotation_retry_when_readings_conflict():
    p, stub = pipe_with({V1: ["B.No.: HLAS0019"], V2: ["B.No.: HLAS50019"]})
    r = p.check(PHOTO)
    assert stub.calls == [V1, V2]  # ambiguity is never "retried until it agrees", and there is no confirm pass
    assert r.extraction.batch.state is FieldState.AMBIGUOUS and r.decision.status is Status.UNABLE_TO_VERIFY


def test_confirmation_pass_is_single_and_a_disagreeing_confirmation_stays_ambiguous():
    p, stub = pipe_with({V1: ["B.No.: HLAS0019"], "full_rot0_x1.3": ["B.No.: HLAS50019"]})
    r = p.check(PHOTO)
    assert stub.calls == [V1, V2, "full_rot0_x1.3"]  # exactly one extra pass
    assert r.extraction.batch.state is FieldState.AMBIGUOUS and r.decision.status is Status.UNABLE_TO_VERIFY


def test_confirmation_pass_that_agrees_gives_a_read():
    p, _ = pipe_with({V1: [ZX], "full_rot0_x1.3": [ZX]})
    assert p.check(PHOTO).extraction.batch.state is FieldState.READ


# ---- the investigation's wrong readings, end to end, against a dataset that lists the true batch ----
@pytest.mark.parametrize("wrong", ["HLAS50019", "INA26083", "5BA13A7", "18261604K8"])
def test_consistent_misread_of_a_listed_batch_never_yields_no_alert_found(wrong):
    p, _ = pipe_with({V1: [f"B.No.: {wrong}"], V2: [f"B.No.: {wrong}"]}, _dataset())
    r = p.check(PHOTO)
    assert r.extraction.batch.state is FieldState.READ  # both passes agreed on the (wrong) value
    assert r.decision.status is Status.UNABLE_TO_VERIFY and r.decision.reason_code == "fuzzy_candidate_only"


def test_conflicting_readings_never_yield_no_alert_found_even_if_neither_is_listed():
    p, _ = pipe_with({V1: ["B.No.: QQ12345"], V2: ["B.No.: QQ12385"]})
    assert p.check(PHOTO).decision.status is Status.UNABLE_TO_VERIFY


def test_batch_never_read_is_never_no_alert():
    p, _ = pipe_with({})
    r = p.check(PHOTO)
    assert r.decision.status is Status.UNABLE_TO_VERIFY and r.decision.reason_code == "batch_not_found"
    assert r.ocr_passes == 5  # two views + three rotation retries


# ---- engine availability is a system matter, not a verification status ----
class BrokenRapid(StubRapid):
    def run(self, rgb, source):
        raise OCREngineUnavailable("x")


def test_rapidocr_failure_with_no_tesseract_is_a_system_error():
    p = MedCheckPipeline.load(rapid_engine=BrokenRapid({}), tesseract_engine=None)
    r = p.check(PHOTO)
    assert r.decision.system_failure is SystemFailure.OCR_ENGINE_UNAVAILABLE and r.decision.status is None


def test_rapidocr_failure_falls_back_to_tesseract_and_says_so():
    from medcheck.ocr import find_engine

    try:
        find_engine()
    except OCREngineUnavailable:
        pytest.skip("Tesseract not installed")
    p = MedCheckPipeline.load(rapid_engine=BrokenRapid({}))
    r = p.check(PHOTO)
    assert any("RapidOCR engine is unavailable" in n for n in r.notes)
    assert r.decision is not None and r.engines == ("tesseract",)


# ---- real engine, network blocked ----
def test_real_rapidocr_runs_offline(monkeypatch):
    from medcheck.ocr_rapid import RapidEngine
    from tests.helpers import font_path, render_label

    if font_path() is None:
        pytest.skip("no TrueType font")

    def no_network(*a, **k):
        raise AssertionError("network access attempted")

    monkeypatch.setattr(socket.socket, "connect", no_network)
    monkeypatch.setattr(socket, "getaddrinfo", no_network)
    import numpy as np

    img = render_label(["Paracetamol Tablets IP 500 mg", "B.No.: ZX99001Q   Mfg: 01/2026", "Exp: 12/2028"])
    out = RapidEngine().run(np.asarray(img), "full_rot0")
    assert out.engine == "rapidocr" and out.pass_id == "rapidocr:full_rot0"
    text = " ".join(out.lines).upper().replace(" ", "")
    assert "ZX99001Q" in text and all(0 <= w.confidence <= 100 for w in out.words)


# ---- model integrity (supply chain): fail closed ----
def test_packaged_models_match_their_pinned_hashes():
    from medcheck.ocr_rapid import verify_models

    verify_models()  # raises if a model file is missing or altered


def test_a_tampered_or_missing_model_makes_rapidocr_unavailable(tmp_path):
    from medcheck import config
    from medcheck.ocr_rapid import RapidEngine, verify_models

    for name in config.RAPIDOCR_MODEL_SHA256:
        (tmp_path / name).write_bytes(b"not the real model")
    with pytest.raises(OCREngineUnavailable):
        verify_models(tmp_path)
    with pytest.raises(OCREngineUnavailable):
        verify_models(tmp_path / "does-not-exist")
    eng = RapidEngine()
    import medcheck.ocr_rapid as mod

    orig = mod.verify_models
    mod.verify_models = lambda *a, **k: orig(tmp_path)
    try:
        with pytest.raises(OCREngineUnavailable):
            eng.check_available()
    finally:
        mod.verify_models = orig


# ---- edge detection in the real adapter and end to end ----
def test_rapid_adapter_flags_lines_touching_the_edge():
    import numpy as np

    from medcheck.ocr_rapid import RapidEngine
    from tests.helpers import font_path
    from PIL import ImageDraw, ImageFont

    if font_path() is None:
        pytest.skip("no TrueType font")
    font = ImageFont.truetype(font_path(), 46)
    img = Image.new("RGB", (1300, 400), "white")
    d = ImageDraw.Draw(img)
    d.text((300, 150), "B.No.: ZX99001Q", fill="black", font=font)   # well inside
    d.text((2, 330), "Paracetamol tablets IP", fill="black", font=font)  # hugging the left/bottom edge
    out = RapidEngine().run(np.asarray(img), "full_rot0")
    inside = [i for i, ln in enumerate(out.lines) if "ZX99001Q" in ln.replace(" ", "")]
    assert inside and not set(inside) & set(out.edge_lines)
    assert out.edge_lines  # the edge-hugging line is flagged


class EdgeStub(StubRapid):
    """Reports every line as touching the edge (batch cut off by the frame)."""

    def run(self, rgb, source):
        out = super().run(rgb, source)
        return OCRPass(out.variant_id, out.psm, out.lines, out.words, engine=out.engine, source=out.source,
                       edge_lines=tuple(range(len(out.lines))))


def test_cut_off_batch_never_gives_no_alert_found_end_to_end():
    stub = EdgeStub({V1: ["B.No.: SIH1166A"], V2: ["B.No.: SIH1166A"]})
    r = MedCheckPipeline.load(rapid_engine=stub, tesseract_engine=None).check(PHOTO)
    assert r.decision.status is Status.UNABLE_TO_VERIFY and r.decision.reason_code == "batch_not_found"
    assert r.extraction.edge_ignored == ("SIH1166A",)
