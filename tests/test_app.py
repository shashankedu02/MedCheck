"""Streamlit UI tests using the headless AppTest harness (milestone M5).

AppTest cannot attach a file, so results are injected through session state; the pipeline itself is
covered end to end in test_pipeline.py.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from medcheck.decision import decide, system_error_decision
from medcheck.extraction import BatchField, DateField, ExtractionResult
from medcheck.image_input import ImageRejected
from medcheck.dataset import load_dataset
from medcheck.models import (
    ExpiryAssessment, ExpiryOutcome, FieldState, MatchAssessment, MatchOutcome, Status, SystemFailure,
)
from medcheck.normalization import batch_key
from medcheck.pipeline import ScanResult

APP = str(Path(__file__).resolve().parent.parent / "app.py")
RECORD = next(r for r in load_dataset().records if r.serial == 4)

ALLOWED_NEGATIONS = (
    "does not mean the medicine is safe, genuine or free of quality problems",
    "does not test medicine quality or authenticity",
    "not an authenticity or safety test",
)
BANNED = re.compile(r"\b(safe|genuine|authentic\w*|counterfeit|fake|guarantee\w*|free (of|from) defects)\b", re.I)


def extraction(batch_state=FieldState.READ):
    bk = batch_key("TG261185")
    b = BatchField(batch_state, "TG261185", bk) if batch_state is FieldState.READ else BatchField(batch_state, None, None, "reason text", ("AB123", "AB124"))
    return ExtractionResult(b, DateField(FieldState.READ, "04/2028"), DateField(FieldState.NOT_FOUND), "Linzotal 600\nB.No. TG261185", 8)


def result_for(outcome, batch_state=FieldState.READ, serial=None, record=None):
    match = None if batch_state is not FieldState.READ else MatchAssessment(outcome, "t", matched_serial=serial, evidence=("Evidence line.",))
    exp = ExpiryAssessment(ExpiryOutcome.UNDETERMINED, "04/2028", "Printed expiry reads 04/2028. Policy not approved.")
    d = decide(system_failure=None, batch_state=batch_state, match=match, expiry=exp, dataset_period="AUG-2026")
    return ScanResult(decision=d, extraction=extraction(batch_state), match=match, matched_record=record, expiry=exp,
                      engine_version="tesseract 5.5.3", variants_used=("gray",), ocr_passes=8)


def run_with(result):
    at = AppTest.from_file(APP, default_timeout=30)
    at.session_state["result"] = result
    at.session_state["result_digest"] = None
    at.run()
    assert not at.exception, [e.value for e in at.exception]
    return at


def all_text(at):
    parts = []
    for coll in (at.title, at.markdown, at.caption, at.text, at.info, at.warning, at.error, at.subheader, at.header, at.success):
        parts += [e.value for e in coll]
    return "\n".join(parts)


def test_default_page_states_scope_and_period():
    at = AppTest.from_file(APP, default_timeout=30).run()
    assert not at.exception
    text = all_text(at)
    assert "AUG-2026" in text and "not an authenticity or safety test" in text
    assert any("Photos are processed in memory" in c.value for c in at.caption)
    assert len(at.tabs) == 2 and len(at.file_uploader) == 1 and len(at.camera_input) == 1
    assert not at.success  # never a green "all good" element


def test_alert_found_rendering_shows_matched_record():
    at = run_with(result_for(MatchOutcome.CONFIRMED, serial=4, record=RECORD))
    assert at.error and "Alert found" in at.error[0].value
    text = all_text(at)
    assert "TG261185" in text and "Serial: 4" in text and "NSQ result:" in text and "AUG-2026" in text


def test_no_alert_is_neutral_not_green_and_has_disclaimer():
    at = run_with(result_for(MatchOutcome.NO_MATCH))
    assert at.info and any("No alert found" in i.value for i in at.info)
    assert not at.success and not at.error
    text = all_text(at)
    assert "does not mean the medicine is safe, genuine or free of quality problems" in text and "AUG-2026" in text


@pytest.mark.parametrize("outcome", [MatchOutcome.COLLISION, MatchOutcome.UNCORROBORATED, MatchOutcome.CONFLICT, MatchOutcome.FUZZY_ONLY])
def test_unable_to_verify_explains_and_suggests_next_step(outcome):
    at = run_with(result_for(outcome, serial=None))
    assert at.warning and "Unable to verify" in at.warning[0].value
    assert "pharmacist" in all_text(at)


def test_unreadable_batch_shows_readings_and_unable():
    at = run_with(result_for(None, batch_state=FieldState.AMBIGUOUS))
    assert "Unable to verify" in at.warning[0].value
    assert "AB123 | AB124" in all_text(at)


def test_system_error_is_distinct_and_never_a_status():
    for failure in SystemFailure:
        at = run_with(ScanResult(decision=system_error_decision(failure)))
        assert at.error and "System error" in at.error[0].value
        assert "not a 'No alert found' result" in at.error[0].value
        assert not any("No alert found" in w.value for w in at.warning) and not at.info[1:]


def test_rejected_upload_message_is_shown():
    at = run_with(ScanResult(rejection=ImageRejected("not_an_image", "The file could not be read as an image. It may be corrupt.")))
    assert at.error and "could not be used" in at.error[0].value


@pytest.mark.parametrize("make", [
    lambda: result_for(MatchOutcome.CONFIRMED, serial=4, record=RECORD),
    lambda: result_for(MatchOutcome.NO_MATCH),
    lambda: result_for(MatchOutcome.COLLISION),
    lambda: result_for(None, batch_state=FieldState.NOT_FOUND),
    lambda: ScanResult(decision=system_error_decision(SystemFailure.DATASET_INTEGRITY)),
])
def test_no_forbidden_claims_anywhere_on_page(make):
    text = all_text(run_with(make()))
    for ok in ALLOWED_NEGATIONS:
        text = text.replace(ok, "")
    assert not BANNED.search(text), BANNED.search(text).group(0)


def test_ocr_text_is_rendered_as_plain_text_not_markup():
    r = result_for(MatchOutcome.NO_MATCH)
    nasty = ExtractionResult(r.extraction.batch, r.extraction.expiry, r.extraction.manufacturing, "<script>alert(1)</script> **bold** [x](http://evil)", 8)
    at = run_with(ScanResult(decision=r.decision, extraction=nasty, match=r.match, expiry=r.expiry, engine_version="t", variants_used=("gray",), ocr_passes=1))
    assert any("<script>" in t.value for t in at.text)  # shown verbatim as text
    assert not any("<script>" in m.value for m in at.markdown)  # never fed to the markdown renderer


# ---------- real upload flow through the widgets (synthetic labels; plumbing, not accuracy) ----------
def _upload_and_check(blob: bytes, name: str = "label.png", mime: str = "image/png", camera: bool = False):
    at = AppTest.from_file(APP, default_timeout=120).run()
    if camera:
        at.camera_input[0].upload("photo.jpg", blob, "image/jpeg")
    else:
        at.file_uploader[0].upload(name, blob, mime)
    at.run()
    next(b for b in at.button if b.label == "Check this photo").click()
    at.run()
    assert not at.exception, [e.value for e in at.exception]
    return at


def test_upload_flow_alert_found_shows_matched_record():
    from tests.helpers import encode, render_label
    blob = encode(render_label(["Linzotal 600", "Linezolid Tablets IP 600 mg", "B.No.: TG261185    Mfg: 05/2026", "Exp: 04/2028"]), "PNG")
    at = _upload_and_check(blob)
    assert at.error and "Alert found" in at.error[0].value
    assert "Serial: 4" in all_text(at)


def test_upload_flow_no_alert_is_neutral():
    from tests.helpers import encode, render_label
    blob = encode(render_label(["Paracetamol Tablets IP 500 mg", "B.No.: ZX99001Q    Mfg: 01/2026", "Exp: 12/2028"]), "PNG")
    at = _upload_and_check(blob)
    assert any("No alert found" in i.value for i in at.info) and not at.success


def test_upload_flow_corrupt_file_shows_friendly_error():
    at = _upload_and_check(b"definitely not an image", "bad.png")
    assert at.error and "could not be used" in at.error[0].value


def test_camera_flow_uses_same_pipeline():
    from tests.helpers import encode, render_label
    blob = encode(render_label(["Paracetamol Tablets IP 500 mg", "Keep cool", "Exp: 12/2028"]), "JPEG", quality=95)
    at = _upload_and_check(blob, camera=True)
    assert at.warning and "Unable to verify" in at.warning[0].value


def test_streamlit_config_is_local_and_telemetry_free():
    cfg = (Path(APP).parent / ".streamlit" / "config.toml").read_text()
    assert 'address = "localhost"' in cfg and "gatherUsageStats = false" in cfg and "maxUploadSize = 10" in cfg
