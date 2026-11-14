"""Typed data contracts shared across MedCheck stages.

Keep OCR confidence, extraction confidence, string similarity and the identity
decision as separate things: none of the numeric values here is a probability
that a medicine is or is not on the NSQ list.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Status(str, Enum):
    """The four user-facing outcomes. Exact labels are part of the contract."""

    ALERT_FOUND = "Alert found"
    NO_ALERT_FOUND = "No alert found"
    EXPIRED = "Expired"
    UNABLE_TO_VERIFY = "Unable to verify"


class BatchSource(str, Enum):
    """Where the batch number used for matching came from. Never conflated."""

    OCR = "ocr"  # read by an OCR engine from the photo
    USER_CORRECTED = "user_corrected"  # OCR read something, the user changed it
    USER_ENTERED = "user_entered"  # OCR read nothing usable, the user typed it


class FieldState(str, Enum):
    NOT_FOUND = "not_found"
    AMBIGUOUS = "ambiguous"  # several plausible values, or passes disagree
    READ = "read"  # a single consistent value


class MatchOutcome(str, Enum):
    NO_MATCH = "no_match"  # batch checked against the dataset; nothing qualifies
    CONFIRMED = "confirmed"  # unique exact batch + corroborating identity
    UNCORROBORATED = "uncorroborated"  # exact batch, identity evidence insufficient
    CONFLICT = "conflict"  # exact batch, but product/strength contradicts
    COLLISION = "collision"  # several rows or confusable-equivalent rows
    FUZZY_ONLY = "fuzzy_only"  # near-batch candidates only (retrieval, never proof)


@dataclass(frozen=True)
class MatchAssessment:
    outcome: MatchOutcome
    reason: str
    matched_serial: int | None = None
    candidate_serials: tuple[int, ...] = ()
    evidence: tuple[str, ...] = ()
    source_caveats: tuple[str, ...] = ()


class ExpiryOutcome(str, Enum):
    NOT_READ = "not_read"
    UNPARSEABLE = "unparseable"
    UNDETERMINED = "undetermined"  # parsed, but policy does not allow a verdict
    EXPIRED = "expired"
    NOT_EXPIRED = "not_expired"


@dataclass(frozen=True)
class ExpiryAssessment:
    outcome: ExpiryOutcome
    raw: str | None = None
    note: str = ""


class SystemFailure(str, Enum):
    """System failures are NOT verification results."""

    DATASET_MISSING = "dataset_missing"
    DATASET_SCHEMA = "dataset_schema"
    DATASET_INTEGRITY = "dataset_integrity"
    OCR_ENGINE_UNAVAILABLE = "ocr_engine_unavailable"
    OCR_TIMEOUT = "ocr_timeout"
    INTERNAL = "internal_error"


@dataclass(frozen=True)
class Decision:
    """Either a status or a system failure, never both."""

    status: Status | None
    reason_code: str
    headline: str
    explanation: str
    caveats: tuple[str, ...] = ()
    matched_serial: int | None = None
    system_failure: SystemFailure | None = None
    evidence: tuple[str, ...] = field(default_factory=tuple)
    batch_source: BatchSource = BatchSource.OCR
    batch_as_read: str | None = None  # the batch string that was actually matched (raw)
    batch_confirmed: bool = False  # the user ticked 'I compared this number with the pack' for this result

    @property
    def is_system_error(self) -> bool:
        return self.system_failure is not None


@dataclass(frozen=True)
class ManualEntry:
    """A batch number supplied by the user. Kept apart from OCR evidence everywhere."""

    raw: str
    key: str
    source: BatchSource  # USER_CORRECTED or USER_ENTERED (or OCR when the user merely confirmed the OCR value)
    confirmed: bool  # user ticked "I compared this with the pack"
