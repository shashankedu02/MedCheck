"""Evaluation tooling tests (milestone M6). Rows are MADE UP to check arithmetic; no performance is implied."""
from __future__ import annotations

import csv
import subprocess
import sys
from pathlib import Path

import pytest

from medcheck.evaluation import EvalRow, compute_metrics, format_report, wilson
from medcheck.models import Status
from tests.helpers import encode, font_path, render_label

ROOT = Path(__file__).resolve().parent.parent
S = Status


def row(expected, status, serial=None, expected_serial=None, kind="status", true_batch=None, read=None, sec=1.0):
    return EvalRow(expected, expected_serial, status, kind, serial, true_batch, read, sec)


def test_wilson_known_values():
    lo, hi = wilson(8, 10)
    assert round(lo, 3) == 0.490 and round(hi, 3) == 0.943
    assert wilson(0, 0) is None
    assert wilson(0, 10)[0] == 0.0 and wilson(10, 10)[1] == 1.0


def test_abstentions_stay_in_denominators():
    rows = [row(True, S.ALERT_FOUND, 4, 4), row(True, S.UNABLE_TO_VERIFY), row(True, S.NO_ALERT_FOUND),
            row(False, S.NO_ALERT_FOUND), row(False, S.UNABLE_TO_VERIFY), row(False, S.ALERT_FOUND, 9)]
    m = compute_metrics(rows)
    assert m["alert_sensitivity"]["k"] == 1 and m["alert_sensitivity"]["n"] == 3
    assert m["false_negatives_wrong_clean_negative"] == 1 and m["alerts_missed_by_abstention"] == 1
    assert m["false_positives"] == 1
    assert m["alert_precision"]["k"] == 1 and m["alert_precision"]["n"] == 2
    assert m["specificity_clean_no_alert_on_non_alert"]["k"] == 1 and m["specificity_clean_no_alert_on_non_alert"]["n"] == 3
    assert m["abstention_rate"]["k"] == 2 and m["abstention_rate"]["n"] == 6
    assert m["coverage_decisive"]["k"] == 4


def test_wrong_serial_is_not_a_true_positive():
    m = compute_metrics([row(True, S.ALERT_FOUND, 5, 4)])
    assert m["alert_sensitivity"]["k"] == 0 and m["alerts_with_wrong_serial"] == 1


def test_system_errors_and_rejections_counted_not_dropped():
    m = compute_metrics([row(True, None, kind="system_error"), row(False, None, kind="rejected"), row(True, S.ALERT_FOUND, 1, 1)])
    assert m["system_errors"] == 1 and m["rejected_uploads"] == 1 and m["images"] == 3
    assert m["alert_sensitivity"]["n"] == 2 and m["abstention_rate"]["n"] == 3


def test_batch_accuracy_exact_and_confidently_wrong():
    m = compute_metrics([row(True, S.ALERT_FOUND, 1, 1, true_batch="AB123", read="AB123"),
                         row(True, S.UNABLE_TO_VERIFY, true_batch="AB124", read="AB12A"),
                         row(True, S.UNABLE_TO_VERIFY, true_batch="AB125", read=None),
                         row(False, S.NO_ALERT_FOUND)])
    assert m["batch_exact_accuracy_all_labelled"]["k"] == 1 and m["batch_exact_accuracy_all_labelled"]["n"] == 3
    assert m["batch_confidently_wrong"] == 1


def test_latency_and_empty_input():
    m = compute_metrics([row(False, S.NO_ALERT_FOUND, sec=s) for s in range(1, 21)])
    assert m["latency_seconds"]["median"] == 10.5 and m["latency_seconds"]["p95"] == 19
    empty = compute_metrics([])
    assert empty["images"] == 0 and empty["alert_sensitivity"]["value"] is None
    assert "n/a" in format_report(empty, "h")


def test_report_has_validity_header():
    assert format_report(compute_metrics([row(False, S.NO_ALERT_FOUND)]), "HEADER LINE").startswith("HEADER LINE")


# ---- CLI on a tiny synthetic manifest (tests the tool only) ----
@pytest.mark.skipif(font_path() is None, reason="no font")
def test_cli_runs_and_rejects_bad_manifests(tmp_path):
    (tmp_path / "a.png").write_bytes(encode(render_label(["Linzotal 600", "Linezolid Tablets IP 600 mg", "B.No.: TG261185", "Exp: 04/2028"]), "PNG"))
    (tmp_path / "b.png").write_bytes(encode(render_label(["Paracetamol Tablets IP 500 mg", "B.No.: ZX99001Q", "Exp: 12/2028"]), "PNG"))
    man = tmp_path / "manifest.csv"
    with man.open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["image_path", "split", "expected_alert", "expected_serial", "true_batch"])
        w.writerow(["a.png", "heldout", "yes", "4", "TG261185"])
        w.writerow(["b.png", "heldout", "no", "", "ZX99001Q"])
    out = tmp_path / "res.csv"
    r = subprocess.run([sys.executable, str(ROOT / "scripts" / "evaluate.py"), "--manifest", str(man), "--out", str(out)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    assert "Valid only if the set follows docs/EVALUATION.md" in r.stdout and "Images: 2" in r.stdout
    assert len(list(csv.DictReader(out.open()))) == 2

    (tmp_path / "dup.png").write_bytes((tmp_path / "a.png").read_bytes())
    with man.open("a", newline="") as fh:
        csv.writer(fh).writerow(["dup.png", "heldout", "yes", "4", ""])
    r2 = subprocess.run([sys.executable, str(ROOT / "scripts" / "evaluate.py"), "--manifest", str(man)], capture_output=True, text=True)
    assert r2.returncode == 2 and "duplicate image content" in r2.stderr
