"""Run every photo in evaluation/incoming_photos through the real MedCheck pipeline and record the results.

    .\\.venv\\Scripts\\python.exe scripts\\run_evaluation.py
    .\\.venv\\Scripts\\python.exe scripts\\run_evaluation.py --rescore run_20261114_120000

Each run gets its own folder under evaluation/results/runs/<run_id>/; the top-level
evaluation_results.csv / evaluation_report.md are copies of the latest run. Photographs are only
read, never modified, moved or copied. Everything stays local; no network, no uploads.
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from medcheck import real_eval as ev  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--photos", type=Path, default=ROOT / "evaluation" / "incoming_photos")
    ap.add_argument("--results", type=Path, default=ROOT / "evaluation" / "results")
    ap.add_argument("--ground-truth", type=Path, default=ROOT / "evaluation" / "ground_truth.csv")
    ap.add_argument("--reference", type=Path, default=ROOT / "evaluation" / "reference_batches.csv")
    ap.add_argument("--heldout", type=Path, default=ROOT / "evaluation" / "heldout_ids.txt")
    ap.add_argument("--include-heldout", action="store_true",
                    help="ALSO process the reserved held-out photographs (do this once, after the design is frozen)")
    ap.add_argument("--rescore", metavar="RUN_ID", help="re-apply current ground truth to a past run without re-processing")
    args = ap.parse_args(argv)
    args.results.mkdir(parents=True, exist_ok=True)

    heldout = set() if args.include_heldout else ev.load_heldout(args.heldout)
    reference = ev.load_reference(args.reference)
    if args.rescore:
        gt = ev.load_ground_truth(args.ground_truth)
        run_id, records, ctx = ev.rescore(args.results, args.rescore, gt, skip_ids=heldout, reference=reference)
        ctx["heldout_excluded"] = ", ".join(sorted(heldout)) or "none"
        run_dir = ev.write_run(args.results, run_id, records, ctx)
    else:
        from medcheck.pipeline import MedCheckPipeline  # imported here: rescoring needs no OCR stack

        started = datetime.now()
        files = [p for p in ev.discover(args.photos) if ev.test_id_for(p) not in heldout]  # held-out files are never opened
        ids = [ev.test_id_for(p) for p in files]
        gt = ev.ensure_ground_truth(args.ground_truth, ids)
        before = {p.name: ev.sha256_file(p) for p in files}
        pipe = MedCheckPipeline.load()
        run_id = ev.new_run_id(args.results, started)
        print(f"{run_id}: processing {len(files)} files ...", flush=True)
        records = ev.process_folder(args.photos, pipe.check, run_id, gt, skip_ids=heldout, reference=reference)
        after = {p.name: ev.sha256_file(p) for p in files}
        engines = sorted({r.ocr_engine for r in records if r.ocr_engine})
        ctx = ev.run_context(pipe, run_id, started, {
            "photo_folder": str(args.photos), "ground_truth_file": str(args.ground_truth),
            "ocr_engine": "; ".join(engines) or "n/a", "originals_unchanged": before == after,
            "heldout_excluded": ", ".join(sorted(heldout)) or "none",
        })
        run_dir = ev.write_run(args.results, run_id, records, ctx)
        if before != after:
            print("WARNING: an original photograph changed during the run", file=sys.stderr)
            return 2

    s = ev.summarize(records)
    print(f"files: {s['total']}  verification outcomes: {s['processed']}  not processed/failed: {len(s['failed'])} {s['failed']}")
    for k, v in sorted(s["by_outcome"].items()):
        print(f"  {k}: {v}")
    print(f"awaiting confirmation of the printed batch (clean negatives withheld, D-026): {len(s['awaiting_confirmation'])} {s['awaiting_confirmation']}")
    b = s["batch_result"]
    print(f"batch vs reference (certain tier): exact={b['exact']} incorrect={b['incorrect']} ambiguous={b['ambiguous']} not_found={b['not_found']}")
    print(f"evaluation status: correct={s['correct']} incorrect={s['incorrect']} pending={s['pending']} inconclusive={s['inconclusive']}")
    print(f"run folder: {run_dir}")
    print(f"latest CSV: {args.results / 'evaluation_results.csv'}")
    print(f"latest report: {args.results / 'evaluation_report.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
