"""Decision-engine truth-table tests (milestone M2). Engine is independent of OCR."""
from __future__ import annotations

import itertools
import re

import pytest

from medcheck.decision import decide
from medcheck.models import (
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


def run(batch=FieldState.READ, match=None, expiry=ExpiryOutcome.NOT_READ, failure=None, anomaly=False):
    return decide(system_failure=failure, batch_state=batch, match=match, expiry=_expiry(expiry), dataset_period=PERIOD, expiry_anomaly=anomaly)


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
        assert not BANNED.search(cleaned), cleaned
