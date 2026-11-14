"""Shared helpers for the V2 manual-testing review. Diagnostic only; not imported by the app.
Held-out photographs are refused (evaluation/heldout_ids.txt)."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from medcheck import real_eval as ev  # noqa: E402

PHOTOS = ROOT / "evaluation" / "incoming_photos"
OUT = Path(__file__).resolve().parent / "out"
OUT.mkdir(exist_ok=True)
HELDOUT = ev.load_heldout(ROOT / "evaluation" / "heldout_ids.txt")
REFERENCE = ev.load_reference(ROOT / "evaluation" / "reference_batches.csv")
CERTAIN = {k: v[0] for k, v in REFERENCE.items() if v[1] == "certain"}
DEV = [i for i in range(1, 28) if f"T{i:03d}" not in HELDOUT]


def photo_path(i: int) -> Path:
    assert f"T{i:03d}" not in HELDOUT, "held-out photographs must not be opened"
    return PHOTOS / f"{i}.jpeg"


def photo_bytes(i: int) -> bytes:
    return photo_path(i).read_bytes()
