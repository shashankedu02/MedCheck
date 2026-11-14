"""Deterministic four-status decision engine. Pure: no I/O, no OCR, no UI.

Precedence (see docs/MATCHING.md):
  1. System failure            -> system error (NOT a status)
  2. Batch not read cleanly    -> Unable to verify
  3. Match outcome
       confirmed               -> Alert found   (expiry only adds a caveat)
       uncorroborated/conflict/collision/fuzzy-only -> Unable to verify
       no match                -> step 4
  4. No NSQ match: Expired only if the expiry verdict is EXPIRED (never while the
     month-only policy is unapproved), otherwise No alert found.

Wording must never call a medicine safe, genuine, authentic or free of defects.
"""
from __future__ import annotations

from dataclasses import replace

from .models import (
    BatchSource,
    Decision,
    ExpiryAssessment,
    ExpiryOutcome,
    FieldState,
    MatchAssessment,
    MatchOutcome,
    Status,
    SystemFailure,
)

LIMITATION_TEXT = (
    "MedCheck only compares what it could read from the photo with one monthly CDSCO NSQ list. "
    "It does not test medicine quality or authenticity and is not medical advice. "
    "If you are unsure about a medicine, ask a pharmacist or doctor; do not start or stop a medicine based on this result."
)

_SYSTEM_MESSAGES = {
    SystemFailure.DATASET_MISSING: "The NSQ dataset could not be found, so no check was performed.",
    SystemFailure.DATASET_SCHEMA: "The NSQ dataset has an unexpected format, so no check was performed.",
    SystemFailure.DATASET_INTEGRITY: "The NSQ dataset failed its integrity check, so no check was performed.",
    SystemFailure.OCR_ENGINE_UNAVAILABLE: "The text-recognition engine (Tesseract) is not available, so no check was performed.",
    SystemFailure.OCR_TIMEOUT: "Text recognition took too long, so no check was performed.",
    SystemFailure.INTERNAL: "An unexpected internal error occurred, so no check was performed.",
}


def system_error_decision(failure: SystemFailure) -> Decision:
    return Decision(
        status=None,
        reason_code=f"system_{failure.value}",
        headline="System error: no result",
        explanation=_SYSTEM_MESSAGES[failure] + " This is not a 'No alert found' result.",
        caveats=(LIMITATION_TEXT,),
        system_failure=failure,
    )


def _unable(code: str, why: str, extra: tuple[str, ...] = (), evidence: tuple[str, ...] = ()) -> Decision:
    return Decision(
        status=Status.UNABLE_TO_VERIFY,
        reason_code=code,
        headline=Status.UNABLE_TO_VERIFY.value,
        explanation=why + " Try a clearer, well-lit, in-focus photo of the batch line, or ask a pharmacist.",
        caveats=(*extra, LIMITATION_TEXT),
        evidence=evidence,
    )


def _decide_core(
    *,
    system_failure: SystemFailure | None,
    batch_state: FieldState,
    match: MatchAssessment | None,
    expiry: ExpiryAssessment,
    dataset_period: str,
    expiry_anomaly: bool = False,
) -> Decision:
    if system_failure is not None:
        return system_error_decision(system_failure)

    expiry_caveats: list[str] = []
    if expiry.note:
        expiry_caveats.append(expiry.note)
    if expiry_anomaly:
        expiry_caveats.append("The printed expiry appears to be earlier than the manufacturing date; the dates may have been misread.")

    if batch_state is FieldState.NOT_FOUND:
        return _unable("batch_not_found", "No batch number could be read from the image.")
    if batch_state is FieldState.AMBIGUOUS:
        return _unable(
            "batch_ambiguous",
            "The batch number could not be read consistently (several different readings or conflicting passes).",
        )
    if match is None:  # defensive: a readable batch must always have been matched
        return system_error_decision(SystemFailure.INTERNAL)

    ev = match.evidence
    if match.outcome is MatchOutcome.CONFIRMED:
        caveats = (*match.source_caveats, *expiry_caveats, f"Only the {dataset_period} CDSCO NSQ list was checked.", LIMITATION_TEXT)
        return Decision(
            status=Status.ALERT_FOUND,
            reason_code="alert_confirmed",
            headline=Status.ALERT_FOUND.value,
            explanation=(
                "The batch number read from the photo and the product details match an entry in the "
                f"{dataset_period} CDSCO NSQ (Not of Standard Quality) list. See the matched record below."
            ),
            caveats=caveats,
            matched_serial=match.matched_serial,
            evidence=ev,
        )
    if match.outcome is MatchOutcome.UNCORROBORATED:
        return _unable("identity_uncorroborated", "A listed batch number matches, but the product details could not be confirmed.", evidence=ev)
    if match.outcome is MatchOutcome.CONFLICT:
        return _unable("identity_conflict", "A listed batch number matches, but the product or strength read from the photo conflicts with the listed record.", evidence=ev)
    if match.outcome is MatchOutcome.COLLISION:
        return _unable("batch_collision", "The batch reading matches more than one listed record or can be confused with another, so it cannot be tied to a single entry.", evidence=ev)
    if match.outcome is MatchOutcome.FUZZY_ONLY:
        return _unable("fuzzy_candidate_only", "The batch reading is only similar to a listed batch, which is not enough to confirm or rule out a match.", evidence=ev)

    # MatchOutcome.NO_MATCH: a clean batch read found no qualifying row.
    if expiry.outcome is ExpiryOutcome.EXPIRED:
        return Decision(
            status=Status.EXPIRED,
            reason_code="expired",
            headline=Status.EXPIRED.value,
            explanation=f"No matching entry was found in the {dataset_period} CDSCO NSQ list, and the printed expiry date has passed.",
            caveats=(*expiry_caveats, f"Only the {dataset_period} CDSCO NSQ list was checked.", LIMITATION_TEXT),
            evidence=ev,
        )
    return Decision(
        status=Status.NO_ALERT_FOUND,
        reason_code="no_alert",
        headline=Status.NO_ALERT_FOUND.value,
        explanation=(
            f"No qualifying match for the batch read from the photo was found in the {dataset_period} CDSCO NSQ list. "
            "This does not mean the medicine is safe, genuine or free of quality problems."
        ),
        caveats=(*expiry_caveats, f"Only the {dataset_period} CDSCO NSQ list was checked; other months and sources were not.", LIMITATION_TEXT),
        evidence=ev,
    )


_SOURCE_NOTE = {
    BatchSource.USER_CORRECTED: "The batch number was corrected by you; it is not exactly what was read from the photo. This result applies to the batch you entered.",
    BatchSource.USER_ENTERED: "The batch number was typed by you; it was not read from the photo. This result applies to the batch you entered.",
}


def decide(
    *,
    system_failure: SystemFailure | None,
    batch_state: FieldState,
    match: MatchAssessment | None,
    expiry: ExpiryAssessment,
    dataset_period: str,
    expiry_anomaly: bool = False,
    batch_source: BatchSource = BatchSource.OCR,
    batch_raw: str | None = None,
    entry_confirmed: bool = False,
) -> Decision:
    """Core decision plus provenance rules.

    * A user-supplied batch never counts as OCR evidence and goes through exactly the same matching
      (collision, near-neighbour abstention, corroboration from the *photo's* text).
    * A clean negative (No alert found / Expired) for a user-supplied batch needs the user to confirm
      they compared it with the pack, because a typing error would otherwise produce false reassurance.
    * Every decision that used a batch records which batch string was matched and where it came from.
    """
    manual = batch_source is not BatchSource.OCR
    if (manual and system_failure is None and batch_state is FieldState.READ and match is not None
            and match.outcome is MatchOutcome.NO_MATCH and not entry_confirmed):
        return replace(
            _unable(
                "manual_entry_unconfirmed",
                "No listed batch matches the number you entered, but a typing error could hide a match. "
                "Compare the number with the pack and tick the confirmation box to continue.",
                evidence=match.evidence,
            ),
            batch_source=batch_source,
            batch_as_read=batch_raw,
        )
    d = _decide_core(
        system_failure=system_failure, batch_state=batch_state, match=match, expiry=expiry,
        dataset_period=dataset_period, expiry_anomaly=expiry_anomaly,
    )
    if d.is_system_error or batch_state is not FieldState.READ or match is None:
        return d
    explanation, caveats = d.explanation, d.caveats
    if d.status is Status.NO_ALERT_FOUND and batch_raw:
        explanation += f" Batch checked: {batch_raw}. Compare it with the number printed on the pack."
    if manual:
        explanation = explanation.replace("The batch number read from the photo", "The batch number you entered")
        caveats = (_SOURCE_NOTE[batch_source], *caveats)
    return replace(d, explanation=explanation, caveats=caveats, batch_source=batch_source, batch_as_read=batch_raw)
