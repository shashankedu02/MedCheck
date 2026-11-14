"""Local Tesseract adapter.

Design notes
* Calls the `tesseract` executable directly and passes the image on **stdin** (TSV on
  stdout), so no image is ever written to a temp file. (`pytesseract` writes temp files
  and is therefore not used at runtime.)
* Raw output is kept untouched; confidence is Tesseract's per-word value and is NOT a
  probability that the text is correct.
* Never logs image bytes or recognised text.
"""
from __future__ import annotations

import io
import os
import shutil
import subprocess
import time
from dataclasses import dataclass

import numpy as np
from PIL import Image

from . import config


class OCREngineUnavailable(Exception):
    pass


class OCRTimeout(Exception):
    pass


@dataclass(frozen=True)
class OCRWord:
    text: str
    confidence: float  # Tesseract word confidence 0-100; not a probability of correctness
    left: int
    top: int
    width: int
    height: int


@dataclass(frozen=True)
class OCRPass:
    variant_id: str
    psm: int
    lines: tuple[str, ...]  # raw recognised lines, in reading order
    words: tuple[OCRWord, ...]

    @property
    def text(self) -> str:
        return "\n".join(self.lines)


@dataclass(frozen=True)
class EngineInfo:
    command: str
    version: str


def find_engine() -> EngineInfo:
    """Locate Tesseract and read its version, or raise OCREngineUnavailable."""
    for cand in config.tesseract_cmd_candidates():
        exe = shutil.which(cand) or (cand if os.path.isfile(cand) else None)
        if not exe:
            continue
        try:
            r = subprocess.run([exe, "--version"], capture_output=True, text=True, timeout=10)
        except (OSError, subprocess.SubprocessError):
            continue
        out = (r.stdout or r.stderr).strip()
        if r.returncode == 0 and out.lower().startswith("tesseract"):
            return EngineInfo(exe, out.splitlines()[0])
    raise OCREngineUnavailable("Tesseract executable not found")


def _png_bytes(pixels: np.ndarray) -> bytes:
    buf = io.BytesIO()
    Image.fromarray(pixels).save(buf, format="PNG")
    return buf.getvalue()


def parse_tsv(tsv: str) -> tuple[tuple[str, ...], tuple[OCRWord, ...]]:
    """Group Tesseract TSV word rows into lines (block, paragraph, line) and word objects."""
    lines: dict[tuple[int, int, int], list[str]] = {}
    words: list[OCRWord] = []
    for row in tsv.splitlines()[1:]:
        cols = row.split("\t")
        if len(cols) < 12 or cols[0] != "5":
            continue
        text = cols[11].strip()
        if not text:
            continue
        try:
            conf = float(cols[10])
            key = (int(cols[2]), int(cols[3]), int(cols[4]))
            box = (int(cols[6]), int(cols[7]), int(cols[8]), int(cols[9]))
        except ValueError:
            continue
        lines.setdefault(key, []).append(text)
        words.append(OCRWord(text, conf, *box))
    return tuple(" ".join(v) for _, v in sorted(lines.items())), tuple(words)


def run_pass(engine: EngineInfo, pixels: np.ndarray, variant_id: str, psm: int, timeout: float) -> OCRPass:
    cmd = [engine.command, "stdin", "stdout", "-l", config.OCR_LANGUAGE, "--psm", str(psm), "--oem", "3",
           "-c", "preserve_interword_spaces=1", "tsv"]
    try:
        r = subprocess.run(cmd, input=_png_bytes(pixels), capture_output=True, timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        raise OCRTimeout("Tesseract timed out") from exc
    except OSError as exc:
        raise OCREngineUnavailable("Tesseract could not be started") from exc
    if r.returncode != 0:
        raise OCREngineUnavailable("Tesseract failed to run")  # stderr deliberately not echoed
    lines, words = parse_tsv(r.stdout.decode("utf-8", errors="replace"))
    return OCRPass(variant_id, psm, lines, words)


def run_ocr(variants, engine: EngineInfo | None = None) -> tuple[list[OCRPass], EngineInfo]:
    """Run each variant under each configured page-segmentation mode within a total time budget."""
    engine = engine or find_engine()
    deadline = time.monotonic() + config.OCR_TOTAL_BUDGET_SECONDS
    passes: list[OCRPass] = []
    for v in variants:
        for psm in config.OCR_PSM_MODES:
            remaining = deadline - time.monotonic()
            if remaining <= 1:
                break
            passes.append(run_pass(engine, v.pixels, v.variant_id, psm, min(config.OCR_TIMEOUT_SECONDS, remaining)))
    if not passes:
        raise OCRTimeout("OCR time budget exhausted before any pass completed")
    return passes, engine
