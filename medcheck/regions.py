"""Pack-region detection: find the medicine strip/box in a photo so OCR can run on it.

Foil and printing have dense local gradients; a table or wall is smooth. We threshold local
gradient energy, close gaps and take the largest blob. Pure geometry: no ML, no network.
Returns None when nothing useful is found or the blob is almost the whole frame (cropping would
add nothing), and callers then use the full image. A crop is only ever an *additional* view.
"""
from __future__ import annotations

import cv2
import numpy as np
from PIL import Image

_MIN_AREA_FRACTION = 0.02
_MAX_AREA_FRACTION = 0.85
_PAD = 0.03


def detect_pack_region(image: Image.Image) -> tuple[int, int, int, int] | None:
    """Return (x, y, w, h) in image pixels, or None."""
    g = cv2.cvtColor(np.asarray(image.convert("RGB")), cv2.COLOR_RGB2GRAY)
    H, W = g.shape
    s = 800 / max(H, W)
    sm = cv2.GaussianBlur(cv2.resize(g, None, fx=s, fy=s, interpolation=cv2.INTER_AREA), (3, 3), 0)
    mag = cv2.magnitude(cv2.Sobel(sm, cv2.CV_32F, 1, 0), cv2.Sobel(sm, cv2.CV_32F, 0, 1))
    energy = cv2.boxFilter(mag, -1, (15, 15))
    mask = (energy > max(float(np.percentile(energy, 50)) * 2.0, 12.0)).astype(np.uint8) * 255
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (31, 31)))
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (15, 15)))
    n, _, stats, _ = cv2.connectedComponentsWithStats(mask)
    if n <= 1:
        return None
    k = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
    x, y, w, h, area = (float(v) for v in stats[k])
    if area < _MIN_AREA_FRACTION * mask.size:
        return None
    x, y, w, h = x / s, y / s, w / s, h / s
    x0, y0 = max(0, int(x - _PAD * w)), max(0, int(y - _PAD * h))
    x1, y1 = min(W, int(x + w + _PAD * w)), min(H, int(y + h + _PAD * h))
    if (x1 - x0) * (y1 - y0) > _MAX_AREA_FRACTION * W * H or min(x1 - x0, y1 - y0) < 40:
        return None
    return x0, y0, x1 - x0, y1 - y0


def crop_to(image: Image.Image, box: tuple[int, int, int, int]) -> Image.Image:
    x, y, w, h = box
    return image.crop((x, y, x + w, y + h))
