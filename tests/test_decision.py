"""Decision-engine truth-table tests (milestone M2). Engine is independent of OCR."""
from __future__ import annotations

import itertools
import re

import pytest

from medcheck.decision import decide
from medcheck.models import (
    BatchSource,
    ExpiryAssessment,
    ExpiryOutcome,
    FieldState,
    MatchAssessment,
    MatchOutcome,
    Status,
    SystemFailure,
)

PERIOD = "AUG-2026"
BANNED = re.compile(r"\b(is safe|are safe|genuine|authentic|counterfeit|free (of|from) defects|guarantee)", re.I)


def _match(outcome, serial=None):
    return MatchAssessment(outcome, "test", matched_serial=serial, candidate_serials=(serial,) if serial else (), evidence=("e",))


def _expiry(outcome):
    return ExpiryAssessment(outcome, "x", f"note-{outcome.value}")


def run(batch=FieldState.READ, match=None, expiry=ExpiryOutcome.NOT_READ, failure=None, anomaly=False,
        confirmed=True, source=BatchSource.OCR, raw="AB12345"):
    """`confirmed=True` by default: most truth-table tests are about the matching outcome itself. The confirmation
    policy (D-026) has its own tests below with confirmed=False."""
    return decide(system_failure=failure, batch_state=batch, match=match, expiry=_expiry(expiry), dataset_period=PERIOD,
                  expiry_anomaly=anomaly, batch_source=source, batch_raw=raw, entry_confirmed=confirmed)


def test_system_failures_are_never_a_status():
    for f in SystemFailure:
        d = run(failure=f, match=_match(MatchOutcome.NO_MATCH))
        assert d.status is None and d.is_system_error and d.system_failure is f
        assert "not a 'No alert found'" in d.explanation


def test_system_failure_beats_everything():
    d = run(failure=SystemFailure.DATASET_INTEGRITY, match=_match(MatchOutcome.CONFIRMED, 5), expiry=ExpiryOutcome.EXPIRED)
    assert d.status is None


@pytest.mark.parametrize("state", [FieldState.NOT_FOUND, FieldState.AMBIGUOUS])
def test_unreadable_or_ambiguous_batch_abstains_even_with_a_match_object(state):
    d = run(batch=state, match=_match(MatchOutcome.CONFIRMED, 1), expiry=ExpiryOutcome.EXPIRED)
    assert d.status is Status.UNABLE_TO_VERIFY


@pytest.mark.parametrize("outcome", [MatchOutcome.UNCORROBORATED, MatchOutcome.CONFLICT, MatchOutcome.COLLISION, MatchOutcome.FUZZY_ONLY])
def test_non_confirmed_matches_abstain(outcome):
    d = run(match=_match(outcome, 3), expiry=ExpiryOutcome.EXPIRED)
    assert d.status is Status.UNABLE_TO_VERIFY and d.matched_serial is None


def test_confirmed_is_alert_and_expiry_never_overrides():
    for e in ExpiryOutcome:
        d = run(match=_match(MatchOutcome.CONFIRMED, 7), expiry=e)
        assert d.status is Status.ALERT_FOUND and d.matched_serial == 7
        if e is not ExpiryOutcome.NOT_READ:
            assert any(f"note-{e.value}" in c for c in d.caveats)


def test_no_match_without_expired_verdict_is_no_alert():
    for e in (ExpiryOutcome.NOT_READ, ExpiryOutcome.UNPARSEABLE, ExpiryOutcome.UNDETERMINED, ExpiryOutcome.NOT_EXPIRED):
        assert run(match=_match(MatchOutcome.NO_MATCH), expiry=e).status is Status.NO_ALERT_FOUND


def test_no_match_with_expired_verdict_is_expired():
    assert run(match=_match(MatchOutcome.NO_MATCH), expiry=ExpiryOutcome.EXPIRED).status is Status.EXPIRED


def test_expired_requires_a_clean_no_match():
    d = run(match=_match(MatchOutcome.FUZZY_ONLY), expiry=ExpiryOutcome.EXPIRED)
    assert d.status is Status.UNABLE_TO_VERIFY


def test_missing_match_object_for_readable_batch_is_internal_error():
    assert run(match=None).system_failure is SystemFailure.INTERNAL


def test_expiry_anomaly_is_surfaced():
    d = run(match=_match(MatchOutcome.NO_MATCH), anomaly=True)
    assert any("earlier than the manufacturing date" in c for c in d.caveats)


def test_exhaustive_grid_only_valid_statuses_and_limits_always_present():
    allowed = {None, *Status}
    for failure, batch, outcome, expiry in itertools.product(
        [None, SystemFailure.DATASET_MISSING], FieldState, MatchOutcome, ExpiryOutcome
    ):
        d = run(batch=batch, match=_match(outcome, 1), expiry=expiry, failure=failure)
        assert d.status in allowed
        assert d.is_system_error == (d.status is None)
        assert any("not medical advice" in c for c in d.caveats)
        if d.status is Status.EXPIRED:
            assert outcome is MatchOutcome.NO_MATCH and batch is FieldState.READ and failure is None


def test_dataset_period_always_shown_for_real_statuses():
    for outcome in (MatchOutcome.CONFIRMED, MatchOutcome.NO_MATCH):
        d = run(match=_match(outcome, 1))
        assert PERIOD in " ".join((d.explanation, *d.caveats))


def test_no_forbidden_claims_in_any_text():
    for failure, batch, outcome, expiry in itertools.product([None, SystemFailure.INTERNAL], FieldState, MatchOutcome, ExpiryOutcome):
        d = run(batch=batch, match=_match(outcome, 1), expiry=expiry, failure=failure)
        text = " ".join((d.headline, d.explanation, *d.caveats))
        # the only allowed occurrence is the explicit negation in the No-alert wording
        cleaned = text.replace("does not mean the medicine is safe, genuine or free of quality problems", "")
        cleaned = cleaned.replace("does not test medicine quality or authenticity", "")
        cleaned = cleaned.replace("it does not show the medicine is genuine or safe", "")
        assert not BANNED.search(cleaned), cleaned


# ---- D-026: no clean negative for ANY batch string until the user has compared it with the pack ----
@pytest.mark.parametrize("source", list(BatchSource))
def test_clean_negative_is_withheld_until_confirmed_for_every_batch_source(source):
    d = run(match=_match(MatchOutcome.NO_MATCH), confirmed=False, source=source)
    assert d.status is Status.UNABLE_TO_VERIFY and not d.is_system_error
    assert d.reason_code == ("ocr_batch_unconfirmed" if source is BatchSource.OCR else "manual_entry_unconfirmed")
    assert d.batch_confirmed is False and d.batch_source is source and d.batch_as_read == "AB12345"
    assert "AB12345" in d.explanation or source is not BatchSource.OCR  # an OCR reading is shown back to the user
    assert "does not show the medicine is genuine or safe" in d.explanation  # what confirmation does NOT mean
    assert d.evidence == ("e",) and PERIOD in " ".join(d.caveats)


@pytest.mark.parametrize("source", list(BatchSource))
def test_confirmed_clean_negative_is_shown_and_records_the_confirmation(source):
    d = run(match=_match(MatchOutcome.NO_MATCH), confirmed=True, source=source)
    assert d.status is Status.NO_ALERT_FOUND and d.batch_confirmed is True
    assert "Batch checked: AB12345 (confirmed by you against the pack)" in d.explanation
    assert any("confirmed that this batch number matches the one printed on the pack" in c and "does not show the medicine is genuine or safe" in c
               for c in d.caveats)
    assert (any("by you" in c or "typed by you" in c for c in d.caveats)) == (source is not BatchSource.OCR)


@pytest.mark.parametrize("source", list(BatchSource))
def test_expired_is_also_withheld_until_confirmed(source):
    assert run(match=_match(MatchOutcome.NO_MATCH), expiry=ExpiryOutcome.EXPIRED, confirmed=False, source=source).status is Status.UNABLE_TO_VERIFY
    assert run(match=_match(MatchOutcome.NO_MATCH), expiry=ExpiryOutcome.EXPIRED, confirmed=True, source=source).status is Status.EXPIRED


@pytest.mark.parametrize("source", list(BatchSource))
def test_alert_is_never_delayed_for_confirmation(source):
    d = run(match=_match(MatchOutcome.CONFIRMED, 7), confirmed=False, source=source)
    assert d.status is Status.ALERT_FOUND and d.matched_serial == 7 and d.batch_confirmed is False


def test_confirmation_changes_nothing_except_the_clean_negative():
    for outcome in MatchOutcome:
        if outcome is MatchOutcome.NO_MATCH:
            continue
        a, b = run(match=_match(outcome, 3), confirmed=False), run(match=_match(outcome, 3), confirmed=True)
        assert (a.status, a.reason_code, a.matched_serial) == (b.status, b.reason_code, b.matched_serial), outcome


def test_exhaustive_grid_without_confirmation_never_yields_a_clean_negative():
    for failure, batch, outcome, expiry, source in itertools.product(
        [None, SystemFailure.INTERNAL], FieldState, MatchOutcome, ExpiryOutcome, BatchSource
    ):
        d = run(batch=batch, match=_match(outcome, 1), expiry=expiry, failure=failure, confirmed=False, source=source)
        assert d.status not in (Status.NO_ALERT_FOUND, Status.EXPIRED), (batch, outcome, expiry, source)
