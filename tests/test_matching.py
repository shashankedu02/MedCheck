"""Matching tests (milestone M3): real dataset rows plus adversarial cases."""
from __future__ import annotations

import pytest

from medcheck.dataset import load_dataset
from medcheck.matching import DatasetIndex, match_batch
from medcheck.models import MatchOutcome as O
from medcheck.normalization import batch_key
from medcheck.product import extract_strengths, parse_product_name, score_identity


@pytest.fixture(scope="module")
def ds():
    return load_dataset()


@pytest.fixture(scope="module")
def index(ds):
    return DatasetIndex.build(ds)


def rec(ds, serial):
    return next(r for r in ds.records if r.serial == serial)


def photo_text(r):
    """Simulated perfect OCR text for a record: its own product name and manufacturer."""
    return f"{r.product_name} Batch No. {r.batch_number} Mfg {r.manufacturing_date} Exp {r.expiry_date} {r.manufactured_by}"


# ---------- product parsing ----------
def test_parse_brand_and_generic():
    p = parse_product_name("Linezolid Tablets IP 600mg (Brand Name : Linzotal 600)")
    assert p.brand_aliases == ("Linzotal 600",) and "linezolid" in p.ingredient_tokens
    assert (600.0, "mg") in p.strengths and "tablet" in p.forms


def test_na_brand_is_not_a_brand():
    assert parse_product_name("Chlorine Tablets (Brand Name : NA)").brand_aliases == ()


def test_parenthesised_alias_and_salt_words():
    p = parse_product_name("Telmisartan & Amlodipine Tablets IP (Telsa A) (Brand Name : NA)")
    assert "Telsa A" in p.brand_aliases and {"telmisartan", "amlodipine"} <= set(p.ingredient_tokens)
    q = parse_product_name("Diclofenac Potass um & Serratiopeptidase Tablets (Brand Name : Wyser?M.K)")
    assert "potass" not in q.ingredient_tokens and "diclofenac" in q.ingredient_tokens


def test_strength_extraction_units():
    assert extract_strengths("500 mg and 5GM, 250 i.u., 2.5%") == {(500.0, "mg"), (5.0, "g"), (250.0, "iu"), (2.5, "%")}


def test_identity_conflicts():
    info = parse_product_name("Linezolid Tablets IP 600mg (Brand Name : Linzotal 600)")
    assert score_identity(info, "Linezolid Tablets 400 mg").strength_conflict
    assert score_identity(info, "Linezolid Syrup 600 mg").form_conflict
    assert not score_identity(info, "Linezolid Tablets 600 mg").has_conflict


# ---------- core alert logic on real rows ----------
def test_exact_batch_with_product_confirms(ds, index):
    r = rec(ds, 4)  # Linzotal 600, TG261185
    m = match_batch(index, batch_key("TG261185"), "Linzotal 600 Linezolid Tablets IP 600mg")
    assert m.outcome is O.CONFIRMED and m.matched_serial == 4


def test_batch_alone_does_not_confirm(ds, index):
    m = match_batch(index, batch_key("TG261185"), "completely unrelated text 12345")
    assert m.outcome is O.UNCORROBORATED and m.matched_serial is None


def test_product_name_alone_never_alerts(ds, index):
    """Perfect product text but a batch not in the dataset -> no alert path."""
    r = rec(ds, 4)
    m = match_batch(index, batch_key("ZZQ99887766"), photo_text(r))
    assert m.outcome is O.NO_MATCH


def test_same_product_different_batch_is_not_an_alert(ds, index):
    m = match_batch(index, batch_key("TG261186"), photo_text(rec(ds, 4)))  # one char off
    assert m.outcome is O.FUZZY_ONLY and m.matched_serial is None


def test_strength_conflict_abstains(ds, index):
    m = match_batch(index, batch_key("TG261185"), "Linzotal Linezolid Tablets 400 mg")
    assert m.outcome is O.CONFLICT


def test_trailing_comma_batches_match_without_the_comma(ds, index):
    for serial, typed in ((150, "GTF2327C"), (153, "GBT26241")):
        m = match_batch(index, batch_key(typed), photo_text(rec(ds, serial)))
        assert m.outcome is O.CONFIRMED and m.matched_serial == serial
        assert any("punctuation" in c for c in m.source_caveats)


def test_serial_121_lowercase_l_batch_matches_only_its_own_spelling(ds, index):
    r = rec(ds, 121)
    assert match_batch(index, batch_key("0l25038"), photo_text(r)).matched_serial == 121
    assert match_batch(index, batch_key("0I25038"), photo_text(r)).outcome is O.FUZZY_ONLY  # confusable, not equal
    assert match_batch(index, batch_key("0125038"), photo_text(r)).outcome is O.FUZZY_ONLY


# ---------- required collision case: serials 38 and 157 ----------
def test_serials_38_and_157_are_a_collision_in_both_directions(ds, index):
    for typed, other in (("BKBP02601", 157), ("BKBP O2601", 38), ("BKBPO2601", 38)):
        r = rec(ds, 38 if other == 157 else 157)
        m = match_batch(index, batch_key(typed), photo_text(r))
        assert m.outcome is O.COLLISION, typed
        assert set(m.candidate_serials) == {38, 157} and m.matched_serial is None


def test_collision_even_with_perfect_product_text(ds, index):
    m = match_batch(index, batch_key("BKBP02601"), "Bupivacaine Hydrochloride In Dextrose Injection USP")
    assert m.outcome is O.COLLISION


# ---------- short batches ----------
def test_short_batch_needs_two_identity_signals(ds, index):
    r = next(x for x in ds.records if x.batch_number == "292")  # chlorine tablets, Hind Pharma
    only_ingredient = match_batch(index, batch_key("292"), "Chlorine Tablets")
    assert only_ingredient.outcome is O.UNCORROBORATED
    both = match_batch(index, batch_key("292"), "Chlorine Tablets Hind Pharma Bhopal")
    assert both.outcome is O.CONFIRMED and both.matched_serial == r.serial


def test_short_numeric_batch_without_product_never_confirms(index):
    for b in ("292", "49", "38", "090", "433", "568", "585", "291"):
        assert match_batch(index, batch_key(b), "random packaging text 2027").outcome in (O.UNCORROBORATED, O.COLLISION, O.NO_MATCH)


def test_unknown_short_batches_do_not_fuzzy_match(index):
    assert match_batch(index, batch_key("293"), "x").outcome is O.NO_MATCH  # 292 exists, but short keys retrieve exact-only


def test_empty_key_is_rejected(index):
    with pytest.raises(ValueError):
        match_batch(index, batch_key(" - "), "x")


# ---------- dataset-wide properties ----------
EXPECTED_ABSTAIN_WITH_PERFECT_TEXT = {38, 157}


def test_every_row_with_perfect_text_confirms_except_known_collisions(ds, index):
    """Records the real abstention behaviour of the full dataset."""
    abstained = set()
    for r in ds.records:
        m = match_batch(index, batch_key(r.batch_number), photo_text(r))
        if m.outcome is O.CONFIRMED:
            assert m.matched_serial == r.serial
        else:
            abstained.add(r.serial)
    assert abstained == EXPECTED_ABSTAIN_WITH_PERFECT_TEXT, sorted(abstained)


def test_no_row_confirms_with_batch_only_or_wrong_product(ds, index):
    other = rec(ds, 4)
    for r in ds.records:
        if r.serial == 4:
            continue
        assert match_batch(index, batch_key(r.batch_number), "no product information").outcome is not O.CONFIRMED
        assert match_batch(index, batch_key(r.batch_number), photo_text(other)).outcome is not O.CONFIRMED


def test_dataset_has_no_exact_key_duplicates(index):
    assert all(len(v) == 1 for v in index.by_key.values())


def test_only_known_confusable_pairs_exist(index):
    pairs = {tuple(sorted(r.serial for r in v)) for v in index.by_confusable.values() if len(v) > 1}
    assert pairs == {(38, 157)}
