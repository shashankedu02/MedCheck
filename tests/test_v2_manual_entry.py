"""Manual batch entry: user-supplied batches use the same safeguards and are never OCR evidence."""
from __future__ import annotations

import numpy as np
import pytest
from PIL import Image

from medcheck.models import BatchSource, FieldState, Status
from medcheck.pipeline import ManualEntryError, MedCheckPipeline, ScanResult
from medcheck.regions import crop_to, detect_pack_region
from tests.helpers import encode
from tests.test_v2_pipeline import StubRapid

PHOTO = encode(Image.new("RGB", (500, 400), "white"), "PNG")
PRODUCT = ["Linzotal 600", "Linezolid Tablets IP 600 mg"]  # corroborates listed serial 4 (batch TG261185)


def checked(lines_by_view) -> tuple[MedCheckPipeline, ScanResult]:
    p = MedCheckPipeline.load(rapid_engine=StubRapid(lines_by_view), tesseract_engine=None)
    return p, p.check(PHOTO)


@pytest.fixture()
def no_batch_with_product():
    # OCR sees the product text but no batch label at all (the common real failure)
    return checked(lambda src: PRODUCT)


def test_typed_batch_with_photo_product_text_can_alert_and_is_marked_user_entered(no_batch_with_product):
    p, prior = no_batch_with_product
    assert prior.extraction.batch.state is FieldState.NOT_FOUND
    r = p.verify_manual(prior, "TG261185", confirmed=False)
    assert r.decision.status is Status.ALERT_FOUND and r.matched_record.serial == 4
    assert r.decision.batch_source is BatchSource.USER_ENTERED and r.manual.source is BatchSource.USER_ENTERED
    assert any("typed by you" in c for c in r.decision.caveats)
    assert "The batch number you entered" in r.decision.explanation
    # OCR evidence is untouched: the typed value never enters the extraction
    assert r.extraction is prior.extraction and r.extraction.batch.state is FieldState.NOT_FOUND and r.extraction.batch.raw is None


def test_user_text_never_corroborates_the_product():
    p, prior = checked(lambda src: ["Some unrelated tablets"])  # no product evidence in the photo text
    r = p.verify_manual(prior, "TG261185", confirmed=True)
    assert r.decision.status is Status.UNABLE_TO_VERIFY and r.decision.reason_code == "identity_uncorroborated"


def test_ocr_value_corrected_by_user_is_marked_corrected():
    p, prior = checked(lambda src: [*PRODUCT, "B.No.: TG261186"])  # OCR consistently read the wrong last digit
    assert prior.extraction.batch.raw == "TG261186"
    r = p.verify_manual(prior, "TG261185", confirmed=False)
    assert r.manual.source is BatchSource.USER_CORRECTED and r.decision.batch_source is BatchSource.USER_CORRECTED
    assert r.decision.status is Status.ALERT_FOUND
    assert r.extraction.batch.raw == "TG261186"  # the raw OCR reading is preserved next to the correction


def test_confirming_the_ocr_value_keeps_the_ocr_source():
    p, prior = checked(lambda src: [*PRODUCT, "B.No.: TG261185"])
    r = p.verify_manual(prior, "TG261185", confirmed=False)
    assert r.manual.source is BatchSource.OCR and r.decision.batch_source is BatchSource.OCR
    assert not any("typed by you" in c or "corrected by you" in c for c in r.decision.caveats)


def test_unlisted_manual_batch_needs_confirmation_before_no_alert_found(no_batch_with_product):
    p, prior = no_batch_with_product
    unconfirmed = p.verify_manual(prior, "ZX99001Q", confirmed=False)
    assert unconfirmed.decision.status is Status.UNABLE_TO_VERIFY and unconfirmed.decision.reason_code == "manual_entry_unconfirmed"
    confirmed = p.verify_manual(prior, "ZX99001Q", confirmed=True)
    assert confirmed.decision.status is Status.NO_ALERT_FOUND
    assert "Batch checked: ZX99001Q" in confirmed.decision.explanation
    assert any("typed by you" in c for c in confirmed.decision.caveats)
    assert "safe" not in confirmed.decision.headline.lower()


@pytest.mark.parametrize("typed", ["TG26118", "TG261186", "TG2611855", "tg261l85"])
def test_near_neighbours_of_a_listed_batch_still_abstain_when_typed(no_batch_with_product, typed):
    p, prior = no_batch_with_product
    r = p.verify_manual(prior, typed, confirmed=True)
    assert r.decision.status is Status.UNABLE_TO_VERIFY and r.decision.reason_code == "fuzzy_candidate_only"


def test_collision_pair_abstains_for_typed_batches_in_both_directions(no_batch_with_product):
    p, prior = no_batch_with_product
    for typed in ("BKBP02601", "BKBP O2601"):  # serials 38 and 157 differ only by 0 vs letter O
        r = p.verify_manual(prior, typed, confirmed=True)
        assert r.decision.status is Status.UNABLE_TO_VERIFY and r.decision.reason_code == "batch_collision", typed


def test_manual_entry_never_emits_expired_while_policy_is_unapproved(no_batch_with_product):
    p, prior = no_batch_with_product
    assert p.verify_manual(prior, "ZX99001Q", confirmed=True).decision.status is not Status.EXPIRED


@pytest.mark.parametrize("bad", ["", "   ", "AB", "ABCDEF", "x" * 31, "AB12\x00", "AB12\n34"])
def test_invalid_entries_are_rejected_with_a_friendly_error(no_batch_with_product, bad):
    p, prior = no_batch_with_product
    with pytest.raises(ManualEntryError):
        p.verify_manual(prior, bad, confirmed=True)


def test_manual_entry_needs_a_checked_photo():
    p = MedCheckPipeline.load(rapid_engine=StubRapid({}), tesseract_engine=None)
    with pytest.raises(ManualEntryError):
        p.verify_manual(ScanResult(), "TG261185", confirmed=True)


def test_manual_entry_does_not_log_the_typed_text(no_batch_with_product, caplog):
    import logging

    p, prior = no_batch_with_product
    with caplog.at_level(logging.DEBUG):
        p.verify_manual(prior, "TG261185", confirmed=True)
    assert "TG261185" not in caplog.text


# ---- pack-region detection (used to crop before OCR) ----
def _textured_pack_on_plain(size=(1200, 900), box=(500, 300, 1000, 600)):
    rng = np.random.default_rng(0)
    a = np.full((size[1], size[0], 3), 200, np.uint8)
    x0, y0, x1, y1 = box
    a[y0:y1, x0:x1] = rng.integers(60, 230, (y1 - y0, x1 - x0, 1), dtype=np.uint8)  # dense texture like foil/print
    return Image.fromarray(a)


def test_pack_region_found_on_plain_background():
    img = _textured_pack_on_plain()
    x, y, w, h = detect_pack_region(img)
    assert x <= 500 + 5 and y <= 300 + 5 and x + w >= 1000 - 5 and y + h >= 600 - 5
    assert w * h < 0.5 * img.width * img.height
    assert crop_to(img, (x, y, w, h)).size == (w, h)


def test_no_region_on_plain_or_full_frame_texture():
    assert detect_pack_region(Image.new("RGB", (800, 600), "white")) is None
    rng = np.random.default_rng(1)
    assert detect_pack_region(Image.fromarray(rng.integers(0, 255, (600, 800, 3), dtype=np.uint8))) is None
