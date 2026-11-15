"""Clickable batch readings (suggestions) in the manual batch form.

A click only fills the existing box with the exact OCR reading and clears the pack confirmation. It never confirms,
never submits, never preselects, and never changes what the matching or decision code does with the number.
"""
from __future__ import annotations

import pytest

from medcheck.decision import decide
from medcheck.extraction import BatchField, DateField, ExtractionResult
from medcheck.models import ExpiryAssessment, ExpiryOutcome, FieldState, MatchOutcome, Status
from medcheck.pipeline import ScanResult
from medcheck_ui import result as view
from tests.test_app import RECORD, result_for, run_with

# Deliberately awkward but allowed readings: look-alikes, lower case, a trailing comma, a hyphen. They must reach the box unchanged.
READINGS = ("TG26118S", "tg261l85,", "AB-12O5")


def ambiguous(readings=READINGS) -> ScanResult:
    exp = ExpiryAssessment(ExpiryOutcome.UNDETERMINED, "04/2028", "Policy not approved.")
    d = decide(system_failure=None, batch_state=FieldState.AMBIGUOUS, match=None, expiry=exp, dataset_period="AUG-2026")
    ex = ExtractionResult(BatchField(FieldState.AMBIGUOUS, None, None, "different batch readings across passes", tuple(readings)),
                          DateField(FieldState.READ, "04/2028"), DateField(FieldState.NOT_FOUND), "Linzotal 600", 8)
    return ScanResult(decision=d, extraction=ex, expiry=exp, engine_version="x", ocr_passes=4)


def sugg_buttons(at):
    return [b for b in at.button if b.key and b.key.startswith("mc_sugg_")]


def sugg_states(at):
    return {b.label: b.key.split("_")[2] for b in sugg_buttons(at)}


def suggestion(at, text):
    return next(b for b in sugg_buttons(at) if b.label == text)


def box(at):
    return at.text_input(key="manual_text")


def tick(at):
    return at.checkbox(key="manual_confirmed")


def check_button(at):
    return next(b for b in at.button if b.label == "Check this batch number")


def test_every_reading_is_offered_and_nothing_is_preselected_or_submitted():
    at = run_with(ambiguous())
    assert [b.label for b in sugg_buttons(at)] == list(READINGS)  # all of them, in the order the pipeline gave them
    assert box(at).value == "" and tick(at).value is False  # the first candidate is NOT chosen for the user
    assert set(sugg_states(at).values()) == {"off"}
    assert at.session_state["result"].decision.status is Status.UNABLE_TO_VERIFY


@pytest.mark.parametrize("reading", READINGS)
def test_clicking_a_suggestion_fills_the_box_with_the_exact_reading(reading):
    at = run_with(ambiguous())
    suggestion(at, reading).click().run()
    assert not at.exception
    assert box(at).value == reading  # byte for byte: no upper-casing, no O/0 or S/5 substitution, comma kept


def test_clicking_another_suggestion_replaces_the_box():
    at = run_with(ambiguous())
    suggestion(at, READINGS[0]).click().run()
    suggestion(at, READINGS[1]).click().run()
    assert box(at).value == READINGS[1]


def test_selected_and_unselected_suggestions_are_distinguishable():
    at = run_with(ambiguous())
    suggestion(at, READINGS[0]).click().run()
    assert sugg_states(at) == {READINGS[0]: "on", READINGS[1]: "off", READINGS[2]: "off"}
    suggestion(at, READINGS[2]).click().run()
    assert sugg_states(at) == {READINGS[0]: "off", READINGS[1]: "off", READINGS[2]: "on"}


def test_a_suggestion_is_marked_selected_only_while_the_box_holds_exactly_that_reading():
    at = run_with(ambiguous())
    suggestion(at, READINGS[0]).click().run()
    box(at).set_value(READINGS[0] + "X").run()  # edited -> no longer the OCR candidate
    assert set(sugg_states(at).values()) == {"off"}
    box(at).set_value(READINGS[0].lower()).run()  # case differs -> not the same string
    assert set(sugg_states(at).values()) == {"off"}


def test_selecting_a_suggestion_clears_an_earlier_confirmation_and_never_confirms():
    at = run_with(ambiguous())
    box(at).set_value("ZX99001Q").run()
    tick(at).check().run()
    assert tick(at).value is True
    suggestion(at, READINGS[0]).click().run()
    assert tick(at).value is False
    suggestion(at, READINGS[1]).click().run()
    assert tick(at).value is False  # a click is never a confirmation


def test_editing_the_box_clears_the_confirmation_after_a_suggestion():
    at = run_with(ambiguous())
    suggestion(at, READINGS[0]).click().run()
    tick(at).check().run()
    assert tick(at).value is True
    box(at).set_value(READINGS[0] + "1").run()
    assert tick(at).value is False


def test_a_click_does_not_submit_and_checking_still_requires_the_tick():
    at = run_with(ambiguous())
    before = at.session_state["result"]
    suggestion(at, "AB-12O5").click().run()
    assert at.session_state["result"] is before  # clicking did not run any check
    check_button(at).click().run()  # not ticked -> must not reassure
    d = at.session_state["result"].decision
    assert d.status is Status.UNABLE_TO_VERIFY and d.reason_code == "manual_entry_unconfirmed" and not d.batch_confirmed
    assert d.batch_as_read == "AB-12O5"  # the exact reading is what got checked


def test_ticking_after_a_suggestion_then_checking_uses_that_exact_reading():
    at = run_with(ambiguous())
    suggestion(at, "AB-12O5").click().run()
    tick(at).check().run()
    check_button(at).click().run()
    res = at.session_state["result"]
    assert res.decision.status is Status.NO_ALERT_FOUND and res.decision.batch_confirmed
    assert res.decision.batch_as_read == "AB-12O5" and res.manual.raw == "AB-12O5"
    assert res.manual.source.value == "user_corrected"  # a reading picked by the user is the user's value, never OCR evidence


def test_typing_without_any_suggestion_still_works():
    at = run_with(ambiguous())
    box(at).set_value("ZX99001Q").run()
    check_button(at).click().run()
    assert at.session_state["result"].decision.reason_code == "manual_entry_unconfirmed"
    tick(at).check().run()
    check_button(at).click().run()
    res = at.session_state["result"]
    assert res.decision.status is Status.NO_ALERT_FOUND and res.manual.raw == "ZX99001Q"


def test_no_suggestions_without_readings_or_when_the_result_is_not_unable_to_verify():
    assert not sugg_buttons(run_with(ambiguous(readings=())))
    assert not sugg_buttons(run_with(result_for(MatchOutcome.CONFIRMED, serial=4, record=RECORD)))


def test_the_suggestions_text_says_selecting_is_not_confirming():
    t = view.suggestions_intro_html()
    assert "Select one to fill the box" in t and "does not confirm" in t and "tick the confirmation box" in t


def test_keyboard_and_focus_support_is_in_place():
    css = view.css()
    assert "button:focus-visible" in css and "outline: 3px solid" in css  # visible focus ring on every suggestion
    assert "st-key-mc_sugg_on_" in css  # a distinct selected style
