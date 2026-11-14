"""Run MedCheck over a labelled image set and report honest metrics.

    python scripts/evaluate.py --manifest eval_private/manifest.csv [--split heldout] [--out results.csv]

Manifest CSV columns (header required):
    image_path      path relative to the manifest file
    split           dev | heldout   (tune only on dev; report heldout)
    expected_alert  yes | no        (ground truth: is this batch on the August 2026 list?)
    expected_serial optional dataset serial for alert-listed images
    true_batch      optional printed batch exactly as it reads on the pack

Privacy: images stay where they are; results contain no image bytes and no OCR text. Use a folder
outside version control (eval_private/ and eval_images/ are git-ignored).
This script computes numbers from whatever you give it. They are only meaningful if the set was
collected and labelled according to docs/EVALUATION.md.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from medcheck.evaluation import EvalRow, compute_metrics, format_report  # noqa: E402
from medcheck.pipeline import MedCheckPipeline  # noqa: E402

REQUIRED = {"image_path", "split", "expected_alert"}


def read_manifest(path: Path) -> list[dict]:
    with path.open(encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        if not REQUIRED <= set(reader.fieldnames or ()):
            raise SystemExit(f"manifest must have columns {sorted(REQUIRED)}")
        rows = list(reader)
    for r in rows:
        if r["expected_alert"].strip().lower() not in ("yes", "no"):
            raise SystemExit(f"expected_alert must be yes/no: {r['image_path']}")
        if r["split"].strip().lower() not in ("dev", "heldout"):
            raise SystemExit(f"split must be dev/heldout: {r['image_path']}")
    return rows


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--manifest", required=True, type=Path)
    ap.add_argument("--split", choices=["dev", "heldout", "all"], default="heldout")
    ap.add_argument("--out", type=Path, default=None, help="optional per-image results CSV")
    args = ap.parse_args(argv)

    manifest = read_manifest(args.manifest)
    base = args.manifest.parent
    selected = [r for r in manifest if args.split == "all" or r["split"].strip().lower() == args.split]
    if not selected:
        print("no images in the selected split", file=sys.stderr)
        return 2

    seen: dict[str, str] = {}
    blobs = []
    for r in selected:
        p = base / r["image_path"]
        if not p.is_file():
            print(f"missing image listed in manifest: {r['image_path']}", file=sys.stderr)
            return 2
        data = p.read_bytes()
        h = hashlib.sha256(data).hexdigest()
        if h in seen:
            print(f"duplicate image content: {r['image_path']} == {seen[h]}", file=sys.stderr)
            return 2
        seen[h] = r["image_path"]
        blobs.append((r, data))

    pipe = MedCheckPipeline.load()
    rows: list[EvalRow] = []
    out_rows = []
    for r, data in blobs:
        res = pipe.check(data)
        if res.rejection is not None:
            kind, status, reason = "rejected", None, res.rejection.code
        elif res.decision.is_system_error:
            kind, status, reason = "system_error", None, res.decision.reason_code
        else:
            kind, status, reason = "status", res.decision.status, res.decision.reason_code
        serial = res.decision.matched_serial if res.decision else None
        batch_read = res.extraction.batch.raw if res.extraction else None
        exp_serial = int(r["expected_serial"]) if r.get("expected_serial", "").strip() else None
        rows.append(EvalRow(r["expected_alert"].strip().lower() == "yes", exp_serial, status, kind, serial,
                            (r.get("true_batch") or None), batch_read, res.elapsed_seconds,
                            reason_code=reason if kind == "status" else ""))
        out_rows.append({"image_path": r["image_path"], "split": r["split"], "expected_alert": r["expected_alert"],
                         "status": status.value if status else kind, "reason": reason, "matched_serial": serial or "",
                         "batch_read": batch_read or "", "seconds": f"{res.elapsed_seconds:.2f}"})

    header = f"EVALUATION on split='{args.split}', {len(rows)} images. Valid only if the set follows docs/EVALUATION.md."
    print(format_report(compute_metrics(rows), header))
    if args.out:
        with args.out.open("w", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(out_rows[0]))
            w.writeheader()
            w.writerows(out_rows)
        print(f"per-image results written to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
