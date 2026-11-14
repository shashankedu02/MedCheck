"""Pure metric computation for the labelled-image evaluation (docs/EVALUATION.md).

Conventions (stated so numbers cannot be read more favourably than they are):
  * Abstentions ("Unable to verify") are NEVER dropped from a denominator.
  * Sensitivity = correct alerts / ALL alert-listed images (abstentions and misses both count against it).
  * A wrong clean negative on an alert-listed image (No alert found / Expired) is a false negative and
    is reported separately from abstentions.
  * System errors and rejected uploads are counted separately and also stay in denominators.
  * Confirmation policy (D-026): an automated run never confirms a batch, so a clean negative is recorded as
    "Unable to verify" awaiting the user's confirmation (reason `ocr_batch_unconfirmed` / `manual_entry_unconfirmed`).
    These are counted in their OWN category, split by whether the batch string offered for confirmation equals the
    true printed batch:
      - on a NON-listed pack with the correct string: "ready for confirmation" (a careful user then sees No alert found);
      - on a NON-listed pack with a wrong string: the user must catch the error (reported, never counted as correct);
      - on a LISTED pack: a POTENTIAL MISS (the listed batch was misread into an unlisted string; if the user confirms
        without spotting it, the result is a false negative). Reported separately and never hidden as an abstention.
  * Batch strings are compared on the comparison key (case, spaces and punctuation ignored; look-alikes NOT folded).
"""
from __future__ import annotations

import math
import statistics
from dataclasses import dataclass

from .models import Status
from .normalization import batch_key

AWAITING_CONFIRMATION_CODES = frozenset({"ocr_batch_unconfirmed", "manual_entry_unconfirmed"})


@dataclass(frozen=True)
class EvalRow:
    expected_alert: bool
    expected_serial: int | None
    status: Status | None  # None = system error or rejected upload
    outcome_kind: str  # "status" | "system_error" | "rejected"
    matched_serial: int | None
    true_batch: str | None
    batch_read: str | None
    seconds: float
    reason_code: str = ""  # Decision.reason_code; identifies results awaiting the user's confirmation (D-026)

    @property
    def awaiting_confirmation(self) -> bool:
        return self.outcome_kind == "status" and self.status is Status.UNABLE_TO_VERIFY and self.reason_code in AWAITING_CONFIRMATION_CODES


def _same_batch(read: str | None, truth: str | None) -> bool | None:
    """True/False when both strings exist, None when either is missing."""
    if read is None or truth is None:
        return None
    return batch_key(read).key == batch_key(truth).key


def wilson(successes: int, n: int, z: float = 1.96) -> tuple[float, float] | None:
    if n == 0:
        return None
    p = successes / n
    d = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / d
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return max(0.0, centre - half), min(1.0, centre + half)


def _prop(k: int, n: int) -> dict:
    return {"k": k, "n": n, "value": (k / n if n else None), "wilson95": wilson(k, n)}


def _p95(values: list[float]) -> float | None:
    if not values:
        return None
    s = sorted(values)
    return s[min(len(s) - 1, math.ceil(0.95 * len(s)) - 1)]


def compute_metrics(rows: list[EvalRow]) -> dict:
    alerts = [r for r in rows if r.expected_alert]
    non_alerts = [r for r in rows if not r.expected_alert]

    def is_status(r: EvalRow, *statuses: Status) -> bool:
        return r.outcome_kind == "status" and r.status in statuses

    tp = [r for r in alerts if is_status(r, Status.ALERT_FOUND) and (r.expected_serial is None or r.matched_serial == r.expected_serial)]
    wrong_serial = [r for r in alerts if is_status(r, Status.ALERT_FOUND) and r not in tp]
    fn = [r for r in alerts if is_status(r, Status.NO_ALERT_FOUND, Status.EXPIRED)]
    fp = [r for r in non_alerts if is_status(r, Status.ALERT_FOUND)]
    tn = [r for r in non_alerts if is_status(r, Status.NO_ALERT_FOUND)]
    decisive = [r for r in rows if r.outcome_kind == "status" and r.status is not Status.UNABLE_TO_VERIFY]
    awaiting = [r for r in rows if r.awaiting_confirmation]
    abstained = [r for r in rows if is_status(r, Status.UNABLE_TO_VERIFY) and not r.awaiting_confirmation]

    potential_misses = [r for r in alerts if r.awaiting_confirmation]
    na_awaiting = [r for r in non_alerts if r.awaiting_confirmation]
    ready = [r for r in na_awaiting if _same_batch(r.batch_read, r.true_batch) is True]
    wrong_offered = [r for r in na_awaiting if _same_batch(r.batch_read, r.true_batch) is False]

    with_truth = [r for r in rows if r.true_batch is not None]
    exact = [r for r in with_truth if _same_batch(r.batch_read, r.true_batch) is True]
    read_wrong = [r for r in with_truth if _same_batch(r.batch_read, r.true_batch) is False]

    times = [r.seconds for r in rows]
    return {
        "images": len(rows),
        "alert_listed": len(alerts),
        "non_alert": len(non_alerts),
        "alert_sensitivity": _prop(len(tp), len(alerts)),
        "false_negatives_wrong_clean_negative": len(fn),
        "potential_misses_awaiting_confirmation": len(potential_misses),
        "alerts_missed_by_abstention": sum(1 for r in alerts if is_status(r, Status.UNABLE_TO_VERIFY) and not r.awaiting_confirmation),
        "awaiting_confirmation": _prop(len(awaiting), len(rows)),
        "non_alert_ready_for_confirmation": _prop(len(ready), len(non_alerts)),
        "non_alert_wrong_string_offered": len(wrong_offered),
        "non_alert_awaiting_unlabelled": len(na_awaiting) - len(ready) - len(wrong_offered),
        "alerts_with_wrong_serial": len(wrong_serial),
        "false_positives": len(fp),
        "alert_precision": _prop(len(tp), len(tp) + len(fp) + len(wrong_serial)),
        "specificity_clean_no_alert_on_non_alert": _prop(len(tn), len(non_alerts)),
        "abstention_rate": _prop(len(abstained), len(rows)),
        "coverage_decisive": _prop(len(decisive), len(rows)),
        "system_errors": sum(1 for r in rows if r.outcome_kind == "system_error"),
        "rejected_uploads": sum(1 for r in rows if r.outcome_kind == "rejected"),
        "batch_exact_accuracy_all_labelled": _prop(len(exact), len(with_truth)),
        "batch_confidently_wrong": len(read_wrong),
        "latency_seconds": {"median": statistics.median(times) if times else None, "p95": _p95(times)},
    }


def format_report(metrics: dict, header: str) -> str:
    def pct(p: dict) -> str:
        if p["n"] == 0:
            return "n/a (0 images)"
        lo, hi = p["wilson95"]
        return f"{p['k']}/{p['n']} = {100 * p['value']:.1f}% (95% CI {100 * lo:.1f}-{100 * hi:.1f}%)"

    lat = metrics["latency_seconds"]
    lines = [
        header,
        f"Images: {metrics['images']} (alert-listed {metrics['alert_listed']}, non-alert {metrics['non_alert']})",
        f"Alert sensitivity (abstentions count as misses): {pct(metrics['alert_sensitivity'])}",
        f"False negatives (wrong clean negative on alert-listed): {metrics['false_negatives_wrong_clean_negative']}",
        f"POTENTIAL MISSES (alert-listed, misread into an unlisted string, awaiting the user's confirmation): {metrics['potential_misses_awaiting_confirmation']}",
        f"Alert-listed images missed by abstention: {metrics['alerts_missed_by_abstention']}",
        f"Awaiting the user's confirmation (D-026; never counted as correct): {pct(metrics['awaiting_confirmation'])}",
        f"Non-alert images ready for confirmation (correct batch string offered): {pct(metrics['non_alert_ready_for_confirmation'])}; "
        f"wrong string offered: {metrics['non_alert_wrong_string_offered']}; no true batch label: {metrics['non_alert_awaiting_unlabelled']}",
        f"Alerts with wrong serial: {metrics['alerts_with_wrong_serial']}",
        f"False positives (alert on non-alert image): {metrics['false_positives']}",
        f"Alert precision: {pct(metrics['alert_precision'])}",
        f"Clean 'No alert found' on non-alert images (only possible with recorded user confirmations): {pct(metrics['specificity_clean_no_alert_on_non_alert'])}",
        f"Abstention rate (excluding results awaiting confirmation): {pct(metrics['abstention_rate'])}",
        f"Decisive coverage: {pct(metrics['coverage_decisive'])}",
        f"System errors: {metrics['system_errors']}; rejected uploads: {metrics['rejected_uploads']}",
        f"Batch exact accuracy on labelled images: {pct(metrics['batch_exact_accuracy_all_labelled'])}; batch read but wrong: {metrics['batch_confidently_wrong']}",
        f"Latency: median {lat['median']}, p95 {lat['p95']} seconds",
    ]
    return "\n".join(lines)
