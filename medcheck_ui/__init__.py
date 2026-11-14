"""Presentation layer for MedCheck (3D stage, theme, story). Frontend only: it holds no matching, OCR or decision logic
and receives nothing but the phase and the status name of a finished decision."""
from __future__ import annotations

import os


def plain_ui() -> bool:
    """MEDCHECK_PLAIN_UI=1 restores the plain interface (no theme, story or 3D stage): the demonstration safety net."""
    return os.environ.get("MEDCHECK_PLAIN_UI", "").strip().lower() not in ("", "0", "false", "no")
