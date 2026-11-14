"""End-to-end pipeline tests (milestone M5).

Images are SYNTHETIC rendered labels built from public dataset values. They demonstrate that the
integrated software behaves correctly; they are NOT an accuracy evaluation on real photographs.
"""
from __future__ import annotations

import logging
import shutil
from datetime import date

import pytest

from medcheck import config, pipeline as pl
from medcheck.dataset import load_dataset
from medcheck.models import Status, SystemFailure
from medcheck.ocr import OCREngineUnavailable, OCRTimeout, find_engine
from medcheck.pipeline import MedCheckPipeline
from tests.helpers import encode, font_path, render_label

def _engine_available() -> bool:
    try:
        find_engine()
        return True
    except OCREngineUnavailable:
        return False


pytestmark = [
    pytest.mark.skipif(font_path() is None, reason="no TrueType font"),
    pytest.mark.skipif(not _engine_available(), reason="Tesseract not installed"),
]


@pytest.fixture(scope="module")
def pipe():
    p = MedCheckPipeline.load()
    assert p.dataset_failure is None
    return p


def label(*lines):
    return encode(render_label(list(lines)), "PNG")


# ---- the four outcomes, through real OCR ----
def test_alert_found_for_listed_batch_with_product(pipe):
    r = pipe.check(label("Linzotal 600", "Linezolid Tablets IP 600 mg", "B.No.: TG261185    Mfg: 05/2026", "Exp: 04/2028"))
    assert r.decision.status is Status.ALERT_FOUND, (r.decision, r.extraction and r.extraction.batch)
    assert r.matched_record.serial == 4 and r.ocr_passes >= 2
    assert any("has not been approved" in c for c in r.decision.caveats)  # expiry caveat, no verdict


def test_no_alert_for_unlisted_batch(pipe):
    r = pipe.check(label("Paracetamol Tablets IP 500 mg", "B.No.: ZX99001Q    Mfg: 01/2026", "Exp: 12/2028"))
    assert r.decision.status is Status.NO_ALERT_FOUND
    assert "2026" in " ".join(r.decision.caveats) and "safe" not in r.decision.headline.lower()


def test_unable_when_no_batch_label(pipe):
    r = pipe.check(label("Paracetamol Tablets IP 500 mg", "Keep in a cool dry place", "Exp: 12/2028"))
    assert r.decision.status is Status.UNABLE_TO_VERIFY and r.decision.reason_code == "batch_not_found"


def test_unable_for_confusable_collision_serials_38_157(pipe):
    r = pipe.check(label("Bupivacaine Hydrochloride In Dextrose Injection USP", "B.No.: BKBP02601", "Mfg: 05/2026   Exp: 04/2028"))
    assert r.decision.status is Status.UNABLE_TO_VERIFY, r.decision
    assert r.decision.reason_code in ("batch_collision", "batch_ambiguous")  # either way: no alert, no clean negative
    assert r.matched_record is None


def test_expired_is_never_emitted_while_policy_unapproved(pipe):
    r = pipe.check(label("Paracetamol Tablets IP 500 mg", "B.No.: ZX99001Q    Mfg: 01/2019", "Exp: 01/2020"))
    assert r.decision.status is Status.NO_ALERT_FOUND  # month-only expiry policy is OPEN


def test_product_name_alone_cannot_alert(pipe):
    r = pipe.check(label("Linzotal 600", "Linezolid Tablets IP 600 mg", "B.No.: QQ778899    Exp: 04/2028"))
    assert r.decision.status is not Status.ALERT_FOUND and r.matched_record is None


# ---- failure types are distinct ----
def test_bad_upload_is_a_rejection_not_a_status(pipe):
    r = pipe.check(b"not an image")
    assert r.rejection is not None and r.decision is None


def test_dataset_failure_is_system_error_never_no_alert(tmp_path):
    p = MedCheckPipeline.load(csv_path=tmp_path / "missing.csv", manifest_path=tmp_path / "m.json")
    r = p.check(label("B.No.: ZX99001Q"))
    assert r.decision.status is None and r.decision.system_failure is SystemFailure.DATASET_MISSING


def test_tampered_dataset_is_system_error(tmp_path):
    csv_p, man_p = tmp_path / "d.csv", tmp_path / "m.json"
    shutil.copy(config.DATASET_MANIFEST_PATH, man_p)
    csv_p.write_bytes(config.CANONICAL_DATASET_PATH.read_bytes().replace(b"TG261185", b"TG261186"))
    r = MedCheckPipeline.load(csv_path=csv_p, manifest_path=man_p).check(label("B.No.: TG261185"))
    assert r.decision.system_failure is SystemFailure.DATASET_INTEGRITY and r.decision.status is None


def test_no_ocr_engine_at_all_is_system_error(pipe):
    none = MedCheckPipeline(pipe.dataset, rapid_engine=None, tesseract_engine=None)
    r = none.check(label("B.No.: ZX99001Q"))
    assert r.decision.system_failure is SystemFailure.OCR_ENGINE_UNAVAILABLE and r.decision.status is None


def test_tesseract_only_failures_are_system_errors(pipe, monkeypatch):
    only_tess = MedCheckPipeline(pipe.dataset, rapid_engine=None)
    monkeypatch.setattr(pl, "run_ocr", lambda *a, **k: (_ for _ in ()).throw(OCREngineUnavailable("x")))
    assert only_tess.check(label("B.No.: ZX99001Q")).decision.system_failure is SystemFailure.OCR_ENGINE_UNAVAILABLE
    monkeypatch.setattr(pl, "run_ocr", lambda *a, **k: (_ for _ in ()).throw(OCRTimeout("x")))
    assert only_tess.check(label("B.No.: ZX99001Q")).decision.system_failure is SystemFailure.OCR_TIMEOUT


def test_tesseract_failure_is_not_fatal_while_rapidocr_works(pipe, monkeypatch):
    monkeypatch.setattr(pl, "run_ocr", lambda *a, **k: (_ for _ in ()).throw(OCREngineUnavailable("x")))
    r = pipe.check(label("Paracetamol Tablets IP 500 mg", "B.No.: ZX99001Q    Mfg: 01/2026"))
    assert r.decision.system_failure is None and r.engines == ("rapidocr",)
    assert any("Tesseract is unavailable" in n for n in r.notes)


def test_unexpected_exception_is_internal_error_without_leaking(pipe, monkeypatch, caplog):
    def boom(_):
        raise RuntimeError("SECRETTEXT 0l25038 C:\\Users\\someone")
    monkeypatch.setattr(pl, "extract", boom)
    with caplog.at_level(logging.DEBUG):
        r = pipe.check(label("B.No.: ZX99001Q"))
    assert r.decision.system_failure is SystemFailure.INTERNAL
    assert "SECRETTEXT" not in r.decision.explanation
    assert "SECRETTEXT" not in caplog.text and "RuntimeError" in caplog.text  # exception type only


# ---- privacy ----
def test_no_files_written_and_no_ocr_text_logged(pipe, tmp_path, monkeypatch, caplog):
    monkeypatch.chdir(tmp_path)
    with caplog.at_level(logging.DEBUG):
        pipe.check(label("Linzotal 600", "Linezolid Tablets IP 600 mg", "B.No.: TG261185", "Exp: 04/2028"))
    assert list(tmp_path.iterdir()) == []
    for needle in ("TG261185", "Linezolid", "Linzotal"):
        assert needle not in caplog.text


def test_dataset_loaded_once_and_reused(pipe):
    assert pipe.dataset is not None and len(pipe.dataset) == 220
