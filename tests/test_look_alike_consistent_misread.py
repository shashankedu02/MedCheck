"""Regression for the manual-testing report: T003 (true batch HLAS0019) was read as HLA50019 by BOTH engine views,
shown as "read consistently", and produced `No alert found`. (Reproduced with the reporter's own loosely cropped file:
both RapidOCR views returned HLA50019 on every run. These tests use a stub engine that returns exactly that reading.)

Two separate properties, deliberately tested separately:
  1. If the true batch IS on the list, a consistent S/5 misread is a near-neighbour and abstains (matching safeguard).
  2. If the true batch is NOT near any listed batch nothing can reveal the misread, so (D-026) the OCR-read batch is shown
     back and a clean `No alert found` appears only after the user has compared it with the pack. No automatic S/5
     substitution exists; the user's correction goes through the same matching rules.
"""
from __future__ import annotations

from dataclasses import replace

import pytest

from medcheck.dataset import DatasetRecord
from medcheck.models import FieldState, Status
from medcheck.pipeline import MedCheckPipeline
from tests.test_v2_pipeline import PHOTO, V1, V2, StubRapid

LINE = "B.No.HLA50019 MFG.JUL.2025 EXP.JUN.2028"  # what the engines returned in the report (S read as 5)
PRODUCT = "Hicet-L Levocetirizine Tablets IP"


def pipeline(listed_true_batch: bool) -> MedCheckPipeline:
    stub = StubRapid({V1: [LINE, PRODUCT], V2: [LINE, PRODUCT]})
    p = MedCheckPipeline.load(rapid_engine=stub, tesseract_engine=None)
    if listed_true_batch:  # synthetic record: HLAS0019 is NOT in the real August 2026 list
        rec = DatasetRecord(999, "Hicet-L Levocetirizine Tablets IP 5 mg", "HLAS0019", "07/2025", "06/2028", "Test Ltd", "NSQ", "t", "t", "AUG-2026")
        p = MedCheckPipeline(replace(p.dataset, records=(*p.dataset.records, rec)), rapid_engine=stub, tesseract_engine=None)
    return p


def test_both_views_agree_on_the_wrong_string_and_the_batch_is_marked_read():
    r = pipeline(False).check(PHOTO)
    assert r.extraction.batch.state is FieldState.READ and r.extraction.batch.raw == "HLA50019"  # raw reading kept as read
    assert r.extraction.batch.raw != "HLAS0019"  # S was NOT silently substituted for 5


def test_if_the_true_batch_is_listed_the_consistent_misread_abstains():
    r = pipeline(True).check(PHOTO)
    assert r.match.outcome.value == "fuzzy_only"
    assert r.decision.status is Status.UNABLE_TO_VERIFY and r.decision.reason_code == "fuzzy_candidate_only"
    assert 999 in r.match.candidate_serials  # the listed look-alike is shown as a candidate, never as a match


def test_consistent_misread_of_an_unlisted_batch_must_not_give_a_clean_no_alert_without_human_confirmation():
    """D-026 closes the gap that was an xfail: the OCR-read batch HLA50019 is shown back and must be compared with the pack."""
    p = pipeline(False)
    r = p.check(PHOTO)
    assert r.decision.status is Status.UNABLE_TO_VERIFY and r.decision.reason_code == "ocr_batch_unconfirmed"
    assert "HLA50019" in r.decision.explanation and "S and 5" in r.decision.explanation
    # the user compares with the pack, sees HLAS0019 and corrects it (S is NOT substituted automatically): same matching rules
    fixed = p.verify_manual(r, "HLAS0019", confirmed=True)
    assert fixed.manual.source.value == "user_corrected" and fixed.decision.status is Status.NO_ALERT_FOUND
    assert "Batch checked: HLAS0019" in fixed.decision.explanation
    # a user who cannot confirm keeps Unable to verify
    assert p.verify_manual(r, "HLA50019", confirmed=False).decision.status is Status.UNABLE_TO_VERIFY
