"""Conservative, deterministic comparison keys. Raw values are never modified.

All functions return NEW comparison copies. Confusable-character folding exists
only to DETECT ambiguity; it must never be used to confirm an identity.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

# O/0, I/1 (and lowercase l), S/5, B/8 - the confusable pairs named in the spec.
_CONFUSABLE_FOLD = str.maketrans({"O": "0", "I": "1", "L": "1", "S": "5", "B": "8"})
_NON_ALNUM = re.compile(r"[^A-Z0-9]")
_WS = re.compile(r"\s+")


@dataclass(frozen=True)
class BatchKey:
    raw: str  # exactly as read (OCR) or as in the dataset
    key: str  # comparison key: NFKC, uppercase, letters+digits only
    confusable_key: str  # key with O/0 I/1 L/1 S/5 B/8 folded - ambiguity detection ONLY
    transformations: tuple[str, ...]  # human-readable trace of what changed


def batch_key(raw: str) -> BatchKey:
    """Build the comparison key for a batch identifier.

    Keeps leading zeros and every letter/digit. Removes only whitespace,
    punctuation and symbols (hyphens, slashes, trailing commas, ...), which are
    treated as formatting. Does NOT map O/0, I/1, S/5 or B/8.
    """
    steps: list[str] = []
    text = unicodedata.normalize("NFKC", raw)
    if text != raw:
        steps.append("unicode_nfkc")
    upper = text.upper()
    if upper != text:
        steps.append("uppercase")
    key = _NON_ALNUM.sub("", upper)
    if key != upper:
        steps.append("removed_non_alphanumeric")
    return BatchKey(raw=raw, key=key, confusable_key=key.translate(_CONFUSABLE_FOLD), transformations=tuple(steps))


def normalize_text(raw: str) -> str:
    """Comparison copy for free text (product names): NFKC, casefold, collapsed whitespace."""
    return _WS.sub(" ", unicodedata.normalize("NFKC", raw)).strip().casefold()


_TOKEN = re.compile(r"[a-z0-9]+")


def tokens(raw: str) -> list[str]:
    return _TOKEN.findall(normalize_text(raw))
