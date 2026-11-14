"""Turn OCR lines into candidate fields and reconcile them across OCR passes.

Heuristic by design: label-anchored patterns only (Batch/B.No./Lot, Mfg, Exp). A field is
READ only when every pass that found one agrees; any disagreement is AMBIGUOUS (abstain).
Raw strings are returned exactly as recognised; nothing is "corrected".
"""
from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass

from . import config
from .dates import parse_month_year
from .models import FieldState
from .normalization import BatchKey, batch_key

_NEXT_LABEL = r"(?:MFG|MFD|M\.?\s?F\.?\s?G|EXP|E\.?\s?X\.?\s?P|MRP|M\.?R\.?P|PRICE|DATE|MANUF|USE\s*BEFORE|BEST\s*BEFORE|RS\b|PACK|NET\b|QTY)"
_BATCH_LABEL = re.compile(
    r"(?:\bB\s*\.?\s*N[O0]\b|\bBATCH\s*(?:N[O0]\b|NUMBER|#)?|\bLOT\s*(?:N[O0]\b|NUMBER|#)?|\bB\s*[.:]\s*N[O0])\s*\.?\s*[:;#\-]*\s*",
    re.I,
)
_NEXT_LABEL_RE = re.compile(r"\b" + _NEXT_LABEL, re.I)
_EXP_LABEL = re.compile(r"(?:\bEXP(?:IRY|IRES)?\b|\bE\s*\.\s*X\s*\.\s*P\b|\bUSE\s*BEFORE\b|\bBEST\s*BEFORE\b)\s*\.?\s*(?:DATE)?\s*[:;\-]*\s*", re.I)
_MFG_LABEL = re.compile(r"(?:\bMFG\b|\bMFD\b|\bMANUF(?:ACTURING|ACTURED)?\b(?:\s*DATE)?|\bM\s*\.\s*F\s*\.\s*G\b)\s*\.?\s*(?:DATE)?\s*[:;\-]*\s*(?!\s*BY\b)", re.I)
_DATE_VALUE = re.compile(
    r"(\d{1,2}\s*[/\-. ]\s*\d{4}|\d{1,2}\s*[/\-.]\s*\d{2}\b|\d{4}\s*[/\-.]\s*\d{1,2}\b|[A-Za-z]{3,9}\.?\s*[/\-. ]?\s*\d{4}|[A-Za-z]{3}\.?\s*[/\-.]\s*\d{2}\b)"
)


@dataclass(frozen=True)
class PassFields:
    batch_candidates: tuple[str, ...]
    expiry_candidates: tuple[str, ...]
    mfg_candidates: tuple[str, ...]


def _cut_at_next_label(rest: str) -> str:
    m = _NEXT_LABEL_RE.search(rest)
    return rest[: m.start()] if m else rest


def _pick_batch(rest: str) -> str | None:
    rest = _cut_at_next_label(rest).strip(" \t:;|")
    toks = rest.split()
    if not toks:
        return None
    t0 = toks[0]
    has_digit = lambda t: any(c.isdigit() for c in t)  # noqa: E731
    alnum = lambda t: sum(c.isalnum() for c in t)  # noqa: E731
    if has_digit(t0) and alnum(t0) >= config.MIN_BATCH_KEY_LENGTH:
        cand = t0
    elif len(toks) > 1 and has_digit(toks[1]):
        cand = f"{t0} {toks[1]}"  # e.g. "BKBP O2601": a letters-only first token continues in the next
    else:
        return None
    k = batch_key(cand).key
    if len(k) < config.MIN_BATCH_KEY_LENGTH or len(k) > 20 or not any(c.isdigit() for c in k):
        return None
    return cand.strip(" \t:;|")


def _find_dates(lines: list[str], label: re.Pattern) -> list[str]:
    out: list[str] = []
    for i, line in enumerate(lines):
        for m in label.finditer(line):
            tail = line[m.end(): m.end() + 24]
            if not tail.strip() and i + 1 < len(lines):
                tail = lines[i + 1][:24]
            v = _DATE_VALUE.search(_cut_at_next_label(tail))
            if v:
                out.append(v.group(1).strip())
    return out


def extract_from_lines(lines: list[str]) -> PassFields:
    batches: list[str] = []
    for i, line in enumerate(lines):
        for m in _BATCH_LABEL.finditer(line):
            rest = line[m.end():]
            val = _pick_batch(rest)
            if val is None and not rest.strip() and i + 1 < len(lines):  # label alone on its line
                val = _pick_batch(lines[i + 1])
            if val:
                batches.append(val)
    return PassFields(tuple(batches), tuple(_find_dates(lines, _EXP_LABEL)), tuple(_find_dates(lines, _MFG_LABEL)))


# ---------------- reconciliation across passes ----------------
@dataclass(frozen=True)
class BatchField:
    state: FieldState
    raw: str | None = None
    key: BatchKey | None = None
    reason: str = ""
    readings: tuple[str, ...] = ()  # distinct raw readings seen (for transparency)


@dataclass(frozen=True)
class DateField:
    state: FieldState
    raw: str | None = None
    reason: str = ""


@dataclass(frozen=True)
class ExtractionResult:
    batch: BatchField
    expiry: DateField
    manufacturing: DateField
    product_text: str  # de-duplicated recognised lines, used only as product-identity corroboration
    passes_used: int


def reconcile_batch(per_pass: list[PassFields], min_agree: int | None = None) -> BatchField:
    min_agree = config.MIN_AGREEING_OCR_PASSES if min_agree is None else min_agree
    support: Counter[str] = Counter()
    raws: dict[str, Counter[str]] = {}
    for pf in per_pass:
        keys_in_pass = set()
        for raw in pf.batch_candidates:
            k = batch_key(raw).key
            keys_in_pass.add(k)
            raws.setdefault(k, Counter())[raw] += 1
        support.update(keys_in_pass)
    if not support:
        return BatchField(FieldState.NOT_FOUND, reason="no batch label with a plausible value was found")
    readings = tuple(sorted({r for c in raws.values() for r in c}))
    if len(support) > 1:
        return BatchField(FieldState.AMBIGUOUS, reason="different batch readings across passes or labels", readings=readings)
    (key, n), = support.items()
    if n < min_agree:
        return BatchField(FieldState.AMBIGUOUS, reason=f"batch seen in only {n} OCR pass(es); {min_agree} required", readings=readings)
    raw = raws[key].most_common(1)[0][0]
    return BatchField(FieldState.READ, raw=raw, key=batch_key(raw), readings=readings)


def reconcile_date(per_pass_values: list[tuple[str, ...]]) -> DateField:
    raws = [v for vals in per_pass_values for v in vals]
    if not raws:
        return DateField(FieldState.NOT_FOUND, reason="no labelled date found")
    parsed = {(p.year, p.month) for r in raws if (p := parse_month_year(r))}
    if len(parsed) > 1:
        return DateField(FieldState.AMBIGUOUS, reason="conflicting date readings across passes")
    return DateField(FieldState.READ, raw=Counter(raws).most_common(1)[0][0])


def extract(passes) -> ExtractionResult:
    """`passes` are ocr.OCRPass objects (only `.lines` is used)."""
    per_pass = [extract_from_lines(list(p.lines)) for p in passes]
    seen: list[str] = []
    for p in passes:
        for line in p.lines:
            if line not in seen:
                seen.append(line)
    return ExtractionResult(
        batch=reconcile_batch(per_pass),
        expiry=reconcile_date([pf.expiry_candidates for pf in per_pass]),
        manufacturing=reconcile_date([pf.mfg_candidates for pf in per_pass]),
        product_text="\n".join(seen),
        passes_used=len(per_pass),
    )
