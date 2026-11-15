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
    "it does not show the medicine is genuine or safe",
)
BANNED = re.compile(r"\b(safe|genuine|authentic\w*|counterfeit|fake|guarantee\w*|free (of|from) defects)\b", re.I)


def extraction(batch_state=FieldState.READ):
    bk = batch_key("TG261185")
    b = BatchField(batch_state, "TG261185", bk) if batch_state is FieldState.READ else BatchField(batch_state, None, None, "reason text", ("AB123", "AB124"))
    return ExtractionResult(b, DateField(FieldState.READ, "04/2028"), DateField(FieldState.NOT_FOUND), "Linzotal 600\nB.No. TG261185", 8)


def result_for(outcome, batch_state=FieldState.READ, serial=None, record=None):
    match = None if batch_state is not FieldState.READ else MatchAssessment(outcome, "t", matched_serial=serial, evidence=("Evidence line.",))
    exp = ExpiryAssessment(ExpiryOutcome.UNDETERMINED, "04/2028", "Printed expiry reads 04/2028. Policy not approved.")
    d = decide(system_failure=None, batch_state=batch_state, match=match, expiry=exp, dataset_period="AUG-2026",
               entry_confirmed=True)  # fixture for rendering: a clean negative that the user has already confirmed
    return ScanResult(decision=d, extraction=extraction(batch_state), match=match, matched_record=record, expiry=exp,
                      engine_version="tesseract 5.5.3", variants_used=("gray",), ocr_passes=8)


def run_with(result):
    at = AppTest.from_file(APP, default_timeout=30)
    at.session_state["result"] = result
    at.session_state["result_digest"] = None
    at.run()
    assert not at.exception, [e.value for e in at.exception]
    return at


def page_html(at):
    """Everything the page rendered through st.html (the redesigned result view), as one string."""
    return "\n".join(e.value for e in at.get("html"))


def visible_html_text(at):
    """The page's st.html content as text: stylesheets dropped, tags replaced by spaces, entities decoded."""
    import html as _html
    h = re.sub(r"<style>.*?</style>", " ", page_html(at), flags=re.S)
    return _html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", h)))


def status_of(at):
    """Presentation bucket of the result banner (alert / no_alert / unable / expired / system / rejected), or None."""
    m = re.search(r'class="mcr-hero" data-status="(\w+)"', page_html(at))
    return m.group(1) if m else None


def headline_of(at):
    import html as _html
    m = re.search(r'<h2 class="mcr-headline">(.*?)</h2>', page_html(at), flags=re.S)
    return _html.unescape(m.group(1)) if m else None


def record_value(at, label):
    import html as _html
    m = re.search(r'<dt>' + re.escape(label) + r'</dt><dd>(.*?)</dd>', page_html(at), flags=re.S)
    return _html.unescape(m.group(1)) if m else None


def all_text(at):
    parts = []
    for coll in (at.title, at.markdown, at.caption, at.text, at.info, at.warning, at.error, at.subheader, at.header, at.success):
        parts += [e.value for e in coll]
    parts.append(visible_html_text(at))
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
    assert status_of(at) == "alert" and headline_of(at) == "Alert found" and not at.error
    text = all_text(at)
    assert "TG261185" in text and record_value(at, "Serial") == "4" and record_value(at, "NSQ result") and "AUG-2026" in text
    assert "Listed batch" in text and "Batch read from the photo" in text


def test_no_alert_is_neutral_not_green_and_has_disclaimer():
    at = run_with(result_for(MatchOutcome.NO_MATCH))
    assert status_of(at) == "no_alert" and headline_of(at) == "No alert found"  # the HEADLINE, not the page disclaimer
    assert not at.success and not at.error
    text = all_text(at)
    assert "does not mean the medicine is safe, genuine or free of quality problems" in text and "AUG-2026" in text


@pytest.mark.parametrize("outcome", [MatchOutcome.COLLISION, MatchOutcome.UNCORROBORATED, MatchOutcome.CONFLICT, MatchOutcome.FUZZY_ONLY])
def test_unable_to_verify_explains_and_suggests_next_step(outcome):
    at = run_with(result_for(outcome, serial=None))
    assert status_of(at) == "unable" and headline_of(at) == "Unable to verify"
    assert "pharmacist" in all_text(at)


def test_unreadable_batch_shows_readings_and_unable():
    at = run_with(result_for(None, batch_state=FieldState.AMBIGUOUS))
    assert status_of(at) == "unable"
    assert {b.label for b in at.button if b.key and b.key.startswith("mc_sugg_")} == {"AB123", "AB124"}  # both readings offered as buttons


def test_system_error_is_distinct_and_never_a_status():
    for failure in SystemFailure:
        at = run_with(ScanResult(decision=system_error_decision(failure)))
        assert status_of(at) == "system" and "System error" in headline_of(at)
        assert "not a 'No alert found' result" in visible_html_text(at)
        assert headline_of(at) != "No alert found" and not at.info[1:]


def test_rejected_upload_message_is_shown():
    at = run_with(ScanResult(rejection=ImageRejected("not_an_image", "The file could not be read as an image. It may be corrupt.")))
    assert status_of(at) == "rejected" and "could not be used" in visible_html_text(at)


@pytest.mark.parametrize("make", [
    lambda: result_for(MatchOutcome.CONFIRMED, serial=4, record=RECORD),
    lambda: result_for(MatchOutcome.NO_MATCH),
    lambda: result_for(MatchOutcome.COLLISION),
    lambda: result_for(None, batch_state=FieldState.NOT_FOUND),
    lambda: ScanResult(decision=system_error_decision(SystemFailure.DATASET_INTEGRITY)),
])
def test_no_forbidden_claims_anywhere_on_page(make):
    text = all_text(run_with(make()))
    for ok in ALLOWED_NEGATIONS:  # the same permitted negations, also when they start a sentence
        text = text.replace(ok, "").replace(ok.capitalize(), "")
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
    assert status_of(at) == "alert" and headline_of(at) == "Alert found"
    assert record_value(at, "Serial") == "4"


def test_upload_flow_no_alert_is_neutral():
    from tests.helpers import encode, render_label
    blob = encode(render_label(["Paracetamol Tablets IP 500 mg", "B.No.: ZX99001Q    Mfg: 01/2026", "Exp: 12/2028"]), "PNG")
    at = _upload_and_check(blob)
    # D-026: first the app asks for the pack comparison; no clean negative and no neutral "No alert found" box yet
    assert status_of(at) == "unable" and headline_of(at) != "No alert found"
    assert "compare this number with the one printed on the pack" in visible_html_text(at)
    assert any("Next step" in i.value for i in at.info) and at.text_input(key="manual_text").value == "ZX99001Q"
    at.checkbox(key="manual_confirmed").check().run()
    _button(at, "Check this batch number").click().run()
    assert status_of(at) == "no_alert" and not at.success
    assert at.session_state["result"].decision.batch_confirmed and at.session_state["result"].manual.source.value == "ocr"
    assert "confirmed by you against the pack" in all_text(at)


def test_upload_flow_corrupt_file_shows_friendly_error():
    at = _upload_and_check(b"definitely not an image", "bad.png")
    assert status_of(at) == "rejected" and "could not be used" in visible_html_text(at)


def test_camera_flow_uses_same_pipeline():
    from tests.helpers import encode, render_label
    blob = encode(render_label(["Paracetamol Tablets IP 500 mg", "Keep cool", "Exp: 12/2028"]), "JPEG", quality=95)
    at = _upload_and_check(blob, camera=True)
    assert status_of(at) == "unable" and headline_of(at) == "Unable to verify"


def test_streamlit_config_is_local_and_telemetry_free():
    cfg = (Path(APP).parent / ".streamlit" / "config.toml").read_text()
    assert 'address = "localhost"' in cfg and "gatherUsageStats = false" in cfg and "maxUploadSize = 10" in cfg


# ---- manual batch entry in the UI (V2) ----
def _button(at, label):
    return next(b for b in at.button if b.label == label)


def test_manual_entry_flow_in_the_ui():
    at = run_with(result_for(MatchOutcome.NO_MATCH, batch_state=FieldState.NOT_FOUND))
    assert any("batch number yourself" in s.value for s in at.subheader)
    assert at.text_input(key="manual_text").value == ""  # nothing was read cleanly, so nothing is guessed/prefilled

    at.text_input(key="manual_text").set_value("TG261185").run()
    _button(at, "Check this batch number").click().run()
    assert not at.exception
    res = at.session_state["result"]
    # the fixture's OCR had conflicting readings (AB123/AB124), so the user's value counts as a correction
    assert res.decision.status is Status.ALERT_FOUND and res.manual.source.value == "user_corrected"
    assert "corrected by you" in all_text(at) and "not read from the photo" in all_text(at)

    at.text_input(key="manual_text").set_value("ZX99001Q").run()
    _button(at, "Check this batch number").click().run()  # unlisted, not confirmed -> must not reassure
    assert at.session_state["result"].decision.reason_code == "manual_entry_unconfirmed"
    at.checkbox(key="manual_confirmed").check().run()
    _button(at, "Check this batch number").click().run()
    assert at.session_state["result"].decision.status is Status.NO_ALERT_FOUND
    assert "Batch checked: ZX99001Q" in all_text(at)


def test_manual_entry_shows_a_friendly_error_for_bad_input():
    at = run_with(result_for(MatchOutcome.NO_MATCH, batch_state=FieldState.NOT_FOUND))
    at.text_input(key="manual_text").set_value("AB").run()
    _button(at, "Check this batch number").click().run()
    assert not at.exception and any("at least" in w.value for w in at.warning)


def test_clean_ocr_value_is_prefilled_for_review():
    at = run_with(result_for(MatchOutcome.UNCORROBORATED, serial=4))
    assert at.text_input(key="manual_text").value == "TG261185"


def test_no_manual_form_for_rejected_photo_or_system_error():
    rejected = ScanResult(rejection=ImageRejected("too_small", "The image is too small."))
    assert not any("batch number yourself" in s.value for s in run_with(rejected).subheader)


# ---- stale server (code updated while the app was running) ----
def test_stale_modules_show_a_restart_instruction_not_a_traceback(monkeypatch):
    import medcheck.models as models

    monkeypatch.delattr(models, "BatchSource")  # what a long-running server holding an OLD models module looks like
    at = AppTest.from_file(APP, default_timeout=30).run()
    assert not at.exception
    assert any("updated while this page was running" in e.value and "Ctrl+C" in e.value for e in at.error)


def test_editing_the_batch_clears_the_confirmation_tick():
    at = run_with(result_for(MatchOutcome.NO_MATCH, batch_state=FieldState.NOT_FOUND))
    at.text_input(key="manual_text").set_value("ZX99001Q").run()
    at.checkbox(key="manual_confirmed").check().run()
    assert at.checkbox(key="manual_confirmed").value is True
    at.text_input(key="manual_text").set_value("ZX99002Q").run()  # a different number needs its own confirmation
    assert at.checkbox(key="manual_confirmed").value is False
    _button(at, "Check this batch number").click().run()
    assert at.session_state["result"].decision.reason_code == "manual_entry_unconfirmed"


# ---- D-026 in the UI ----
def _unconfirmed_ocr_negative():
    """A cleanly OCR-read batch with no listed match, exactly as pipeline.check() now returns it."""
    from medcheck.decision import decide as _decide

    match = MatchAssessment(MatchOutcome.NO_MATCH, "t", evidence=("Evidence line.",))
    exp = ExpiryAssessment(ExpiryOutcome.UNDETERMINED, "04/2028", "Policy not approved.")
    d = _decide(system_failure=None, batch_state=FieldState.READ, match=match, expiry=exp, dataset_period="AUG-2026",
                batch_raw="TG261185")
    return ScanResult(decision=d, extraction=extraction(FieldState.READ), match=match, expiry=exp, engine_version="x", ocr_passes=2)


def test_unconfirmed_ocr_negative_is_unable_to_verify_with_clear_instructions():
    at = run_with(_unconfirmed_ocr_negative())
    assert status_of(at) == "unable" and headline_of(at) == "Unable to verify"
    text = all_text(at)
    assert "compare this number with the one printed on the pack" in text
    assert "Confirming means you checked the printed batch number; it does not show the medicine is genuine or safe" in text
    assert "agreed by the OCR passes - not yet checked against the pack" in text and "read consistently" not in text
    assert at.text_input(key="manual_text").value == "TG261185" and at.checkbox(key="manual_confirmed").value is False
    assert any("I compared this number with the one printed on the pack" in c.label for c in at.checkbox)


def test_pressing_the_button_without_ticking_keeps_unable_to_verify():
    from dataclasses import replace

    unlisted = ExtractionResult(BatchField(FieldState.READ, "ZX99001Q", batch_key("ZX99001Q")), DateField(FieldState.READ, "04/2028"),
                                DateField(FieldState.NOT_FOUND), "Paracetamol Tablets IP 500 mg", 2)
    at = run_with(replace(_unconfirmed_ocr_negative(), extraction=unlisted))
    _button(at, "Check this batch number").click().run()
    assert at.session_state["result"].decision.status is Status.UNABLE_TO_VERIFY  # cannot confirm -> stays unable
    assert at.session_state["result"].decision.reason_code == "ocr_batch_unconfirmed"


def test_ocr_alert_is_shown_immediately_without_any_confirmation():
    at = run_with(result_for(MatchOutcome.CONFIRMED, serial=4, record=RECORD))
    assert status_of(at) == "alert" and not at.checkbox[0].value  # nothing was ticked
