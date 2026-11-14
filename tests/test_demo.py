"""The demonstration must be true: every SYNTHETIC fixture yields its documented headline through the real pipeline,
and every fixture stays visibly labelled as test material (the banner is legible to OCR, so it is in-frame)."""
from __future__ import annotations

import csv
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import make_demo_images as demo  # noqa: E402

from medcheck.ocr import OCREngineUnavailable, find_engine  # noqa: E402
from medcheck.pipeline import MedCheckPipeline  # noqa: E402

CONFIRMED_HEADLINE = {"FIXTURE_3_no_alert_after_confirmation.png": "No alert found"}  # after the user confirms the batch


def _ok():
    try:
        find_engine()
        return demo._render(["x"]) is not None and any(Path(p).exists() for p in demo.FONTS)
    except OCREngineUnavailable:
        return False


def test_every_fixture_is_named_and_listed_as_synthetic(tmp_path):
    demo.build(tmp_path)
    rows = list(csv.DictReader((tmp_path / "fixtures_manifest.csv").open(encoding="utf-8")))
    assert {r["file"] for r in rows} == set(demo.DEMO_SET) and all(r["file"].startswith("FIXTURE_") for r in rows)
    assert all(r["kind"] == "SYNTHETIC_FIXTURE" for r in rows)


@pytest.mark.skipif(not _ok(), reason="needs Tesseract and a TrueType font")
def test_every_demo_image_produces_its_documented_result(tmp_path):
    expected = demo.build(tmp_path)
    pipe = MedCheckPipeline.load()
    for name, (headline, _why) in expected.items():
        res = pipe.check((tmp_path / name).read_bytes())
        assert res.decision is not None and res.decision.headline == headline, (name, res.decision)
        assert "FIXTURE" in res.extraction.product_text.upper(), name  # the in-frame banner is legible
        serial = demo.DEMO_SET[name][2]
        if serial is not None:
            assert res.matched_record is not None and res.matched_record.serial == serial, name
            assert res.decision.action_check, name  # every alert says what to check on the pack
        if name in CONFIRMED_HEADLINE:  # D-026: a clean negative needs the user's confirmation of the printed batch
            assert res.decision.reason_code == "ocr_batch_unconfirmed"
            done = pipe.verify_manual(res, res.extraction.batch.raw, confirmed=True)
            assert done.decision.headline == CONFIRMED_HEADLINE[name], (name, done.decision)
    res7 = pipe.check((tmp_path / "FIXTURE_7_alert_listed_neighbour.png").read_bytes())
    assert any("Listed serial(s) 118" in e for e in res7.decision.evidence)


@pytest.mark.skipif(not _ok(), reason="needs Tesseract and a TrueType font")
def test_fixture_check_writes_its_own_labelled_folder_never_the_real_photo_runs(tmp_path):
    import run_fixture_check

    assert run_fixture_check.main(["--out", str(tmp_path)]) == 0
    (run,) = list(tmp_path.iterdir())
    assert run.name.startswith("fixture_run_") and not (tmp_path / "runs").exists()
    report = (run / "fixture_report.md").read_text(encoding="utf-8")
    assert "NOT REAL-WORLD EVIDENCE" in report and "7 of 7" in report
