"""Bounded, deterministic preprocessing variants. The original is never modified.

Each variant is a different *reading* of the same photo. OCR results from the
variants are compared field by field (see extraction.py); disagreement on the
batch causes abstention, so a variant can never invent an agreeable answer.
"""
from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np
from PIL import Image

from . import config

_UPSCALE_BELOW_LONG_SIDE = 1600


@dataclass(frozen=True)
class Variant:
    variant_id: str
    description: str
    pixels: np.ndarray  # uint8 grayscale, 2-D


def make_variants(image: Image.Image) -> list[Variant]:
    rgb = np.asarray(image.convert("RGB"))
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)

    long_side = max(gray.shape)
    notes = []
    if long_side < _UPSCALE_BELOW_LONG_SIDE:
        factor = min(2.0, _UPSCALE_BELOW_LONG_SIDE / long_side)
        gray = cv2.resize(gray, None, fx=factor, fy=factor, interpolation=cv2.INTER_CUBIC)
        notes.append(f"upscaled x{factor:.2f}")
    if float(np.median(gray)) < 100:  # light text on a dark background reads poorly
        gray = 255 - gray
        notes.append("inverted (dark background)")
    base = ", ".join(notes) or "no geometric change"

    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(gray)
    blurred = cv2.GaussianBlur(clahe, (3, 3), 0)
    _, otsu = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    adaptive = cv2.adaptiveThreshold(clahe, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 15)

    variants = [
        Variant("gray", f"grayscale ({base})", gray),
        Variant("clahe", "grayscale + CLAHE contrast", clahe),
        Variant("otsu", "CLAHE + light blur + Otsu threshold", otsu),
        Variant("adaptive", "CLAHE + adaptive Gaussian threshold", adaptive),
    ]
    return variants[: config.MAX_PREPROCESS_VARIANTS]
