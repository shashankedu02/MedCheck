"""Test helpers: synthetic label images. These are rendered text, NOT real photographs."""
from __future__ import annotations

import io
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

_FONT_CANDIDATES = [r"C:\Windows\Fonts\arial.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]


def font_path() -> str | None:
    return next((p for p in _FONT_CANDIDATES if Path(p).exists()), None)


def render_label(lines: list[str], size: int = 46, width: int = 1300, bg: str = "white", fg: str = "black") -> Image.Image:
    fp = font_path()
    font = ImageFont.truetype(fp, size) if fp else ImageFont.load_default()
    img = Image.new("RGB", (width, max(340, 40 + len(lines) * (size + 30))), bg)
    d = ImageDraw.Draw(img)
    for i, line in enumerate(lines):
        d.text((30, 25 + i * (size + 30)), line, font=font, fill=fg)
    return img


def encode(img: Image.Image, fmt: str = "PNG", **kw) -> bytes:
    buf = io.BytesIO()
    img.save(buf, format=fmt, **kw)
    return buf.getvalue()
