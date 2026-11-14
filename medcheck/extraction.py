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
_EXP_LABEL = re.compile(r"(?:(?<![A-Za-z])EXP(?:IRY|IRES)?\b|\bE\s*\.\s*X\s*\.\s*P\b|\bUSE\s*BEFORE\b|\bBEST\s*BEFORE\b)\s*\.?\s*(?:DATE)?\s*[:;\-]*\s*", re.I)
_MFG_LABEL = re.compile(r"(?:(?<![A-Za-z])MFG\b|(?<![A-Za-z])MFD\b|\bMANUF(?:ACTURING|ACTURED)?\b(?:\s*DATE)?|\bM\s*\.\s*F\s*\.\s*G\b)\s*\.?\s*(?:DATE)?\s*[:;\-]*\s*(?!\s*BY\b)", re.I)
_DATE_VALUE = re.compile(
    r"(\d{1,2}\s*[/\-. ]\s*\d{4}|\d{1,2}\s*[/\-.]\s*\d{2}\b|\d{4}\s*[/\-.]\s*\d{1,2}\b|[A-Za-z]{3,9}\.?\s*[/\-. ]?\s*\d{4}|[A-Za-z]{3}\.?\s*[/\-.]\s*\d{2}\b)"
)


@dataclass(frozen=True)
class PassFields:
    batch_candidates: tuple[str, ...]
    expiry_candidates: tuple[str, ...]
    mfg_candidates: tuple[str, ...]
    source: str = ""  # provenance: "<engine>:<image view>" of the OCR pass these came from


def _cut_at_next_label(rest: str) -> str:
    m = _NEXT_LABEL_RE.search(rest)
    return rest[: m.start()] if m else rest


# A following label glued onto the batch value because the OCR engine dropped the space, e.g.
# "5BA1617MFD", "HLAS0019MFG.JUL", "25S3GCA146M.R.P". Searched only after the first
# characters so a value that merely starts with such letters is not cut to nothing.
_GLUED_NEXT = re.compile(
    r"(?:MF[GD]|M\.?\s?F\.?\s?G|EXP|M\.?\s?R\.?\s?P|M\.\s?R\b|PER(?:BLIST|STRIP|\b)|INCL|PRICE|RS\.)",
    re.I,
)
_GLUE_SEARCH_FROM = 3
_LABEL_WORDS_ONLY = re.compile(r"^(?:MF[GD]|EXP|MRP|RS|PER|INCL|TABS?|DATE|BATCH|NO)\W*$", re.I)


def _cut_glued(token: str) -> str:
    m = _GLUED_NEXT.search(token, _GLUE_SEARCH_FROM)
    return token[: m.start()] if m else token


def _pick_batch(rest: str) -> str | None:
    """Pick the batch value that follows a batch label, or None if no trustworthy value is there.

    Never trims silently into a different-looking value: a reading that is only label words, has
    no digit, is too short or too long is rejected (the field then stays NOT_FOUND)."""
    rest = _cut_at_next_label(rest).strip(" \t:;|")
    toks = rest.split()
    if not toks:
        return None
    has_digit = lambda t: any(c.isdigit() for c in t)  # noqa: E731
    alnum = lambda t: sum(c.isalnum() for c in t)  # noqa: E731
    t0 = _cut_glued(toks[0]).strip(" \t:;|")  # raw punctuation (e.g. a trailing comma) is preserved
    if _LABEL_WORDS_ONLY.match(t0):
        return None
    glued = t0 != toks[0].strip(" \t:;|")
    if has_digit(t0) and alnum(t0) >= config.MIN_BATCH_KEY_LENGTH:
        cand = t0
    elif not glued and len(toks) > 1 and has_digit(toks[1]) and not _LABEL_WORDS_ONLY.match(toks[1]):
        cand = f"{t0} {_cut_glued(toks[1]).strip(' \t:;|')}"  # e.g. "BKBP O2601": letters first token continues
    else:
        return None
    k = batch_key(cand).key
    if len(k) < config.MIN_BATCH_KEY_LENGTH or len(k) > 20 or not any(c.isdigit() for c in k):
        return None
    # Guards against sentence fragments and OCR garbage that happen to follow a label ("30 deg C. Protect from light"):
    # characters never seen in a listed batch, or a run of letters longer than any listed batch has, is not a batch.
    if re.search(rf"[^{config.BATCH_ALLOWED_CHARS}]", cand):
        return None
    if max((len(x) for x in re.findall(r"[A-Za-z]+", cand)), default=0) > config.MAX_BATCH_LETTER_RUN:
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
    reading_sources: tuple[tuple[str, str], ...] = ()  # (raw reading, "<engine>:<view>") for every report


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
    engines: tuple[str, ...] = ()  # OCR engines that contributed passes (provenance)
    edge_ignored: tuple[str, ...] = ()  # batch readings ignored because their line touched the image/crop edge


def reconcile_batch(per_pass: list[PassFields], min_agree: int | None = None) -> BatchField:
    min_agree = config.MIN_AGREEING_OCR_PASSES if min_agree is None else min_agree
    support: Counter[str] = Counter()
    raws: dict[str, Counter[str]] = {}
    sources: list[tuple[str, str]] = []
    for pf in per_pass:
        keys_in_pass = set()
        for raw in pf.batch_candidates:
            k = batch_key(raw).key
            keys_in_pass.add(k)
            raws.setdefault(k, Counter())[raw] += 1
            if (raw, pf.source) not in sources:
                sources.append((raw, pf.source))
        support.update(keys_in_pass)
    if not support:
        return BatchField(FieldState.NOT_FOUND, reason="no batch label with a plausible value was found")
    readings = tuple(sorted({r for c in raws.values() for r in c}))
    srcs = tuple(sources)
    if len(support) > 1:
        return BatchField(FieldState.AMBIGUOUS, reason="different batch readings across passes or labels", readings=readings, reading_sources=srcs)
    (key, n), = support.items()
    if n < min_agree:
        return BatchField(FieldState.AMBIGUOUS, reason=f"batch seen in only {n} OCR pass(es); {min_agree} required", readings=readings, reading_sources=srcs)
    raw = raws[key].most_common(1)[0][0]
    return BatchField(FieldState.READ, raw=raw, key=batch_key(raw), readings=readings, reading_sources=srcs)


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
    per_pass = []
    edge_ignored: list[str] = []
    for p in passes:
        all_lines = list(p.lines)
        edge = set(getattr(p, "edge_lines", ()) or ())
        # A line touching the edge of the view may be cut off: a truncated batch looks like a clean, shorter one.
        # Such lines are blanked for field extraction (they still count as product text).
        pf = extract_from_lines([("" if i in edge else ln) for i, ln in enumerate(all_lines)]) if edge else extract_from_lines(all_lines)
        if edge:
            for raw in extract_from_lines(all_lines).batch_candidates:
                if raw not in pf.batch_candidates and raw not in edge_ignored:
                    edge_ignored.append(raw)
        per_pass.append(PassFields(pf.batch_candidates, pf.expiry_candidates, pf.mfg_candidates,
                                   getattr(p, "pass_id", "")))
    seen: list[str] = []
    for p in passes:
        for line in p.lines:
            if line not in seen:
                seen.append(line)
    batch = reconcile_batch(per_pass)
    if batch.state is FieldState.NOT_FOUND and edge_ignored:
        batch = BatchField(FieldState.NOT_FOUND, reason="a batch-like line touches the edge of the image, so it may be cut off and was not used")
    return ExtractionResult(
        batch=batch,
        expiry=reconcile_date([pf.expiry_candidates for pf in per_pass]),
        manufacturing=reconcile_date([pf.mfg_candidates for pf in per_pass]),
        product_text="\n".join(seen),
        passes_used=len(per_pass),
        engines=tuple(sorted({getattr(p, "engine", "tesseract") for p in passes})),
        edge_ignored=tuple(edge_ignored),
    )
