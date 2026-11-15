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
    SystemFailure.OCR_ENGINE_UNAVAILABLE: "No text-recognition engine (RapidOCR or Tesseract) is available, so no check was performed.",
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


CONFIRMATION_MEANING = "Confirming means you checked the printed batch number; it does not show the medicine is genuine or safe."
_CONFIRM_NOTE = (
    "You confirmed that this batch number matches the one printed on the pack. "
    "That confirms the printed number only; it does not show the medicine is genuine or safe."
)

def alert_action_check(batch: str | None) -> str:
    """What the user must check on the pack before acting on an alert. Shown with every alert; it never delays it.

    An alert rests on an exact listed batch plus product words from the photo. A single misread character of an
    unlisted neighbouring batch of the same product (batches are often numbered in sequence) would pass both, and the
    product check does not compare the manufacturer. A person comparing the pack with the listed record catches that."""
    shown = f"exactly '{batch}'" if batch else "exactly the listed batch"
    return (
        f"Before acting on this alert, check on the pack that the printed batch number is {shown}, character by character, "
        "and that the product, strength and manufacturer match the listed record. OCR can misread a single character, and "
        "neighbouring batches of the same product are usually not listed. If anything differs, this alert does not apply; "
        "ask a pharmacist if unsure."
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
    * A clean negative (No alert found / Expired) for ANY batch string, OCR-read or user-supplied, needs the user to confirm
      they compared it with the pack (D-026): OCR can misread look-alike characters consistently, and a typing error would
      equally produce false reassurance. `Alert found` needs no confirmation.
    * Every decision that used a batch records which batch string was matched and where it came from.
    """
    manual = batch_source is not BatchSource.OCR
    clean_negative = (system_failure is None and batch_state is FieldState.READ and match is not None
                      and match.outcome is MatchOutcome.NO_MATCH)
    if clean_negative and not entry_confirmed:
        # D-026: no clean negative (No alert found / Expired) is shown for ANY batch string, OCR-read or typed, until the
        # user has compared it with the pack. Two engines can agree on the same wrong look-alike character (HLA50019 for
        # HLAS0019) and nothing in the data can reveal it when no listed batch is nearby. Alerts are not delayed.
        if manual:
            code = "manual_entry_unconfirmed"
            why = (f"No listed batch matches the number you entered, but a typing error could hide a match. "
                   f"Compare the number with the pack and tick the confirmation box to continue. {CONFIRMATION_MEANING}")
        else:
            code = "ocr_batch_unconfirmed"
            why = (f"The batch number was read from the photo as '{batch_raw}', and no listed batch matches or resembles it. "
                   "OCR can misread look-alike characters (S and 5, O and 0, I and 1), so 'No alert found' is shown only after "
                   "you compare this number with the one printed on the pack, correct it if needed, and confirm it below. "
                   f"{CONFIRMATION_MEANING}")
        return Decision(
            status=Status.UNABLE_TO_VERIFY, reason_code=code, headline=Status.UNABLE_TO_VERIFY.value, explanation=why,
            caveats=(f"Only the {dataset_period} CDSCO NSQ list was checked.", LIMITATION_TEXT),
            evidence=match.evidence, batch_source=batch_source, batch_as_read=batch_raw,
        )
    d = _decide_core(
        system_failure=system_failure, batch_state=batch_state, match=match, expiry=expiry,
        dataset_period=dataset_period, expiry_anomaly=expiry_anomaly,
    )
    if d.is_system_error or batch_state is not FieldState.READ or match is None:
        return d
    explanation, caveats = d.explanation, d.caveats
    if d.status in (Status.NO_ALERT_FOUND, Status.EXPIRED) and entry_confirmed:
        if d.status is Status.NO_ALERT_FOUND and batch_raw:
            explanation += f" Batch checked: {batch_raw} (confirmed by you against the pack)."
        caveats = (_CONFIRM_NOTE, *caveats)
    if manual:
        explanation = explanation.replace("The batch number read from the photo", "The batch number you entered")
        explanation = explanation.replace("for the batch read from the photo", "for the batch you entered")  # No alert found / Expired wording
        caveats = (_SOURCE_NOTE[batch_source], *caveats)
    return replace(d, explanation=explanation, caveats=caveats, batch_source=batch_source, batch_as_read=batch_raw,
                   batch_confirmed=bool(entry_confirmed and d.status in (Status.NO_ALERT_FOUND, Status.EXPIRED)),
                   action_check=alert_action_check(batch_raw) if d.status is Status.ALERT_FOUND else "")
