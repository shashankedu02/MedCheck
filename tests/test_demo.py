"""The README demonstration must be true: every demo image yields its documented headline."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import make_demo_images as demo  # noqa: E402

from medcheck.ocr import OCREngineUnavailable, find_engine  # noqa: E402
from medcheck.pipeline import MedCheckPipeline  # noqa: E402


ALERT_SERIALS = {"1_alert_found.png": 4, "2_alert_found_trailing_comma.png": 150}


def _ok():
    try:
        find_engine()
        return demo._render(["x"]) is not None and any(Path(p).exists() for p in demo.FONTS)
    except OCREngineUnavailable:
        return False


@pytest.mark.skipif(not _ok(), reason="needs Tesseract and a TrueType font")
def test_every_demo_image_produces_its_documented_result(tmp_path):
    expected = demo.build(tmp_path)
    pipe = MedCheckPipeline.load()
    for name, (headline, _why) in expected.items():
        res = pipe.check((tmp_path / name).read_bytes())
        assert res.decision is not None and res.decision.headline == headline, (name, res.decision)
        if name in ALERT_SERIALS:  # the README names the matched serial
            assert res.matched_record is not None and res.matched_record.serial == ALERT_SERIALS[name], name
