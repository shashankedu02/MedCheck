"""Local RapidOCR adapter (primary OCR engine; Tesseract stays as extra evidence/fallback).

RapidOCR (Apache-2.0) runs PaddleOCR-derived ONNX models through onnxruntime. The three model
files ship inside the pip wheel, so nothing is downloaded at run time and no network is used.
Like the Tesseract adapter: image stays in memory, recognised text is never logged, and the
per-line score is the engine's own value, NOT a probability that the text is correct.
"""
from __future__ import annotations

import hashlib
import logging
from importlib import metadata
from pathlib import Path

import numpy as np

from . import config
from .ocr import OCREngineUnavailable, OCRPass, OCRWord

ENGINE_NAME = "rapidocr"


def verify_models(models_dir: Path | None = None, expected: dict[str, str] | None = None) -> None:
    """Fail closed unless every packaged model file exists and matches its pinned SHA-256."""
    expected = config.RAPIDOCR_MODEL_SHA256 if expected is None else expected
    if models_dir is None:
        import importlib.util

        spec = importlib.util.find_spec("rapidocr_onnxruntime")
        if spec is None or not spec.origin:
            raise OCREngineUnavailable("RapidOCR is not installed")
        models_dir = Path(spec.origin).parent / "models"
    for name, digest in expected.items():
        f = models_dir / name
        if not f.is_file() or hashlib.sha256(f.read_bytes()).hexdigest() != digest:
            raise OCREngineUnavailable("RapidOCR model files failed their integrity check")


class RapidEngine:
    name = ENGINE_NAME

    def __init__(self) -> None:
        self._ocr = None
        self._version: str | None = None

    @property
    def version(self) -> str:
        if self._version is None:
            try:
                self._version = f"rapidocr-onnxruntime {metadata.version('rapidocr-onnxruntime')}"
            except metadata.PackageNotFoundError:
                self._version = "rapidocr-onnxruntime (unknown version)"
        return self._version

    def _engine(self):
        if self._ocr is None:
            verify_models()
            try:
                logging.getLogger("RapidOCR").setLevel(logging.ERROR)
                from rapidocr_onnxruntime import RapidOCR  # imported lazily: optional at import time

                self._ocr = RapidOCR()
            except Exception as exc:  # noqa: BLE001 - missing package, missing model, bad runtime
                raise OCREngineUnavailable("RapidOCR could not be loaded") from exc
        return self._ocr

    def check_available(self) -> None:
        self._engine()

    def run(self, rgb: np.ndarray, source: str) -> OCRPass:
        """`rgb`: HxWx3 uint8 RGB (or 2-D gray). Returns raw lines in the engine's reading order."""
        engine = self._engine()
        arr = np.ascontiguousarray(rgb)
        if arr.ndim == 3:
            arr = np.ascontiguousarray(arr[..., ::-1])  # RapidOCR expects BGR
        try:
            result, _ = engine(arr)
        except Exception as exc:  # noqa: BLE001
            raise OCREngineUnavailable("RapidOCR failed to run") from exc  # message deliberately generic
        words: list[OCRWord] = []
        lines: list[str] = []
        edge: list[int] = []
        H, W = arr.shape[:2]
        margin = max(config.EDGE_MARGIN_MIN_PX, int(config.EDGE_MARGIN_FRACTION * max(H, W)))
        for box, text, score in result or []:
            text = str(text).strip()
            if not text:
                continue
            xs, ys = [p[0] for p in box], [p[1] for p in box]
            words.append(OCRWord(text, float(score) * 100.0, int(min(xs)), int(min(ys)), int(max(xs) - min(xs)), int(max(ys) - min(ys))))
            if min(xs) <= margin or min(ys) <= margin or max(xs) >= W - margin or max(ys) >= H - margin:
                edge.append(len(lines))
            lines.append(text)
        return OCRPass(source, 0, tuple(lines), tuple(words), engine=ENGINE_NAME, source=source, edge_lines=tuple(edge))
