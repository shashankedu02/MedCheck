"""Normalization and date tests (milestone M2)."""
from __future__ import annotations

from datetime import date

import pytest

from medcheck.dates import assess_expiry, manufacture_after_expiry, parse_month_year
from medcheck.models import ExpiryOutcome
from medcheck.normalization import batch_key, normalize_text, tokens


# ---- batch keys ----
def test_raw_value_is_preserved():
    bk = batch_key("  GTF2327C, ")
    assert bk.raw == "  GTF2327C, " and bk.key == "GTF2327C"


@pytest.mark.parametrize("raw,key", [("090", "090"), ("02T65", "02T65"), ("0l25038", "0L25038"), ("BKBP O2601", "BKBPO2601"),
                                    ("TG-26/1185", "TG261185"), ("GBT26241,", "GBT26241")])
def test_keys_keep_leading_zeros_and_letters(raw, key):
    assert batch_key(raw).key == key


def test_confusables_are_not_substituted_in_the_key():
    assert batch_key("BKBP02601").key != batch_key("BKBP O2601").key
    assert batch_key("A0").key != batch_key("AO").key
    assert batch_key("I1").key != batch_key("11").key
    assert batch_key("S5").key != batch_key("55").key
    assert batch_key("B8").key != batch_key("88").key


def test_confusable_key_exists_only_for_ambiguity_detection():
    assert batch_key("BKBP02601").confusable_key == batch_key("BKBP O2601").confusable_key
    assert batch_key("0l25038").confusable_key == batch_key("0I25038").confusable_key == batch_key("0125038").confusable_key


def test_unicode_punctuation_and_idempotence():
    bk = batch_key("AB–123 X")  # en dash, no-break space
    assert bk.key == "AB123X"
    assert batch_key(bk.key).key == bk.key
    assert "removed_non_alphanumeric" in bk.transformations


def test_empty_after_normalization():
    assert batch_key(" -,. ").key == ""


def test_text_normalization_and_tokens():
    assert normalize_text("  Rosuvastatin   Tablets IP ") == "rosuvastatin tablets ip"
    assert tokens("Linezolid Tablets IP 600mg") == ["linezolid", "tablets", "ip", "600mg"]


# ---- dates ----
@pytest.mark.parametrize("raw,ym", [("08/2027", (2027, 8)), ("8-27", (2027, 8)), ("AUG 2027", (2027, 8)), ("Aug-2027", (2027, 8)),
                                   ("08.27", (2027, 8)), ("2027-08", (2027, 8)), ("Sept 2027", (2027, 9)), ("JAN27", (2027, 1)),
                                   ("MAR.2026", (2026, 3))])
def test_supported_month_year_formats(raw, ym):
    p = parse_month_year(raw)
    assert p is not None and (p.year, p.month) == ym and p.raw == raw


@pytest.mark.parametrize("raw", [None, "", "  ", "13/2027", "00/2027", "15/08/2027", "2027", "soon", "08/1850", "ABC 2027", "08/2027 09/2027"])
def test_unsupported_or_ambiguous_dates_are_rejected(raw):
    assert parse_month_year(raw) is None


def test_expired_never_emitted_while_policy_unapproved():
    for raw in ("01/2020", "12/2099", "Jun-2025"):
        a = assess_expiry(raw, date(2026, 11, 14), policy_approved=False)
        assert a.outcome is ExpiryOutcome.UNDETERMINED and "not been approved" in a.note


def test_not_read_and_unparseable():
    assert assess_expiry(None, date(2026, 1, 1), False).outcome is ExpiryOutcome.NOT_READ
    assert assess_expiry("garbage", date(2026, 1, 1), False).outcome is ExpiryOutcome.UNPARSEABLE


def test_approved_policy_boundary_is_end_of_printed_month():
    today_last = date(2026, 11, 30)
    assert assess_expiry("11/2026", today_last, True).outcome is ExpiryOutcome.NOT_EXPIRED
    assert assess_expiry("11/2026", date(2026, 12, 1), True).outcome is ExpiryOutcome.EXPIRED
    assert assess_expiry("02/2028", date(2028, 2, 29), True).outcome is ExpiryOutcome.NOT_EXPIRED  # leap year


def test_expiry_before_manufacture_flagged():
    assert manufacture_after_expiry("Jul-2025", "Jun-2025")
    assert not manufacture_after_expiry("Jun-2025", "Jul-2025")
    assert not manufacture_after_expiry(None, "Jun-2025")
