"""Alert-side check (completion sprint, D-027): every alert tells the user what to compare on the pack, without delay.

Root cause addressed: an alert rests on an exact listed batch plus product words. A one-character misread of an UNLISTED
neighbouring batch of the same product (listed batches come in sequences such as PAK-636 / PAK-637) passes both checks,
and the product check never compares the manufacturer. Matching rules are unchanged; the alert is never delayed.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from medcheck.dataset import load_dataset
from medcheck.decision import decide
from medcheck.extraction import BatchField, DateField, ExtractionResult
from medcheck.matching import DatasetIndex, listed_neighbours, match_batch
from medcheck.models import ExpiryAssessment, ExpiryOutcome, FieldState, MatchAssessment, MatchOutcome, Status
from medcheck.normalization import batch_key
from medcheck.pipeline import ScanResult

APP = str(Path(__file__).resolve().parent.parent / "app.py")
BANNED = re.compile(r"\b(safe|genuine|authentic\w*|counterfeit|fake|guarantee\w*)\b", re.I)
EXP = ExpiryAssessment(ExpiryOutcome.UNDETERMINED, "04/2028", "Printed expiry reads 04/2028. Policy not approved.")


@pytest.fixture(scope="module")
def ds():
    return load_dataset()


@pytest.fixture(scope="module")
def index(ds):
    return DatasetIndex.build(ds)


def rec(ds, serial):
    return next(r for r in ds.records if r.serial == serial)


def _decide(match, batch_raw="TG261185", confirmed=False):
    return decide(system_failure=None, batch_state=FieldState.READ, match=match, expiry=EXP, dataset_period="AUG-2026",
                  batch_raw=batch_raw, entry_confirmed=confirmed)


def test_every_alert_carries_the_check_and_is_not_delayed(ds, index):
    m = match_batch(index, batch_key("TG261185"), rec(ds, 4).product_name)
    d = _decide(m, confirmed=False)
    assert d.status is Status.ALERT_FOUND  # no confirmation needed: alerts are never delayed (D-026)
    assert "exactly 'TG261185'" in d.action_check
    assert "manufacturer" in d.action_check and "character by character" in d.action_check
    assert not BANNED.search(d.action_check)


@pytest.mark.parametrize("outcome", [o for o in MatchOutcome if o is not MatchOutcome.CONFIRMED])
def test_non_alerts_have_no_action_check(outcome):
    d = _decide(MatchAssessment(outcome, "t"), confirmed=True)
    assert d.status is not Status.ALERT_FOUND and d.action_check == ""


def test_listed_neighbour_is_named_in_the_alert_evidence(ds, index):
    r = rec(ds, 113)  # PAK-637; serial 118 is PAK-636, same maker and product
    m = match_batch(index, batch_key(r.batch_number), r.product_name)
    assert m.outcome is MatchOutcome.CONFIRMED and m.matched_serial == 113  # outcome unchanged
    assert any("Listed serial(s) 118" in e and "single misread character" in e for e in m.evidence)


def test_no_neighbour_warning_when_no_listed_batch_is_close(ds, index):
    r = rec(ds, 4)
    m = match_batch(index, batch_key(r.batch_number), r.product_name)
    assert m.outcome is MatchOutcome.CONFIRMED and not any("Listed serial(s)" in e for e in m.evidence)


def test_neighbour_helper_matches_the_profiled_dataset(index):
    assert listed_neighbours(index, batch_key("PAK-637").key, 113) == (118,)
    assert listed_neighbours(index, batch_key("292").key, 1) == ()  # short keys: exact-only, no neighbours


def test_known_exposure_sibling_misread_still_alerts_with_the_check(ds, index):
    """Documented limitation (not fixed by software): a pack printed PAK-637 read as PAK-636 alerts for serial 118.
    Both are listed here; for an UNLISTED sibling the same mechanism gives a false alert. The check text is the remedy."""
    m = match_batch(index, batch_key("PAK636"), rec(ds, 113).product_name)
    assert m.outcome is MatchOutcome.CONFIRMED and m.matched_serial == 118
    d = _decide(m, batch_raw="PAK636")
    assert d.status is Status.ALERT_FOUND and "exactly 'PAK636'" in d.action_check


def test_known_exposure_conflicting_manufacturer_does_not_block_an_alert(ds, index):
    """Documented limitation: the manufacturer only ever adds support (D-006). A different maker printed on the pack does
    not stop the alert; the check text asks the user to compare the manufacturer with the listed record."""
    r = rec(ds, 113)
    text = "Paracetamol Tablets IP 500 mg\nManufactured by: Someother Remedies Pvt Ltd"
    m = match_batch(index, batch_key(r.batch_number), text)
    assert m.outcome is MatchOutcome.CONFIRMED
    assert "manufacturer" in _decide(m, batch_raw=r.batch_number).action_check


def _alert_result(ds, index):
    r = rec(ds, 4)
    m = match_batch(index, batch_key("TG261185"), r.product_name)
    d = _decide(m)
    ex = ExtractionResult(BatchField(FieldState.READ, "TG261185", batch_key("TG261185")), DateField(FieldState.READ, "04/2028"),
                          DateField(FieldState.NOT_FOUND), "Linzotal 600\nB.No. TG261185", 8)
    return ScanResult(decision=d, extraction=ex, match=m, matched_record=r, expiry=EXP, engine_version="t",
                      variants_used=("crop",), ocr_passes=2)


def test_ui_shows_the_check_and_the_side_by_side_batch(ds, index):
    at = AppTest.from_file(APP, default_timeout=30)
    at.session_state["result"] = _alert_result(ds, index)
    at.session_state["result_digest"] = None
    at.run()
    assert not at.exception
    assert at.error and at.error[0].value.startswith("**Alert found**")
    assert any(w.value.startswith("**Check before acting:**") and "TG261185" in w.value for w in at.warning)
    assert any("Compare: batch read from the photo = TG261185" in t.value and "listed batch = TG261185" in t.value for t in at.text)
