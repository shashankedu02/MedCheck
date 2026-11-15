"""AU-1: a batch the user enters or corrects must never erase an alert the PHOTO produced.

The photo's own result is kept (`ScanResult.photo_result`) and shown first, at alert level, next to the result for the user's
batch. These tests use a scripted OCR stub against the real dataset and drive the real Streamlit script with real widgets.
They also pin what must NOT change: confirmation is still required, the user's batch is still never OCR evidence or product
corroboration, near neighbours still abstain, and legitimate corrections still work."""
from __future__ import annotations

import sys

import pytest
from PIL import Image
from streamlit.testing.v1 import AppTest

from medcheck.models import BatchSource, Status
from medcheck.pipeline import MedCheckPipeline
from tests.helpers import encode
from tests.test_app import ALLOWED_NEGATIONS, APP, BANNED, page_html, run_with, visible_html_text
from tests.test_ui_scene import _components
from tests.test_v2_pipeline import StubRapid

PHOTO = encode(Image.new("RGB", (500, 400), "white"), "PNG")  # plain: no pack region, two RapidOCR views
ALERT_LINES = ["Linzotal 600", "Linezolid Tablets IP 600 mg", "B.No.: TG261185"]          # listed serial 4
SECOND_PRODUCT = "Albendazole Tablets IP 400mg (Brand Name : Zolbe ND-400)"                 # listed serial 5, batch ANE01AOB
UNLISTED = ["Paracetamol Tablets IP 500 mg", "B.No.: ZX99001Q"]                                # not in the list


def check(lines):
    pipe = MedCheckPipeline.load(rapid_engine=StubRapid(lambda src: lines), tesseract_engine=None)
    return pipe, pipe.check(PHOTO)


@pytest.fixture(scope="module")
def alert_prior():
    pipe, prior = check(ALERT_LINES)
    assert prior.decision.status is Status.ALERT_FOUND and prior.matched_record.serial == 4
    return pipe, prior


@pytest.fixture(scope="module")
def two_product_prior():
    pipe, prior = check([*ALERT_LINES, SECOND_PRODUCT])  # the photo text also corroborates serial 5
    assert prior.decision.status is Status.ALERT_FOUND and prior.matched_record.serial == 4
    return pipe, prior


@pytest.fixture(scope="module")
def unlisted_prior():
    pipe, prior = check(UNLISTED)
    assert prior.decision.reason_code == "ocr_batch_unconfirmed" and prior.preserved_photo_alert is None
    return pipe, prior


# the three AU-1 scenarios: (typed batch, tick, expected status of the USER's batch, expected reason code)
SCENARIOS = {
    "no_alert": ("ZX99001Q", True, Status.NO_ALERT_FOUND, "no_alert"),                      # the audit reproduction
    "unable": ("ZX99001Q", False, Status.UNABLE_TO_VERIFY, "manual_entry_unconfirmed"),
    "also_alert": ("ANE01AOB", False, Status.ALERT_FOUND, "alert_confirmed"),
}


def _prior_for(name, alert_prior, two_product_prior):
    return two_product_prior if name == "also_alert" else alert_prior


# ---------------- the data: the photo's result survives, unchanged ----------------
@pytest.mark.parametrize("name", list(SCENARIOS))
def test_the_photo_result_is_preserved_unchanged_next_to_the_users_result(name, alert_prior, two_product_prior):
    pipe, prior = _prior_for(name, alert_prior, two_product_prior)
    typed, tick, status, code = SCENARIOS[name]
    before = (prior.decision, prior.matched_record, prior.extraction, prior.manual)
    res = pipe.verify_manual(prior, typed, tick)
    assert (res.decision.status, res.decision.reason_code) == (status, code)  # the user's batch decides its own result
    assert res.photo_result is prior and res.preserved_photo_alert is prior
    kept = res.preserved_photo_alert
    assert kept.decision.status is Status.ALERT_FOUND and kept.decision.batch_as_read == "TG261185"
    assert kept.matched_record.serial == 4 and kept.decision.action_check and kept.manual is None
    assert (prior.decision, prior.matched_record, prior.extraction, prior.manual) == before  # nothing was mutated or replaced
    assert res.extraction is prior.extraction  # the typed value is still never stored as OCR evidence
    assert res.manual.raw == typed and res.manual.source is BatchSource.USER_CORRECTED  # OCR had read TG261185, so this is a correction


def test_repeated_manual_entries_keep_the_original_photo_result(alert_prior):
    pipe, prior = alert_prior
    first = pipe.verify_manual(prior, "ZX99001Q", True)
    second = pipe.verify_manual(first, "ZX99002Q", True)  # the second attempt starts from the first manual result
    assert second.decision.status is Status.NO_ALERT_FOUND and second.manual.raw == "ZX99002Q"
    assert second.photo_result is prior and second.preserved_photo_alert is prior  # still the ORIGINAL photo result


def test_confirming_the_same_reading_is_not_a_second_result_and_shows_no_duplicate(alert_prior):
    pipe, prior = alert_prior
    res = pipe.verify_manual(prior, "tg-261185", False)  # same comparison key: the user only confirmed what OCR read
    assert res.manual.source is BatchSource.OCR and res.decision.status is Status.ALERT_FOUND
    assert res.preserved_photo_alert is None  # the current result already IS the photo's alert; nothing to add
    assert res.photo_result is prior


def test_no_preserved_alert_when_the_photo_did_not_alert(unlisted_prior):
    pipe, prior = unlisted_prior
    res = pipe.verify_manual(prior, "ZX99002Q", True)  # a normal correction
    assert res.decision.status is Status.NO_ALERT_FOUND and res.manual.source is BatchSource.USER_CORRECTED
    assert res.photo_result is prior and res.preserved_photo_alert is None


# ---------------- safeguards that must not change ----------------
def test_confirmation_provenance_and_matching_safeguards_are_unchanged(alert_prior, unlisted_prior):
    pipe, prior = alert_prior
    unconfirmed = pipe.verify_manual(prior, "ZX99001Q", False)
    assert unconfirmed.decision.status is Status.UNABLE_TO_VERIFY and not unconfirmed.decision.batch_confirmed  # still needs the tick
    confirmed = pipe.verify_manual(prior, "ZX99001Q", True)
    assert confirmed.decision.batch_confirmed and confirmed.manual.confirmed
    near = pipe.verify_manual(prior, "TG261186", True)  # a one-character neighbour of a listed batch: still abstains
    assert near.decision.status is Status.UNABLE_TO_VERIFY and near.decision.reason_code == "fuzzy_candidate_only"
    assert near.preserved_photo_alert is prior  # ... and the photo's alert is still there
    pipe2, prior2 = unlisted_prior  # the photo of an unlisted pack: a typed LISTED batch is still not corroborated by itself
    typed_listed = pipe2.verify_manual(prior2, "TG261185", True)
    assert typed_listed.decision.status is Status.UNABLE_TO_VERIFY  # never an alert on the user's say-so alone
    assert typed_listed.decision.reason_code in ("identity_conflict", "identity_uncorroborated")  # (500 mg photo vs 600 mg listed)


def test_the_notice_text_never_implies_the_users_result_cancels_the_alert(alert_prior):
    pipe, prior = alert_prior
    res = pipe.verify_manual(prior, "ZX99001Q", True)
    text = res.preserved_photo_alert_text("AUG-2026")
    assert "The batch read from the photo (TG261185) matched listed serial 4" in text
    assert "You then entered a different batch (ZX99001Q); that batch gave a different result" in text
    assert "does not cancel, disprove or replace the alert" in text and "Compare the batch printed on the pack with both numbers" in text
    assert res.preserved_photo_alert_text("AUG-2026") and prior.preserved_photo_alert_text("AUG-2026") == ""  # no manual entry -> nothing


# ---------------- the rendered screen (real script, real widgets) ----------------
def _enter(at, typed, tick):
    at.text_input(key="manual_text").set_value(typed).run()
    if tick:
        at.checkbox(key="manual_confirmed").check().run()
    next(b for b in at.button if b.label == "Check this batch number").click().run()
    assert not at.exception, [e.value for e in at.exception]
    return at


def _assert_original_alert_visible(at):
    html = page_html(at)
    assert 'class="mcr-hero mcr-photo" data-status="alert" role="alert"' in html, "the photo's alert section is missing"
    assert '<h2 class="mcr-headline">Alert found for the batch read from the photo</h2>' in html
    text = visible_html_text(at)
    assert "Batch read from the photo TG261185" in text and "listed serial 4" in text
    assert "does not cancel, disprove or replace the alert for the batch read from the photo" in text
    assert "Check before acting" in html and "<dt>Serial</dt><dd>4</dd>" in html  # the photo alert's action check and its record
    assert html.index("From the photo") < html.index("Result for the batch you entered")  # photo first, then the user's result
    scrubbed = text
    for ok in ALLOWED_NEGATIONS:
        scrubbed = scrubbed.replace(ok, "").replace(ok.capitalize(), "")
    assert not BANNED.search(scrubbed), BANNED.search(scrubbed)


@pytest.mark.parametrize("name", list(SCENARIOS))
def test_the_original_alert_stays_on_screen_after_a_manual_entry(name, alert_prior, two_product_prior):
    _pipe, prior = _prior_for(name, alert_prior, two_product_prior)
    typed, tick, status, code = SCENARIOS[name]
    at = _enter(run_with(prior), typed, tick)
    res = at.session_state["result"]
    assert res.decision.status is status and res.decision.reason_code == code
    _assert_original_alert_visible(at)
    html = page_html(at)
    kind = {Status.NO_ALERT_FOUND: "no_alert", Status.UNABLE_TO_VERIFY: "unable", Status.ALERT_FOUND: "alert"}[status]
    assert f'class="mcr-hero" data-status="{kind}"' in html  # the user's own result is shown separately, with its own banner
    assert "Result for the batch you entered" in html and typed in visible_html_text(at)
    if name == "also_alert":
        assert "that batch also gave an alert" in visible_html_text(at) and "<dt>Serial</dt><dd>5</dd>" in html
    else:
        assert "that batch gave a different result" in visible_html_text(at)


def test_the_audit_reproduction_no_longer_loses_the_alert(alert_prior):
    """Audit AU-1, exactly: OCR alert for TG261185, user enters ZX99001Q, ticks, checks."""
    _pipe, prior = alert_prior
    at = run_with(prior)
    assert at.text_input(key="manual_text").value == "TG261185"  # the OCR reading is prefilled
    _enter(at, "ZX99001Q", True)
    assert at.session_state["result"].decision.status is Status.NO_ALERT_FOUND  # the user's batch really is not listed
    _assert_original_alert_visible(at)  # ... but the photo's alert did not disappear


def test_the_alert_survives_a_second_entry_and_goes_away_only_with_a_new_photo_or_clear(alert_prior):
    _pipe, prior = alert_prior
    at = _enter(run_with(prior), "ZX99001Q", True)
    at = _enter(at, "ZX99002Q", True)  # a second manual attempt
    assert at.session_state["result"].manual.raw == "ZX99002Q"
    _assert_original_alert_visible(at)
    next(b for b in at.button if b.label == "Clear and start over").click().run()
    assert "result" not in at.session_state and 'mcr-photo' not in _markup(at)


def _markup(at):
    """The page's HTML without the stylesheet (class names also occur in the CSS)."""
    import re
    return re.sub(r"<style>.*?</style>", "", page_html(at), flags=re.S)


def test_a_normal_correction_after_a_non_alert_photo_shows_no_alert_section(unlisted_prior):
    _pipe, prior = unlisted_prior
    at = _enter(run_with(prior), "ZX99002Q", True)
    assert at.session_state["result"].decision.status is Status.NO_ALERT_FOUND
    html = _markup(at)
    assert "mcr-photo" not in html and "From the photo" not in html and "Result for the batch you entered" not in html
    assert '<p class="mcr-eyebrow">Result</p>' in html  # the ordinary heading is unchanged


def test_the_decorative_stage_follows_the_alert_not_the_calmer_result(alert_prior):
    _pipe, prior = alert_prior
    at = _enter(run_with(prior), "ZX99001Q", True)
    assert at.session_state["result"].decision.status is Status.NO_ALERT_FOUND
    payloads = [c.proto.json for c in _components(at)]
    assert payloads and all('"status": "alert"' in p or '"status":"alert"' in p for p in payloads), payloads


def test_the_basic_fallback_rendering_also_keeps_the_alert(alert_prior, monkeypatch):
    import medcheck_ui
    monkeypatch.setitem(sys.modules, "medcheck_ui.result", None)  # the view cannot load: native rendering takes over
    monkeypatch.delattr(medcheck_ui, "result", raising=False)
    _pipe, prior = alert_prior
    at = _enter(run_with(prior), "ZX99001Q", True)
    assert at.session_state["result"].decision.status is Status.NO_ALERT_FOUND
    errors = [e.value for e in at.error]
    assert any(v.startswith("**Alert found for the batch read from the photo**") and "does not cancel, disprove or replace" in v for v in errors)
    assert any(w.value.startswith("**Check before acting:**") for w in at.warning)
    assert any("Photo alert - Serial: 4" in t.value for t in at.text)
    assert any(i.value.startswith("**No alert found**") for i in at.info)  # the user's own result is still shown, separately
