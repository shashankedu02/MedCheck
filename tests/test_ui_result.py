"""Result presentation (medcheck_ui/result.py): the redesign changes how a result looks, never what it says.

These tests pin the presentation rules: every outcome has its own banner; the clean negative is neutral (not green, no tick);
nothing from the photo or the user reaches the page unescaped; the safety wording is complete and visible; no confidence or
accuracy figure appears; colours meet WCAG AA; and the basic native rendering takes over if the view cannot load.
"""
from __future__ import annotations

import colorsys
import re
import sys
from dataclasses import replace
from html import unescape

import pytest
from streamlit.testing.v1 import AppTest

from medcheck.decision import LIMITATION_TEXT, decide, system_error_decision
from medcheck.extraction import BatchField, DateField, ExtractionResult
from medcheck.image_input import ImageRejected
from medcheck.models import (
    BatchSource, Decision, ExpiryAssessment, ExpiryOutcome, FieldState, ManualEntry, MatchAssessment, MatchOutcome, Status, SystemFailure,
)
from medcheck.normalization import batch_key
from medcheck.pipeline import ScanResult
from medcheck_ui import result as view
from tests.test_app import APP, BANNED, ALLOWED_NEGATIONS, RECORD, extraction, result_for, run_with, status_of, headline_of, page_html, visible_html_text

CSS = view.css()


def text_of(*parts: str) -> str:
    return unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", re.sub(r"<style>.*?</style>", " ", "".join(parts), flags=re.S))))


def full(result, period="AUG-2026") -> str:
    return view.top_html(result, period) + view.bottom_html(result)


ALERT = result_for(MatchOutcome.CONFIRMED, serial=4, record=RECORD)
ALERT = replace(ALERT, decision=replace(ALERT.decision, batch_as_read="TG261185"))  # the pipeline always records the matched string
NO_ALERT = result_for(MatchOutcome.NO_MATCH)
UNABLE = result_for(MatchOutcome.COLLISION)
EXPIRED = replace(NO_ALERT, decision=Decision(Status.EXPIRED, "expired", "Expired", "Printed expiry has passed.", (LIMITATION_TEXT,)))
SYSTEM = ScanResult(decision=system_error_decision(SystemFailure.DATASET_INTEGRITY))
REJECTED = ScanResult(rejection=ImageRejected("too_small", "The image is too small."))


# ---------- every outcome has its own, unmistakable banner ----------
@pytest.mark.parametrize("result,kind,headline", [
    (ALERT, "alert", "Alert found"), (NO_ALERT, "no_alert", "No alert found"), (UNABLE, "unable", "Unable to verify"),
    (EXPIRED, "expired", "Expired"), (SYSTEM, "system", "System error: no result"), (REJECTED, "rejected", "This photo could not be used"),
])
def test_each_outcome_gets_its_own_banner_with_the_engines_headline(result, kind, headline):
    html = view.top_html(result, "AUG-2026")
    assert f'class="mcr-hero" data-status="{kind}"' in html and f'<h2 class="mcr-headline">{headline}</h2>' in html
    assert view.status_kind(result) == kind
    assert len({view.ACCENTS[k][0] for k in view.ACCENTS}) >= 5  # distinct accents; the word and glyph also differ, colour is never alone


def test_the_banner_always_states_what_was_checked_except_for_a_rejected_photo():
    for r in (ALERT, NO_ALERT, UNABLE, EXPIRED, SYSTEM):
        assert "Checked against: AUG-2026 CDSCO NSQ list only." in text_of(view.top_html(r, "AUG-2026"))


def test_alert_and_failures_are_announced_assertively_and_the_rest_politely():
    role = lambda r: re.search(r'class="mcr-hero"[^>]*role="(\w+)"', view.top_html(r, "P")).group(1)
    assert role(ALERT) == role(SYSTEM) == role(REJECTED) == "alert"
    assert role(NO_ALERT) == role(UNABLE) == role(EXPIRED) == "status"


# ---------- the clean negative stays neutral ----------
def _hue(hex_colour: str) -> float:
    r, g, b = (int(hex_colour[i:i + 2], 16) / 255 for i in (1, 3, 5))
    return colorsys.rgb_to_hsv(r, g, b)[0] * 360


def test_no_alert_is_never_green_and_never_carries_a_tick():
    colour, glyph = view.ACCENTS["no_alert"]
    assert not 70 <= _hue(colour) <= 170 and glyph == "i"
    everything = CSS + full(NO_ALERT)
    assert not re.search(r"[✓✔✅☑✨]|shield|success", everything, re.I)
    for colour, _g in view.ACCENTS.values():
        assert not 70 <= _hue(colour) <= 170  # no outcome is shown in a "passed" green


# ---------- nothing from the photo or the user reaches the page as markup ----------
def test_dynamic_values_are_escaped():
    evil = '<img src=x onerror="alert(1)">'
    r = result_for(MatchOutcome.NO_MATCH)
    ex = ExtractionResult(BatchField(FieldState.READ, evil, batch_key("ZX99001Q"), evil), DateField(FieldState.READ, evil, evil),
                          DateField(FieldState.AMBIGUOUS, None, evil), "x", 2)
    d = replace(r.decision, headline=evil, explanation=evil, caveats=(evil,), evidence=(evil,), batch_as_read=evil, action_check=evil)
    manual = ManualEntry(evil, "k", BatchSource.USER_CORRECTED, True)
    res = replace(r, decision=d, extraction=ex, manual=manual)
    html = full(res, period=evil)
    assert "<img" not in html and "onerror=\"" not in html and "&lt;img" in html
    alert = replace(ALERT, decision=replace(ALERT.decision, action_check=evil))
    assert "<img" not in full(alert)


def test_the_photos_recognised_text_is_not_part_of_the_view():
    r = replace(NO_ALERT, extraction=replace(NO_ALERT.extraction, product_text="UNIQUE-PRODUCT-LINE-XYZ"))
    assert "UNIQUE-PRODUCT-LINE-XYZ" not in full(r)  # it stays in the app's plain-text expander


# ---------- the three reading cards ----------
def test_batch_expiry_and_manufacturing_have_their_own_cards_with_a_state_word():
    html = view.top_html(NO_ALERT, "P")
    cards = re.findall(r'<li class="mcr-card" data-state="(\w+)"><p class="mcr-k">([^<]+)</p>', html)
    assert cards == [("read", "Batch number"), ("read", "Expiry date"), ("not_found", "Manufacturing date")]
    assert 'mcr-val mcr-mono">TG261185<' in html and 'mcr-val mcr-mono">04/2028<' in html
    assert 'mcr-none">Not found<' in html
    assert "Read means agreed by the OCR passes - not yet checked against the pack" in text_of(html)


def test_an_uncertain_batch_is_labelled_uncertain_and_its_readings_are_listed():
    r = result_for(None, batch_state=FieldState.AMBIGUOUS)
    html = full(r)
    assert 'data-state="ambiguous"' in html and ">Uncertain<" in html and "reason text" in html
    assert "mcr-reading" not in html  # the readings are now clickable buttons in the batch form (tests/test_batch_suggestions.py)
    assert "Batch readings seen across the passes" in view.suggestions_intro_html() and "does not confirm" in view.suggestions_intro_html()


def test_a_corrected_batch_is_shown_as_yours_and_not_read_from_the_photo():
    ocr = result_for(None, batch_state=FieldState.AMBIGUOUS)
    res = replace(ocr, manual=ManualEntry("TG261185", "TG261185", BatchSource.USER_CORRECTED, False))
    html = view.top_html(res, "P")
    assert "Batch used for this result" in html and "corrected by you; not read from the photo" in html


def _cards(html: str) -> dict[str, str]:
    return {m.group(1): m.group(0) for m in re.finditer(r'<li class="mcr-card".*?<p class="mcr-k">([^<]+)</p>.*?</li>', html, flags=re.S)}


def test_confirmed_ocr_batch_shows_confirmed_by_you_on_the_batch_card_only():
    assert NO_ALERT.decision.batch_confirmed and NO_ALERT.decision.batch_source is BatchSource.OCR
    html = view.top_html(NO_ALERT, "P")
    cards = _cards(html)
    assert "Confirmed by you" in cards["Batch number"] and ">Read<" in cards["Batch number"]  # the state word stays
    assert "Confirmed by you" not in cards["Expiry date"] and "Confirmed by you" not in cards["Manufacturing date"]
    assert html.count("Confirmed by you") == 1
    assert "Read means agreed by the OCR passes - not yet checked against the pack" in text_of(html)  # conservative legend kept


def test_no_confirmed_by_you_chip_until_the_user_has_confirmed():
    assert not UNABLE.decision.batch_confirmed and "Confirmed by you" not in full(UNABLE)
    unconfirmed = replace(NO_ALERT, decision=replace(NO_ALERT.decision, batch_confirmed=False))
    assert "Confirmed by you" not in view.top_html(unconfirmed, "P")
    assert "Confirmed by you" not in view.top_html(ALERT, "P")  # an alert is never confirmed or delayed


def test_confirmed_corrected_batch_carries_the_tick_on_the_users_value_not_on_the_ocr_card():
    manual = ManualEntry("ZX99002Q", "ZX99002Q", BatchSource.USER_CORRECTED, True)
    res = replace(NO_ALERT, manual=manual, decision=replace(NO_ALERT.decision, batch_source=BatchSource.USER_CORRECTED, batch_as_read="ZX99002Q"))
    html = view.top_html(res, "P")
    cards = _cards(html)
    assert html.count("Confirmed by you") == 1
    assert "Batch used for this result" in cards["Batch number"] and "ZX99002Q" in cards["Batch number"]
    used = re.search(r'<p class="mcr-used">.*?</p>', html, flags=re.S).group(0)
    assert "Confirmed by you" in used and "corrected by you; not read from the photo" in used


def test_the_confirmed_chip_is_not_green():
    rule = re.search(r"\.mcr-chip-ok\s*\{([^}]*)\}", CSS).group(1)
    colours = [tuple(int(h[i:i + 2], 16) for i in (0, 2, 4)) for h in re.findall(r"#([0-9a-fA-F]{6})", rule)]
    colours += [tuple(int(x) for x in m) for m in re.findall(r"rgba?\((\d+),\s*(\d+),\s*(\d+)", rule)]
    assert colours and all(not (g > r and g >= b) for r, g, b in colours)  # blue family: green channel never dominant


# ---------- the alert ----------
def test_alert_shows_the_action_check_and_the_batch_beside_the_listed_batch():
    html = view.top_html(ALERT, "AUG-2026")
    assert ALERT.decision.action_check and unescape(ALERT.decision.action_check) in unescape(html)
    assert html.index("Check before acting") < html.index("What was read from the photo") < html.index("Matched NSQ record")
    assert "Batch read from the photo</p>" in html and "Listed batch</p>" in html
    for label in ("Serial", "Product", "Manufacturing date", "Expiry date", "Manufactured by", "NSQ result", "Reported by", "Reporting period"):
        assert f"<dt>{label}</dt>" in html
    assert "Batch checked" in html and "read from the photo" in html


def test_a_typed_batch_is_compared_as_entered_by_you():
    res = replace(ALERT, decision=replace(ALERT.decision, batch_source=BatchSource.USER_ENTERED))
    assert "Batch entered by you</p>" in view.top_html(res, "P")


def test_only_an_alert_gets_the_action_check_or_the_record():
    for r in (NO_ALERT, UNABLE, EXPIRED, SYSTEM, REJECTED):
        html = view.top_html(r, "P")
        assert "Check before acting" not in html and "Matched NSQ record" not in html


# ---------- safety wording is complete and visible ----------
@pytest.mark.parametrize("result", [ALERT, NO_ALERT, UNABLE, EXPIRED, SYSTEM])
def test_the_full_limitation_and_every_caveat_are_visible_on_the_page(result):
    html = view.bottom_html(result)
    assert 'class="mcr-limit"' in html and unescape(LIMITATION_TEXT) in unescape(html)
    for c in result.decision.caveats:
        assert unescape(c) in unescape(html)


def test_the_no_alert_text_keeps_its_negation():
    assert "does not mean the medicine is safe, genuine or free of quality problems" in text_of(view.top_html(NO_ALERT, "P"))


def test_an_unconfirmed_negative_is_unable_to_verify_not_no_alert():
    match = MatchAssessment(MatchOutcome.NO_MATCH, "t")
    exp = ExpiryAssessment(ExpiryOutcome.UNDETERMINED, "04/2028", "n")
    d = decide(system_failure=None, batch_state=FieldState.READ, match=match, expiry=exp, dataset_period="AUG-2026", batch_raw="ZX99001Q")
    res = replace(NO_ALERT, decision=d)
    html = view.top_html(res, "P")
    assert 'data-status="unable"' in html and '<h2 class="mcr-headline">Unable to verify</h2>' in html and "ZX99001Q" in html


@pytest.mark.parametrize("result", [ALERT, NO_ALERT, UNABLE, EXPIRED, SYSTEM, REJECTED])
def test_no_confidence_figure_no_claim_word_and_no_percentage(result):
    text = text_of(full(result)) + " " + view.steps_html()
    assert "%" not in text and not re.search(r"confiden|accura|probab|\bscore", text, re.I)
    for ok in ALLOWED_NEGATIONS:
        text = text.replace(ok, "").replace(ok.capitalize(), "")
    assert not BANNED.search(text), BANNED.search(text).group(0)


def test_the_batch_form_steps_keep_the_lookalike_rule():
    steps = text_of(view.steps_html())
    assert "O is not 0, I is not 1, S is not 5" in steps and "Compare" in steps and "Confirm" in steps


# ---------- accessibility and restraint ----------
def _lum(rgb):
    def ch(v):
        v /= 255
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    r, g, b = (ch(x) for x in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _ratio(a, b):
    la, lb = sorted((_lum(a), _lum(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def _rgb(h):
    return tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))


def _over(fg_rgb, alpha, base):
    return tuple(alpha * f + (1 - alpha) * b for f, b in zip(fg_rgb, base))


# the tool is a navy glass panel over the 3D canvas; the worst case behind it is a white highlight (as in test_ui_scene)
WORST_BASE = _over((8, 24, 50), 0.86, (255, 255, 255))


def _backgrounds():
    """Surfaces the general text colours can sit on (card, callout, verify panel, a banner of any outcome), worst case behind them."""
    bgs = [WORST_BASE, _over((255, 255, 255), 0.045, WORST_BASE), _over((251, 191, 36), 0.09, WORST_BASE), _over((34, 211, 238), 0.09, WORST_BASE)]
    for colour, _g in view.ACCENTS.values():
        bgs.append(_over(_rgb(colour), 0.16, (6, 20, 43)))  # the banner: an opaque mix of the accent into the page navy
    return bgs


def test_every_text_colour_meets_wcag_aa_on_every_surface_it_can_sit_on():
    colours = set(re.findall(r"(?<![-\w])color:\s*(#[0-9a-fA-F]{6})", CSS)) | set(re.findall(r"--mc-(?:text|muted):\s*(#[0-9a-fA-F]{6})", CSS))
    colours.discard("#04122a")  # button label: dark text on the cyan button, checked below
    assert len(colours) >= 6  # the muted, body, heading, chip and warning colours (outcome accents are checked below)
    for c in sorted(colours):
        worst = min(_ratio(_rgb(c), bg) for bg in _backgrounds())
        assert worst >= 4.5, (c, round(worst, 2))
    for colour, _g in view.ACCENTS.values():  # an outcome's accent is text only on its own banner (and on the worst-case card behind a glass panel)
        banner = _over(_rgb(colour), 0.16, (6, 20, 43))
        assert _ratio(_rgb(colour), banner) >= 4.5 and _ratio(_rgb(colour), WORST_BASE) >= 4.5, colour
    assert _ratio(_rgb("#04122a"), _rgb("#22d3ee")) >= 4.5


def test_restraint_and_responsiveness():
    assert "@keyframes" not in CSS and "animation" not in CSS and "transition" not in CSS  # no motion in the result
    assert "@media (max-width: 720px)" in CSS and "auto-fit" in CSS
    assert "monospace" in CSS and ".mcr-mono" in CSS  # batch strings in a mono face, so O/0 and I/1 are easier to tell apart
    assert "http://" not in CSS and "https://" not in CSS and "url(" not in CSS  # nothing remote


def test_headings_are_real_headings_and_decorative_glyphs_are_hidden_from_readers():
    html = full(ALERT)
    assert html.count("<h2") == 1 and "<h3" in html
    assert 'class="mcr-glyph" aria-hidden="true"' in html and 'class="mcr-vs" aria-hidden="true"' in html


# ---------- in the app ----------
def test_app_places_the_batch_form_between_the_result_and_the_explanation():
    at = run_with(NO_ALERT)
    assert status_of(at) == "no_alert"
    assert any("batch number yourself" in s.value for s in at.subheader)
    blocks = [b.value for b in at.get("html")]
    top = next(i for i, b in enumerate(blocks) if 'class="mcr-hero"' in b)
    steps = next(i for i, b in enumerate(blocks) if '<ol class="mcr-steps">' in b)
    notes = next(i for i, b in enumerate(blocks) if '>Please note<' in b)
    assert top < steps < notes  # result, then the action, then the explanation and the notes


def test_the_photos_text_is_still_shown_only_as_plain_text():
    r = replace(NO_ALERT, extraction=replace(NO_ALERT.extraction, product_text="<b>bold</b> line"))
    at = run_with(r)
    assert any("<b>bold</b> line" in t.value for t in at.text) and "<b>bold</b>" not in page_html(at)


def test_basic_native_rendering_takes_over_when_the_view_cannot_load(monkeypatch):
    import medcheck_ui
    monkeypatch.setitem(sys.modules, "medcheck_ui.result", None)  # importing it now raises ImportError
    monkeypatch.delattr(medcheck_ui, "result", raising=False)  # ... also when it was already imported as a package attribute
    at = run_with(ALERT)
    assert at.error and at.error[0].value.startswith("**Alert found**")
    assert any(w.value.startswith("**Check before acting:**") for w in at.warning)
    assert any("Serial: 4" in t.value for t in at.text) and not any('class="mcr-hero"' in e.value for e in at.get("html"))
    at = run_with(NO_ALERT)
    assert any(i.value.startswith("**No alert found**") for i in at.info) and not at.success
    assert any("batch number yourself" in s.value for s in at.subheader)
