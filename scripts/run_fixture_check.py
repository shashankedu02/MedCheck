"""Run the SYNTHETIC test fixtures through the unchanged pipeline and record the results SEPARATELY from real photos.

    python scripts/run_fixture_check.py [--out DIR]     # default: evaluation/results/fixtures/  (git-ignored)

Each run writes a new folder fixture_run_<timestamp>/ with the rendered fixtures, fixture_results.csv and
fixture_report.md. It never writes into evaluation/results/runs/ (real-photograph runs) and its numbers are a
FIXTURE PASS RATE: they show the software path works on known, clean, rendered inputs, not how accurate it is on
real packs. Exit code 0 only if every fixture produced its documented result.
"""
from __future__ import annotations

import argparse
import csv
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import make_demo_images as demo  # noqa: E402

from medcheck.pipeline import MedCheckPipeline  # noqa: E402

HEADER = "SYNTHETIC FIXTURES - NOT REAL-WORLD EVIDENCE. A fixture pass rate is not an accuracy figure."


def _commit() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, capture_output=True, text=True, timeout=10).stdout.strip() or "unknown"
    except (OSError, subprocess.SubprocessError):
        return "unknown"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=Path, default=ROOT / "evaluation" / "results" / "fixtures")
    args = ap.parse_args(argv)

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = args.out / f"fixture_run_{stamp}"
    n = 1
    while run_dir.exists():  # never overwrite an earlier run
        n += 1
        run_dir = args.out / f"fixture_run_{stamp}_{n}"
    expected = demo.build(run_dir / "images")

    pipe = MedCheckPipeline.load()
    pipe.warm_up()
    rows = []
    for name, (headline, _why) in expected.items():
        res = pipe.check((run_dir / "images" / name).read_bytes())
        d = res.decision
        got = d.headline if d is not None else f"rejected: {res.rejection.code}"
        serial_expected = demo.DEMO_SET[name][2]
        serial_got = res.matched_record.serial if res.matched_record is not None else None
        after = ""
        if d is not None and d.reason_code == "ocr_batch_unconfirmed":  # what a user sees after confirming the read batch
            after = pipe.verify_manual(res, res.extraction.batch.raw, confirmed=True).decision.headline
        ok = got == headline and serial_got == serial_expected
        rows.append({"file": name, "kind": demo.FIXTURE_KIND, "expected": headline, "result": got,
                     "reason_code": d.reason_code if d else "", "expected_serial": serial_expected or "",
                     "matched_serial": serial_got or "", "after_user_confirmation": after,
                     "batch_read": (res.extraction.batch.raw or "") if res.extraction else "",
                     "seconds": f"{res.elapsed_seconds:.1f}", "pass": "yes" if ok else "NO"})

    with (run_dir / "fixture_results.csv").open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    passed = sum(r["pass"] == "yes" for r in rows)
    lines = [f"# Fixture check {run_dir.name}", "", f"**{HEADER}**", "",
             f"Commit `{_commit()}`; dataset `{pipe.dataset.sha256[:12]}` ({pipe.dataset.reporting_period}); engines: {res.engine_version}.", "",
             f"Fixtures producing their documented result: **{passed} of {len(rows)}**.", "",
             "| Fixture | Expected | Result | After confirming the read batch | Listed serial | Pass |", "|---|---|---|---|---|---|"]
    lines += [f"| {r['file']} | {r['expected']} | {r['result']} | {r['after_user_confirmation'] or '-'} | {r['matched_serial'] or '-'} | {r['pass']} |" for r in rows]
    (run_dir / "fixture_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(HEADER)
    print(f"{passed}/{len(rows)} fixtures produced their documented result; folder {run_dir}")
    return 0 if passed == len(rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())
