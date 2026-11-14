"""Record an independently verified ground-truth label for one evaluation photo.

    .\\.venv\\Scripts\\python.exe scripts\\set_ground_truth.py T005 "Alert found" --serial 4 --batch ABC123 --verified-by "checked pack + CDSCO list"
    .\\.venv\\Scripts\\python.exe scripts\\set_ground_truth.py T006 "No alert found" --verified-by "pack batch not in the list"
    .\\.venv\\Scripts\\python.exe scripts\\set_ground_truth.py T007 Pending
    .\\.venv\\Scripts\\python.exe scripts\\set_ground_truth.py --list

Labels must come from the physical pack and the official list, NOT from MedCheck's own output.
Then re-score: scripts\\run_evaluation.py --rescore <run_id>   (or simply run the evaluation again).
You can also edit evaluation/ground_truth.csv directly; the same validation applies when it is read.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from medcheck import real_eval as ev  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("test_id", nargs="?")
    ap.add_argument("expected", nargs="?", help=" | ".join(ev.EXPECTED_VALUES))
    ap.add_argument("--serial", default="", help="dataset serial the pack's batch corresponds to")
    ap.add_argument("--batch", default="", help="batch exactly as printed on the pack")
    ap.add_argument("--verified-by", default="", help="who/what independently established this label (required)")
    ap.add_argument("--note", default="")
    ap.add_argument("--file", type=Path, default=ROOT / "evaluation" / "ground_truth.csv")
    ap.add_argument("--list", action="store_true")
    a = ap.parse_args(argv)
    try:
        if a.list:
            for tid, g in sorted(ev.load_ground_truth(a.file).items()):
                print(f"{tid}\t{g['expected_outcome']}\t{g['expected_serial']}\t{g['expected_batch']}\t{g['verified_by']}")
            return 0
        if not a.test_id or not a.expected:
            ap.error("test_id and expected are required (or use --list)")
        ev.set_ground_truth(a.file, a.test_id, a.expected, verified_by=a.verified_by, batch=a.batch,
                            serial=a.serial, note=a.note)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(f"{a.test_id}: expected_outcome set to {a.expected}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
