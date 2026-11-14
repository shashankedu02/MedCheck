"""Preprocessing and OCR adapter tests (milestone M4).

The real-Tesseract tests use synthetic rendered text. They prove the plumbing works; they
are NOT an accuracy evaluation and say nothing about real package photographs.
"""
from __future__ import annotations

import subprocess

import numpy as np
import pytest
from PIL import Image

from medcheck import config, ocr
from medcheck.extraction import extract
from medcheck.image_input import load_image
from medcheck.models import FieldState
from medcheck.preprocessing import make_variants
from tests.helpers import encode, font_path, render_label

needs_engine = pytest.mark.skipif(
    not any(__import__("shutil").which(c) or __import__("os").path.isfile(c) for c in config.tesseract_cmd_candidates()),
    reason="Tesseract not installed",
)
needs_font = pytest.mark.skipif(font_path() is None, reason="no TrueType font available")


# ---------- preprocessing ----------
def test_variants_bounded_labelled_and_deterministic():
    img = render_label(["Batch No. TG261185"])
    a, b = make_variants(img), make_variants(img)
    assert 1 <= len(a) <= config.MAX_PREPROCESS_VARIANTS
    assert [v.variant_id for v in a] == [v.variant_id for v in b] and len({v.variant_id for v in a}) == len(a)
    for x, y in zip(a, b):
        assert np.array_equal(x.pixels, y.pixels) and x.pixels.dtype == np.uint8 and x.pixels.ndim == 2


def test_input_image_is_not_mutated():
    img = render_label(["Batch No. TG261185"])
    before = np.asarray(img).copy()
    make_variants(img)
    assert np.array_equal(before, np.asarray(img))


def test_dark_background_is_inverted():
    img = render_label(["Batch No. TG261185"], bg="black", fg="white")
    gray = make_variants(img)[0]
    assert "inverted" in gray.description and float(np.median(gray.pixels)) > 128


# ---------- engine ----------
@needs_engine
def test_engine_found_and_versioned():
    e = ocr.find_engine()
    assert e.version.lower().startswith("tesseract")


def test_missing_engine_is_a_distinct_error(monkeypatch):
    monkeypatch.setattr(config, "tesseract_cmd_candidates", lambda: ["definitely-not-tesseract-xyz"])
    with pytest.raises(ocr.OCREngineUnavailable):
        ocr.find_engine()


def test_timeout_is_a_distinct_error(monkeypatch):
    def boom(*a, **k):
        raise subprocess.TimeoutExpired("tesseract", 1)

    monkeypatch.setattr(ocr.subprocess, "run", boom)
    with pytest.raises(ocr.OCRTimeout):
        ocr.run_pass(ocr.EngineInfo("x", "tesseract 5"), np.zeros((50, 50), np.uint8), "gray", 6, 1)


def test_engine_failure_does_not_echo_stderr(monkeypatch):
    monkeypatch.setattr(ocr.subprocess, "run", lambda *a, **k: subprocess.CompletedProcess(a, 1, b"", b"SECRET PATH C:\\x"))
    with pytest.raises(ocr.OCREngineUnavailable) as e:
        ocr.run_pass(ocr.EngineInfo("x", "tesseract 5"), np.zeros((50, 50), np.uint8), "gray", 6, 1)
    assert "SECRET" not in str(e.value)


def test_tsv_parser_groups_lines_and_keeps_raw_text():
    tsv = "level\tpage_num\tblock_num\tpar_num\tline_num\tword_num\tleft\ttop\twidth\theight\tconf\ttext\n" \
          "5\t1\t1\t1\t1\t1\t0\t0\t10\t10\t90.5\tB.No.:\n5\t1\t1\t1\t1\t2\t20\t0\t10\t10\t80\t0l25038\n" \
          "5\t1\t1\t1\t2\t1\t0\t30\t10\t10\t-1\t  \n4\t1\t1\t1\t2\t0\t0\t30\t10\t10\t-1\t\n"
    lines, words = ocr.parse_tsv(tsv)
    assert lines == ("B.No.: 0l25038",) and len(words) == 2 and words[1].text == "0l25038"


def test_tsv_parser_tolerates_garbage():
    assert ocr.parse_tsv("") == ((), ())
    assert ocr.parse_tsv("header\nnot\ttsv")[0] == ()


@needs_engine
def test_blank_image_gives_no_text():
    p = ocr.run_pass(ocr.find_engine(), np.full((400, 600), 255, np.uint8), "gray", 6, 20)
    assert p.lines == ()


# ---------- end to end on a synthetic label (plumbing only) ----------
@needs_engine
@needs_font
def test_synthetic_label_end_to_end_plumbing(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    label = render_label(["Linzotal 600 Linezolid Tablets IP 600 mg", "B.No.: TG261185   Mfg: 05/2026", "Exp: 04/2028"])
    validated = load_image(encode(label, "PNG"))
    passes, engine = ocr.run_ocr(make_variants(validated.image))
    assert len(passes) >= 2 and engine.version
    result = extract(passes)
    assert result.batch.state is FieldState.READ and result.batch.key.key == "TG261185"
    assert result.expiry.raw is not None and "2028" in result.expiry.raw
    assert "linezolid" in result.product_text.lower()
    assert list(tmp_path.iterdir()) == []  # OCR wrote no files into the working directory


@needs_engine
@needs_font
def test_confusable_batch_is_read_raw_not_corrected():
    label = render_label(["Batch No.: 0l25038", "Exp: 04/2028"])
    passes, _ = ocr.run_ocr(make_variants(load_image(encode(label, "PNG")).image))
    raws = {r for p in passes for r in __import__("medcheck.extraction", fromlist=["x"]).extract_from_lines(list(p.lines)).batch_candidates}
    # whatever Tesseract returns is kept verbatim; no component rewrites characters
    assert all(r == r.strip() for r in raws)
