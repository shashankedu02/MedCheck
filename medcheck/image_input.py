"""Validate and decode an untrusted upload entirely in memory.

Nothing is written to disk. The filename and declared MIME type are never
trusted (or even accepted): the actual bytes decide.
"""
from __future__ import annotations

import io
from dataclasses import dataclass

from PIL import Image, ImageOps, UnidentifiedImageError

from . import config


class ImageRejected(Exception):
    """The upload cannot be processed. `code` is stable; `message` is safe to show the user."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(frozen=True)
class ValidatedImage:
    image: Image.Image  # RGB, EXIF-oriented, downscaled to the working size
    detected_format: str
    original_size: tuple[int, int]  # as stored (before EXIF rotation / downscaling)


def load_image(data: bytes) -> ValidatedImage:
    if not data:
        raise ImageRejected("empty_file", "The file is empty.")
    if len(data) > config.MAX_UPLOAD_BYTES:
        raise ImageRejected("too_large", f"The file is larger than {config.MAX_UPLOAD_BYTES // (1024 * 1024)} MB.")

    Image.MAX_IMAGE_PIXELS = config.MAX_IMAGE_PIXELS  # PIL raises DecompressionBombError past 2x this
    try:
        probe = Image.open(io.BytesIO(data))
        fmt = probe.format
        size = probe.size  # read from the header; pixel data not decoded yet
        if fmt not in config.ALLOWED_IMAGE_FORMATS:
            raise ImageRejected("unsupported_format", "Unsupported image type. Please use a JPEG, PNG or WebP photo.")
        if getattr(probe, "n_frames", 1) > 1:
            raise ImageRejected("animated_image", "Animated or multi-frame images are not supported.")
        if size[0] * size[1] > config.MAX_IMAGE_PIXELS:
            raise ImageRejected("too_many_pixels", "The image has too many pixels. Please use a smaller photo.")
        if min(size) < config.MIN_IMAGE_SIDE:
            raise ImageRejected("too_small", f"The image is too small (at least {config.MIN_IMAGE_SIDE} pixels on each side is needed).")
        probe.verify()  # structural check; invalidates `probe`
        img = Image.open(io.BytesIO(data))
        img.load()
    except ImageRejected:
        raise
    except Image.DecompressionBombError as exc:
        raise ImageRejected("too_many_pixels", "The image has too many pixels. Please use a smaller photo.") from exc
    except (UnidentifiedImageError, OSError, SyntaxError, ValueError, EOFError) as exc:
        raise ImageRejected("not_an_image", "The file could not be read as an image. It may be corrupt.") from exc

    try:
        img = ImageOps.exif_transpose(img)
    except Exception:  # malformed EXIF must not crash the app; keep the stored orientation
        pass
    img = img.convert("RGB")
    long_side = max(img.size)
    if long_side > config.MAX_WORKING_LONG_SIDE:
        scale = config.MAX_WORKING_LONG_SIDE / long_side
        img = img.resize((max(1, round(img.width * scale)), max(1, round(img.height * scale))), Image.LANCZOS)
    return ValidatedImage(image=img, detected_format=fmt, original_size=size)
