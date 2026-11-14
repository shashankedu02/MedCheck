"""Real-photograph evaluation workflow (kept apart from the user-facing app).

Runs every photo in a folder through the *existing* `MedCheckPipeline.check()` and records
what happened. It contains no matching logic of its own. Ground truth is a separate, human
supplied file: this module never infers it, and an output is never "correct" merely because
it was produced.

Outputs are written per run (`runs/<run_id>/`) so history is never overwritten; the top-level
`evaluation_results.csv` / `evaluation_report.md` are copies of the most recent run.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import re
import shutil
import subprocess
from dataclasses import dataclass, asdict, fields
from datetime import datetime
from pathlib import Path
from typing import Callable, Iterable

from PIL import Image

SUPPORTED_EXTENSIONS = (".jpg", ".jpeg", ".png", ".webp")

# Ground-truth vocabulary. "Pending" = not yet independently established.
PENDING = "Pending"
EXPECTED_VALUES = (PENDING, "Alert found", "No alert found", "Unable to verify")
STATUS_CORRECT, STATUS_INCORRECT, STATUS_PENDING, STATUS_INCONCLUSIVE = "Correct", "Incorrect", "Pending", "Inconclusive"

GT_COLUMNS = ["test_id", "expected_outcome", "expected_batch", "expected_serial", "verified_by", "evidence_note", "updated_at"]

# Actual-outcome labels that are NOT verification results.
OUT_UNSUPPORTED = "Not processed: unsupported file"
OUT_DUPLICATE_ID = "Not processed: duplicate test id"
OUT_REJECTED = "Image rejected"
OUT_SYSTEM = "System error"
OUT_ERROR = "Processing error"
NON_RESULTS = (OUT_UNSUPPORTED, OUT_DUPLICATE_ID, OUT_REJECTED, OUT_SYSTEM, OUT_ERROR)
VERIFICATION_OUTCOMES = ("Alert found", "No alert found", "Expired", "Unable to verify")


# ---------------------------------------------------------------- records
@dataclass
class EvalRecord:
    run_id: str = ""
    test_id: str = ""
    filename: str = ""
    sha256: str = ""
    duplicate_of: str = ""
    width: str = ""
    height: str = ""
    file_bytes: str = ""
    actual_outcome: str = ""
    reason_code: str = ""
    abstention_reason: str = ""
    explanation: str = ""
    processing_error: str = ""
    batch_state: str = ""
    batch_raw: str = ""
    batch_readings: str = ""
    batch_note: str = ""
    expiry_state: str = ""
    expiry_raw: str = ""
    mfg_state: str = ""
    mfg_raw: str = ""
    match_outcome: str = ""
    match_reason: str = ""
    matched_serial: str = ""
    candidate_serials: str = ""
    matched_dataset_product: str = ""
    matched_dataset_manufacturer: str = ""
    ocr_product_text: str = ""  # single-line, truncated OCR text; the only product/manufacturer info extracted
    ocr_passes: str = ""
    ocr_variants: str = ""
    ocr_engine: str = ""
    elapsed_seconds: str = ""
    expected_outcome: str = PENDING
    expected_batch: str = ""
    expected_serial: str = ""
    ground_truth_verified_by: str = ""
    evaluation_status: str = STATUS_PENDING
    evaluation_note: str = ""
    engines: str = ""  # OCR engines that contributed passes (provenance)
    batch_sources: str = ""  # every raw batch reading with the engine:view that produced it
    batch_reference: str = ""  # independently read batch (only when a reference exists)
    reference_tier: str = ""  # certain | probable (only "certain" is scored)
    batch_result: str = ""  # exact | incorrect | ambiguous | not_found | not_processed | unscored | no_reference


CSV_COLUMNS = [f.name for f in fields(EvalRecord)]


@dataclass(frozen=True)
class Photo:
    path: Path
    test_id: str


# ---------------------------------------------------------------- discovery
def test_id_for(path: Path) -> str:
    """Stable ID from the filename stem: numeric stems -> T001, others -> T-<sanitised stem>."""
    stem = path.stem.strip()
    if stem.isdigit():
        return f"T{int(stem):03d}"
    return "T-" + re.sub(r"[^A-Za-z0-9]+", "_", stem).strip("_").upper()


def _sort_key(p: Path):
    return (0, int(p.stem), p.name.lower()) if p.stem.isdigit() else (1, 0, p.name.lower())


def discover(folder: Path) -> list[Path]:
    """Every regular file directly in `folder` (supported or not), in stable order."""
    if not folder.is_dir():
        raise FileNotFoundError(f"photo folder not found: {folder}")
    return sorted((p for p in folder.iterdir() if p.is_file() and not p.name.startswith(".")), key=_sort_key)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:  # read-only; photographs are never modified
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def image_size(data: bytes) -> tuple[int, int] | None:
    """Stored pixel size from the header only (before EXIF rotation); None if unreadable."""
    try:
        with Image.open(io.BytesIO(data)) as im:
            return im.size
    except Exception:  # noqa: BLE001 - corrupt/unsupported content is reported, not raised
        return None


# ---------------------------------------------------------------- ground truth
def load_ground_truth(path: Path) -> dict[str, dict[str, str]]:
    if not path.exists():
        return {}
    with path.open(newline="", encoding="utf-8-sig") as fh:
        rows = list(csv.DictReader(fh))
    out: dict[str, dict[str, str]] = {}
    for r in rows:
        tid = (r.get("test_id") or "").strip()
        exp = (r.get("expected_outcome") or PENDING).strip() or PENDING
        if exp not in EXPECTED_VALUES:
            raise ValueError(f"ground truth for {tid}: invalid expected_outcome {exp!r}; allowed {EXPECTED_VALUES}")
        if tid:
            out[tid] = {**{c: (r.get(c) or "").strip() for c in GT_COLUMNS}, "expected_outcome": exp}
    return out


def save_ground_truth(path: Path, gt: dict[str, dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=GT_COLUMNS, lineterminator="\n")
        w.writeheader()
        for tid in sorted(gt, key=lambda t: (len(t), t)):
            w.writerow({c: gt[tid].get(c, "") for c in GT_COLUMNS})


def ensure_ground_truth(path: Path, test_ids: Iterable[str]) -> dict[str, dict[str, str]]:
    """Create Pending placeholders for new test IDs. Existing labels are never touched."""
    gt = load_ground_truth(path)
    changed = not path.exists()
    for tid in test_ids:
        if tid not in gt:
            gt[tid] = {c: "" for c in GT_COLUMNS} | {"test_id": tid, "expected_outcome": PENDING}
            changed = True
    if changed:
        save_ground_truth(path, gt)
    return gt


def set_ground_truth(path: Path, test_id: str, expected: str, *, verified_by: str, batch: str = "",
                     serial: str = "", note: str = "", now: datetime | None = None) -> None:
    """Record an independently verified label. `verified_by` is mandatory for anything but Pending."""
    if expected not in EXPECTED_VALUES:
        raise ValueError(f"expected must be one of {EXPECTED_VALUES}")
    if expected != PENDING and not verified_by.strip():
        raise ValueError("verified_by is required: say who/what independently established this label")
    if expected == "Alert found" and not (serial.strip() or batch.strip()):
        raise ValueError("an 'Alert found' label needs the expected serial and/or the batch printed on the pack")
    gt = load_ground_truth(path)
    gt[test_id] = {
        "test_id": test_id, "expected_outcome": expected, "expected_batch": batch.strip(),
        "expected_serial": str(serial).strip(), "verified_by": verified_by.strip(), "evidence_note": note.strip(),
        "updated_at": (now or datetime.now()).isoformat(timespec="seconds"),
    }
    save_ground_truth(path, gt)


AWAITING_CONFIRMATION = "ocr_batch_unconfirmed"  # decision reason: clean negative withheld until a person checks the pack (D-026)


def score(actual: str, expected: str, matched_serial: str = "", expected_serial: str = "", reason_code: str = "") -> tuple[str, str]:
    """Evaluation status kept separate from both the actual and expected outcomes."""
    if expected == PENDING or not expected:
        return STATUS_PENDING, "no independently verified ground truth yet"
    if actual not in VERIFICATION_OUTCOMES:
        return STATUS_INCONCLUSIVE, f"no verification outcome was produced ({actual})"
    if reason_code == AWAITING_CONFIRMATION and expected == "No alert found":
        return STATUS_INCONCLUSIVE, ("a clean negative is withheld until a person confirms the printed batch (D-026); "
                                     "the tool cannot confirm it, so the batch string is scored separately (batch_result)")
    if actual == expected:
        if actual == "Alert found" and expected_serial and matched_serial and expected_serial != matched_serial:
            return STATUS_INCORRECT, f"alert on serial {matched_serial} but expected serial {expected_serial}"
        return STATUS_CORRECT, ""
    if actual == "Unable to verify":
        return STATUS_INCORRECT, f"abstained (counts as a miss) where expected '{expected}'"
    return STATUS_INCORRECT, f"got '{actual}', expected '{expected}'"


def apply_ground_truth(rec: EvalRecord, gt: dict[str, dict[str, str]]) -> EvalRecord:
    g = gt.get(rec.test_id, {})
    rec.expected_outcome = g.get("expected_outcome") or PENDING
    rec.expected_batch = g.get("expected_batch", "")
    rec.expected_serial = g.get("expected_serial", "")
    rec.ground_truth_verified_by = g.get("verified_by", "")
    rec.evaluation_status, rec.evaluation_note = score(
        rec.actual_outcome, rec.expected_outcome, rec.matched_serial, rec.expected_serial, rec.reason_code)
    return rec


# ---------------------------------------------------------------- reference batches and held-out set
def load_heldout(path: Path) -> set[str]:
    """Test IDs reserved as held-out. Lines are numbers or Txxx; '#' starts a comment."""
    if not path.exists():
        return set()
    ids: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        s = line.split("#", 1)[0].strip()
        if s:
            ids.add(f"T{int(s):03d}" if s.isdigit() else s.upper())
    return ids


def load_reference(path: Path) -> dict[str, tuple[str, str]]:
    """test_id -> (batch exactly as read independently, tier). Only tier 'certain' is scored."""
    if not path.exists():
        return {}
    with path.open(newline="", encoding="utf-8-sig") as fh:
        return {r["test_id"].strip(): (r["reference_batch"].strip(), r["tier"].strip())
                for r in csv.DictReader(fh) if r.get("test_id")}


def apply_reference(rec: EvalRecord, ref: dict[str, tuple[str, str]]) -> EvalRecord:
    """Score the batch field against an independently read reference. Never uses MedCheck output as truth."""
    from .normalization import batch_key

    batch, tier = ref.get(rec.test_id, ("", ""))
    rec.batch_reference, rec.reference_tier = batch, tier
    if rec.actual_outcome in NON_RESULTS:
        rec.batch_result = "not_processed"
    elif not batch:
        rec.batch_result = "no_reference"
    elif tier != "certain":
        rec.batch_result = "unscored"
    elif rec.batch_state == "read":
        rec.batch_result = "exact" if batch_key(rec.batch_raw).key == batch_key(batch).key else "incorrect"
    elif rec.batch_state == "ambiguous":
        rec.batch_result = "ambiguous"
    else:
        rec.batch_result = "not_found"
    return rec


# ---------------------------------------------------------------- processing
def _one_line(text: str, limit: int) -> str:
    s = " ".join((text or "").split())
    return s if len(s) <= limit else s[: limit - 1] + "…"


def record_from_scan(res, rec: EvalRecord) -> EvalRecord:
    """Copy a `pipeline.ScanResult` into a record. Pure transcription; no judgement added."""
    if res.rejection is not None:
        rec.actual_outcome, rec.reason_code = OUT_REJECTED, res.rejection.code
        rec.explanation = res.rejection.message
    elif res.decision is not None and res.decision.is_system_error:
        rec.actual_outcome, rec.reason_code = OUT_SYSTEM, res.decision.reason_code
        rec.explanation = res.decision.explanation
    elif res.decision is not None:
        d = res.decision
        rec.actual_outcome, rec.reason_code, rec.explanation = d.headline, d.reason_code, d.explanation
        if d.headline == "Unable to verify":
            rec.abstention_reason = d.explanation
        if d.matched_serial is not None:
            rec.matched_serial = str(d.matched_serial)
    else:
        rec.actual_outcome, rec.processing_error = OUT_ERROR, "pipeline returned no decision"
    ex = res.extraction
    if ex is not None:
        rec.batch_state, rec.batch_raw = ex.batch.state.value, ex.batch.raw or ""
        rec.batch_readings = " | ".join(ex.batch.readings)
        rec.batch_note = ex.batch.reason
        rec.expiry_state, rec.expiry_raw = ex.expiry.state.value, ex.expiry.raw or ""
        rec.mfg_state, rec.mfg_raw = ex.manufacturing.state.value, ex.manufacturing.raw or ""
        rec.ocr_product_text = _one_line(ex.product_text, 400)
    if res.match is not None:
        rec.match_outcome, rec.match_reason = res.match.outcome.value, res.match.reason
        rec.candidate_serials = " ".join(str(s) for s in res.match.candidate_serials)
    if res.matched_record is not None:
        rec.matched_dataset_product = _one_line(res.matched_record.product_name, 200)
        rec.matched_dataset_manufacturer = _one_line(res.matched_record.manufactured_by, 200)
    if ex is not None:
        rec.batch_sources = " | ".join(f"{raw}@{src}" for raw, src in ex.batch.reading_sources)
    rec.engines = " ".join(res.engines)
    rec.ocr_passes = str(res.ocr_passes)
    rec.ocr_variants = " ".join(res.variants_used)
    rec.ocr_engine = res.engine_version or ""
    rec.elapsed_seconds = f"{res.elapsed_seconds:.1f}"
    return rec


def process_folder(folder: Path, check: Callable[[bytes], object], run_id: str,
                   gt: dict[str, dict[str, str]], *, skip_ids: set[str] | None = None,
                   reference: dict[str, tuple[str, str]] | None = None) -> list[EvalRecord]:
    """Process every file in `folder` except `skip_ids` (the held-out set: those files are never even opened).
    One bad file never stops the run."""
    records: list[EvalRecord] = []
    seen_ids: dict[str, str] = {}
    seen_hashes: dict[str, str] = {}
    for path in discover(folder):
        if skip_ids and test_id_for(path) in skip_ids:
            continue
        rec = EvalRecord(run_id=run_id, test_id=test_id_for(path), filename=path.name)
        try:
            data = path.read_bytes()
            rec.sha256, rec.file_bytes = hashlib.sha256(data).hexdigest(), str(len(data))
            size = image_size(data)
            if size:
                rec.width, rec.height = str(size[0]), str(size[1])
            if rec.sha256 in seen_hashes:
                rec.duplicate_of = seen_hashes[rec.sha256]  # still processed; flagged for the reader
            else:
                seen_hashes[rec.sha256] = rec.test_id
            if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
                rec.actual_outcome, rec.reason_code = OUT_UNSUPPORTED, "unsupported_extension"
                rec.explanation = f"extension {path.suffix or '(none)'} is not one of {', '.join(SUPPORTED_EXTENSIONS)}"
            elif rec.test_id in seen_ids:
                rec.actual_outcome, rec.reason_code = OUT_DUPLICATE_ID, "duplicate_test_id"
                rec.explanation = f"same test id as {seen_ids[rec.test_id]}; rename one file"
            else:
                seen_ids[rec.test_id] = path.name
                record_from_scan(check(data), rec)
        except Exception as exc:  # noqa: BLE001 - recorded by type only (no content)
            rec.actual_outcome, rec.processing_error = OUT_ERROR, type(exc).__name__
            rec.reason_code = "processing_error"
        records.append(apply_reference(apply_ground_truth(rec, gt), reference or {}))
    return records


# ---------------------------------------------------------------- run bookkeeping
def new_run_id(results_dir: Path, now: datetime | None = None) -> str:
    base = "run_" + (now or datetime.now()).strftime("%Y%m%d_%H%M%S")
    run_id, n = base, 1
    while (results_dir / "runs" / run_id).exists():
        n += 1
        run_id = f"{base}_{n}"
    return run_id


def _git(*args: str) -> str:
    try:
        out = subprocess.run(["git", *args], capture_output=True, text=True, timeout=10, check=False)
        return out.stdout.strip() if out.returncode == 0 else ""
    except Exception:  # noqa: BLE001
        return ""


def run_context(pipeline, run_id: str, started: datetime, extra: dict | None = None) -> dict:
    ds = pipeline.dataset
    return {
        "run_id": run_id,
        "started_at": started.isoformat(timespec="seconds"),
        "git_commit": _git("rev-parse", "--short", "HEAD") or "unknown",
        "git_dirty": bool(_git("status", "--porcelain", "--", "medcheck", "scripts", "data")),
        "dataset_sha256": ds.sha256 if ds else "unavailable",
        "dataset_period": ds.reporting_period if ds else "unavailable",
        **(extra or {}),
    }


def write_csv(path: Path, records: list[EvalRecord]) -> None:
    with path.open("w", newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=CSV_COLUMNS, lineterminator="\n")
        w.writeheader()
        for r in records:
            w.writerow({k: " ".join(str(v).split()) for k, v in asdict(r).items()})


def read_csv(path: Path) -> list[EvalRecord]:
    with path.open(newline="", encoding="utf-8-sig") as fh:
        return [EvalRecord(**{k: (row.get(k) or "") for k in CSV_COLUMNS}) for row in csv.DictReader(fh)]


def _md(text: str) -> str:
    return (text or "").replace("|", "\\|").replace("\n", " ") or "-"


def summarize(records: list[EvalRecord]) -> dict:
    count = lambda attr, val: sum(1 for r in records if getattr(r, attr) == val)  # noqa: E731
    by_outcome: dict[str, int] = {}
    for r in records:
        by_outcome[r.actual_outcome] = by_outcome.get(r.actual_outcome, 0) + 1
    return {
        "total": len(records),
        "processed": sum(1 for r in records if r.actual_outcome in VERIFICATION_OUTCOMES),
        "by_outcome": by_outcome,
        "correct": count("evaluation_status", STATUS_CORRECT),
        "incorrect": count("evaluation_status", STATUS_INCORRECT),
        "pending": count("evaluation_status", STATUS_PENDING),
        "inconclusive": count("evaluation_status", STATUS_INCONCLUSIVE),
        "failed": [r.test_id for r in records if r.actual_outcome in NON_RESULTS],
        "awaiting_confirmation": [r.test_id for r in records if r.reason_code == AWAITING_CONFIRMATION],
        "batch_result": {k: sum(1 for r in records if r.batch_result == k)
                         for k in ("exact", "incorrect", "ambiguous", "not_found", "unscored", "no_reference", "not_processed")},
    }


def format_report(records: list[EvalRecord], ctx: dict) -> str:
    s = summarize(records)
    labelled = s["correct"] + s["incorrect"]
    L = [f"# MedCheck real-photograph evaluation: {ctx['run_id']}", ""]
    L += ["## Run information", ""]
    for k in ("run_id", "started_at", "git_commit", "git_dirty", "dataset_period", "dataset_sha256", "photo_folder",
              "ocr_engine", "ground_truth_file", "source_run", "heldout_excluded"):
        if k in ctx and ctx[k] not in (None, ""):
            L.append(f"- **{k}**: {ctx[k]}")
    L += ["", "## Read this first", "",
          "These are MedCheck's **actual outputs**, not verified results. An output is Correct or Incorrect only "
          "when an independently established ground-truth label exists (compared separately below). "
          "`Expired` is disabled by policy (D-007). "
          + ("**No images have verified ground truth yet, so no accuracy statement can be made.**" if labelled == 0 else
             f"Ground truth exists for {labelled} of {s['total']} images; this is a count on a small, "
             "non-randomised sample and not a validated accuracy figure."), ""]
    L += ["## Summary", "", f"- Files found: **{s['total']}**",
          f"- Produced a verification outcome: **{s['processed']}**",
          f"- Not processed / failed: **{len(s['failed'])}**" + (f" ({', '.join(s['failed'])})" if s["failed"] else ""),
          f"- Clean negatives awaiting a person's confirmation of the printed batch (`{AWAITING_CONFIRMATION}`, reported as Unable to verify): "
          f"**{len(s['awaiting_confirmation'])}**" + (f" ({', '.join(s['awaiting_confirmation'])})" if s["awaiting_confirmation"] else ""),
          "", "| Actual outcome | Count |", "|---|---|"]
    L += [f"| {_md(k)} | {v} |" for k, v in sorted(s["by_outcome"].items())]
    L += ["", f"Evaluation status: Correct **{s['correct']}**, Incorrect **{s['incorrect']}**, "
          f"Pending **{s['pending']}**, Inconclusive **{s['inconclusive']}**.", ""]
    br = s["batch_result"]
    scored = br["exact"] + br["incorrect"] + br["ambiguous"] + br["not_found"]
    L += ["## Batch extraction against the independent reference (diagnostic)", "",
          f"Scored images (reference tier 'certain'): **{scored}**. Exact **{br['exact']}**, incorrect **{br['incorrect']}**, "
          f"ambiguous (abstained) **{br['ambiguous']}**, not found **{br['not_found']}**. Unscored (probable reference) {br['unscored']}, "
          f"no reference {br['no_reference']}. The reference was read by eye, not checked against physical packs; "
          "these counts are not an accuracy estimate.", ""]
    L += ["## Per-image results", "",
          "| Test ID | File | Size | Actual outcome | Batch (state) | Expiry | Mfg | Expected | Status |",
          "|---|---|---|---|---|---|---|---|---|"]
    for r in records:
        size = f"{r.width}x{r.height}" if r.width else "-"
        L.append(f"| {r.test_id} | {_md(r.filename)} | {size} | {_md(r.actual_outcome)} | "
                 f"{_md(r.batch_raw)} ({r.batch_state or '-'}) | {_md(r.expiry_raw)} | {_md(r.mfg_raw)} | "
                 f"{_md(r.expected_outcome)} | {r.evaluation_status} |")
    L += ["", "## Details and abstention reasons", ""]
    for r in records:
        L.append(f"### {r.test_id} ({r.filename})")
        L.append(f"- Outcome: **{r.actual_outcome}**" + (f" [{r.reason_code}]" if r.reason_code else ""))
        for label, val in (("Why", r.abstention_reason or r.explanation), ("Processing error", r.processing_error),
                           ("Batch note", r.batch_note), ("Batch readings across passes", r.batch_readings),
                           ("Match", f"{r.match_outcome}: {r.match_reason}" if r.match_outcome else ""),
                           ("Engines", r.engines), ("Batch readings with source", r.batch_sources),
                           ("Batch reference / result",
                            f"{r.batch_reference} ({r.reference_tier}) -> {r.batch_result}" if r.batch_reference else ""),
                           ("Candidate serials", r.candidate_serials), ("Matched serial", r.matched_serial),
                           ("Duplicate of", r.duplicate_of), ("Evaluation note", r.evaluation_note),
                           ("OCR passes / variants", f"{r.ocr_passes} / {r.ocr_variants}" if r.ocr_passes else "")):
            if val:
                L.append(f"- {label}: {_md(val)}")
        L.append("")
    L += ["## Reproduce", "", "`.\\.venv\\Scripts\\python.exe scripts\\run_evaluation.py`", "",
          "Add ground truth with `scripts\\set_ground_truth.py` and re-score a past run with "
          "`scripts\\run_evaluation.py --rescore <run_id>`. See `docs/EVALUATION.md`.", ""]
    return "\n".join(L)


def write_run(results_dir: Path, run_id: str, records: list[EvalRecord], ctx: dict) -> Path:
    """Write the run folder (never overwrites) and refresh the top-level 'latest' copies."""
    run_dir = results_dir / "runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    write_csv(run_dir / "evaluation_results.csv", records)
    (run_dir / "evaluation_report.md").write_text(format_report(records, ctx), encoding="utf-8")
    (run_dir / "run_info.json").write_text(json.dumps({**ctx, "summary": summarize(records)}, indent=2), encoding="utf-8")
    shutil.copyfile(run_dir / "evaluation_results.csv", results_dir / "evaluation_results.csv")
    shutil.copyfile(run_dir / "evaluation_report.md", results_dir / "evaluation_report.md")
    return run_dir


def rescore(results_dir: Path, source_run: str, gt: dict[str, dict[str, str]], *, skip_ids: set[str] | None = None,
            reference: dict[str, tuple[str, str]] | None = None) -> tuple[str, list[EvalRecord], dict]:
    """Re-apply the *current* ground truth to a past run's recorded outputs (no re-processing)."""
    src = results_dir / "runs" / source_run
    if not (src / "evaluation_results.csv").exists():
        raise FileNotFoundError(f"no such run: {source_run}")
    info = json.loads((src / "run_info.json").read_text(encoding="utf-8")) if (src / "run_info.json").exists() else {}
    records = [r for r in read_csv(src / "evaluation_results.csv") if r.test_id not in (skip_ids or set())]
    run_id = new_run_id(results_dir)
    for r in records:
        r.run_id = run_id
        apply_reference(apply_ground_truth(r, gt), reference or {})
    ctx = {**{k: v for k, v in info.items() if k != "summary"}, "run_id": run_id,
           "started_at": datetime.now().isoformat(timespec="seconds"), "source_run": source_run}
    return run_id, records, ctx
