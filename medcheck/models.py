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

    @property
    def is_system_error(self) -> bool:
        return self.system_failure is not None
