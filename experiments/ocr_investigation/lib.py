"""Diagnostic helpers for the OCR failure investigation. NOT production code.

Imports production modules read-only (OCR runner, extraction) so experiments measure what the
real pipeline would do. Nothing here is imported by the app. Outputs go to ./out (git-ignored).
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from medcheck.extraction import extract_from_lines  # noqa: E402
from medcheck.normalization import batch_key  # noqa: E402
from medcheck.ocr import find_engine, run_pass  # noqa: E402

PHOTOS = ROOT / "evaluation" / "incoming_photos"
OUT = Path(__file__).resolve().parent / "out"
OUT.mkdir(exist_ok=True)

HELDOUT = {9, 12, 15, 18, 21, 24, 27}  # never opened, viewed or run during this investigation
DEV = [i for i in range(1, 28) if i not in HELDOUT]
ENGINE = find_engine()

LABEL_WORDS = re.compile(r"B\.?\s?NO|BATCH|\bMFG|\bMFD|\bEXP|M\.?R\.?P|TABLETS|CAPSULES|MANUFACTURED", re.I)


def load(i: int) -> Image.Image:
    assert i not in HELDOUT, "held-out photographs must not be used in diagnostics"
    im = Image.open(PHOTOS / f"{i}.jpeg")
    im.load()
    return im.convert("RGB")


def to_gray(img) -> np.ndarray:
    a = np.asarray(img)
    return cv2.cvtColor(a, cv2.COLOR_RGB2GRAY) if a.ndim == 3 else a


def ocr(pixels: np.ndarray, psm: int = 11, timeout: float = 40):
    return run_pass(ENGINE, pixels, "x", psm, timeout)


def fields(p):
    pf = extract_from_lines(list(p.lines))
    return pf


def stats(p) -> dict:
    """Image-independent signals: did the label words appear, did a labelled batch/date parse."""
    text = "\n".join(p.lines)
    pf = fields(p)
    good = [w for w in p.words if len(w.text) >= 3 and w.text.isalpha()]
    return {
        "label_words": len(LABEL_WORDS.findall(text)),
        "batch_cands": list(pf.batch_candidates),
        "exp": list(pf.expiry_candidates),
        "mfg": list(pf.mfg_candidates),
        "alpha_words": len(good),
        "mean_conf": round(float(np.mean([w.confidence for w in good])), 1) if good else 0.0,
    }


def rotate(img: Image.Image, deg_ccw: int) -> Image.Image:
    return img.rotate(deg_ccw, expand=True) if deg_ccw else img


def key(s: str) -> str:
    return batch_key(s).key
