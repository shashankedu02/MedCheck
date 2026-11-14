"""Image validation tests (milestone M4)."""
from __future__ import annotations

import io

import pytest
from PIL import Image

from medcheck import config
from medcheck.image_input import ImageRejected, load_image
from tests.helpers import encode, render_label


def _img(w=800, h=500, color="white"):
    return Image.new("RGB", (w, h), color)


@pytest.mark.parametrize("fmt", ["PNG", "JPEG", "WEBP"])
def test_valid_formats_accepted(fmt):
    v = load_image(encode(_img(), fmt))
    assert v.detected_format == fmt and v.image.mode == "RGB" and v.image.size == (800, 500)


def test_zero_bytes_rejected():
    with pytest.raises(ImageRejected) as e:
        load_image(b"")
    assert e.value.code == "empty_file"


def test_corrupt_and_non_image_bytes_rejected():
    for blob in (b"not an image at all", encode(_img(), "PNG")[:200], b"\xff\xd8\xff" + b"\x00" * 50):
        with pytest.raises(ImageRejected) as e:
            load_image(blob)
        assert e.value.code == "not_an_image"


def test_wrong_extension_does_not_matter_only_bytes():
    assert load_image(encode(_img(), "PNG")).detected_format == "PNG"  # no filename is even accepted


def test_unsupported_format_rejected():
    for fmt in ("BMP", "TIFF", "GIF"):
        with pytest.raises(ImageRejected) as e:
            load_image(encode(_img(), fmt))
        assert e.value.code == "unsupported_format"


def test_animated_webp_rejected():
    frames = [_img(400, 400, "red"), _img(400, 400, "blue")]
    blob = encode(frames[0], "WEBP", save_all=True, append_images=frames[1:], duration=100)
    with pytest.raises(ImageRejected) as e:
        load_image(blob)
    assert e.value.code == "animated_image"


def test_oversized_bytes_rejected(monkeypatch):
    monkeypatch.setattr(config, "MAX_UPLOAD_BYTES", 1000)
    with pytest.raises(ImageRejected) as e:
        load_image(encode(render_label(["x" * 20] * 5), "PNG"))
    assert e.value.code == "too_large"


def test_too_many_pixels_rejected_from_header(monkeypatch):
    monkeypatch.setattr(config, "MAX_IMAGE_PIXELS", 500_000)
    with pytest.raises(ImageRejected) as e:
        load_image(encode(_img(1200, 900), "PNG"))
    assert e.value.code == "too_many_pixels"


def test_tiny_image_rejected():
    with pytest.raises(ImageRejected) as e:
        load_image(encode(_img(100, 600), "PNG"))
    assert e.value.code == "too_small"


def test_exif_orientation_applied():
    img = _img(800, 500)
    exif = Image.Exif()
    exif[0x0112] = 6  # rotate 90 degrees clockwise when displayed
    v = load_image(encode(img, "JPEG", exif=exif))
    assert v.image.size == (500, 800)  # displayed orientation
    assert v.original_size == (800, 500)


def test_large_image_downscaled_to_working_size():
    v = load_image(encode(_img(4000, 1000), "PNG"))
    assert max(v.image.size) == config.MAX_WORKING_LONG_SIDE


def test_rejection_messages_are_user_safe():
    with pytest.raises(ImageRejected) as e:
        load_image(b"garbage")
    assert "Traceback" not in e.value.message and "\\" not in e.value.message


def test_no_files_written(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    load_image(encode(_img(), "PNG"))
    assert list(tmp_path.iterdir()) == []
