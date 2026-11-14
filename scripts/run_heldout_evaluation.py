"""One-time evaluation of the seven RESERVED photographs with the unchanged production pipeline.

    python run_heldout_evaluation.py [repo_root]

* Processes ONLY the reserved IDs listed in evaluation/heldout_ids.txt (every other photo is skipped and never opened).
* Writes ONE new run folder  evaluation/results/runs/heldout_<timestamp>/  (CSV, Markdown report, run_info.json).
  It does not touch earlier runs and does not refresh the top-level 'latest' copies.
* No ground truth is supplied at run time (every label stays Pending) and no reference batches are applied: the
  independent reading is done separately, afterwards, without looking at this output first.
* The photographs are only read; their SHA-256 are checked before and after.
* Prints counts only (no outcomes), so the results can be read after the labelling step.
"""
import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from medcheck import real_eval as ev  # noqa: E402
from medcheck.pipeline import MedCheckPipeline  # noqa: E402

PHOTOS = ROOT / "evaluation" / "incoming_photos"
RESULTS = ROOT / "evaluation" / "results"
reserved = ev.load_heldout(ROOT / "evaluation" / "heldout_ids.txt")
files = [p for p in ev.discover(PHOTOS) if ev.test_id_for(p) in reserved]
others = {ev.test_id_for(p) for p in ev.discover(PHOTOS)} - reserved  # skipped: never opened
assert len(files) == len(reserved) == 7, (len(files), sorted(reserved))

started = datetime.now()
before = {p.name: ev.sha256_file(p) for p in files}
pipe = MedCheckPipeline.load()
pipe.warm_up()  # model initialisation is not counted in any photo's time
run_id = "heldout_" + ev.new_run_id(RESULTS, started)
gt = ev.load_ground_truth(ROOT / "evaluation" / "ground_truth.csv")  # read only; reserved IDs have no label -> Pending
records = ev.process_folder(PHOTOS, pipe.check, run_id, gt, skip_ids=others, reference={})
after = {p.name: ev.sha256_file(p) for p in files}

engines = sorted({r.ocr_engine for r in records if r.ocr_engine})
ctx = ev.run_context(pipe, run_id, started, {
    "photo_folder": str(PHOTOS), "ground_truth_file": "none applied (all Pending)", "ocr_engine": "; ".join(engines) or "n/a",
    "originals_unchanged": before == after, "heldout_excluded": "none (this IS the reserved-photo run)",
    "note": "one-time evaluation of the reserved photographs; no tuning; no reference applied at run time",
})
run_dir = RESULTS / "runs" / run_id
run_dir.mkdir(parents=True, exist_ok=False)
ev.write_csv(run_dir / "evaluation_results.csv", records)
(run_dir / "evaluation_report.md").write_text(ev.format_report(records, ctx), encoding="utf-8")
(run_dir / "run_info.json").write_text(json.dumps({**ctx, "summary": ev.summarize(records), "sha256": after}, indent=2), encoding="utf-8")
print(f"{run_id}: processed {len(records)} reserved photographs; originals unchanged: {before == after}; folder {run_dir}")
