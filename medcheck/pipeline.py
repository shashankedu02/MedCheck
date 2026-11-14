"""End-to-end orchestration: image bytes -> ScanResult. No UI, no persistence.

Failure taxonomy (kept distinct on purpose):
  * ImageRejected  -> the upload is unusable (user can retry); not a verification result
  * system failure -> dataset/OCR/internal problem; shown as "System error", never a status
  * Status         -> an actual verification outcome from the decision engine
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import date
from typing import Callable

from . import config
from .dataset import (
    Dataset,
    DatasetError,
    DatasetIntegrityError,
    DatasetMissingError,
    DatasetRecord,
    DatasetSchemaError,
    load_dataset,
)
from .dates import assess_expiry, manufacture_after_expiry
from .decision import decide, system_error_decision
from .extraction import ExtractionResult, extract
from .image_input import ImageRejected, load_image
from .matching import DatasetIndex, match_batch
from .models import Decision, ExpiryAssessment, ExpiryOutcome, FieldState, MatchAssessment, SystemFailure
from .ocr import OCREngineUnavailable, OCRPass, OCRTimeout, run_ocr
from .preprocessing import make_variants

log = logging.getLogger("medcheck")


@dataclass(frozen=True)
class ScanResult:
    decision: Decision | None = None
    rejection: ImageRejected | None = None
    extraction: ExtractionResult | None = None
    match: MatchAssessment | None = None
    matched_record: DatasetRecord | None = None
    expiry: ExpiryAssessment | None = None
    engine_version: str | None = None
    variants_used: tuple[str, ...] = ()
    ocr_passes: int = 0
    elapsed_seconds: float = 0.0
    notes: tuple[str, ...] = field(default_factory=tuple)


_DATASET_FAILURES = {
    DatasetMissingError: SystemFailure.DATASET_MISSING,
    DatasetSchemaError: SystemFailure.DATASET_SCHEMA,
    DatasetIntegrityError: SystemFailure.DATASET_INTEGRITY,
}


class MedCheckPipeline:
    def __init__(self, dataset: Dataset | None, dataset_failure: SystemFailure | None = None,
                 today: Callable[[], date] = date.today):
        self.dataset = dataset
        self.dataset_failure = dataset_failure
        self._today = today
        self.index = DatasetIndex.build(dataset) if dataset is not None else None
        self._records = {r.serial: r for r in dataset.records} if dataset is not None else {}

    @classmethod
    def load(cls, **kwargs) -> "MedCheckPipeline":
        """Load the dataset once. Any dataset problem is remembered as a SYSTEM failure."""
        try:
            return cls(load_dataset(**kwargs))
        except DatasetError as exc:
            failure = next((v for k, v in _DATASET_FAILURES.items() if isinstance(exc, k)), SystemFailure.DATASET_INTEGRITY)
            log.error("dataset failure: %s", exc.code)
            return cls(None, failure)

    # ------------------------------------------------------------------
    def check(self, image_bytes: bytes) -> ScanResult:
        started = time.monotonic()
        try:
            return self._check(image_bytes, started)
        except Exception as exc:  # last resort: never crash the UI, never leak content
            log.error("internal error: %s", type(exc).__name__)
            return ScanResult(decision=system_error_decision(SystemFailure.INTERNAL), elapsed_seconds=time.monotonic() - started)

    def _check(self, image_bytes: bytes, started: float) -> ScanResult:
        if self.dataset_failure is not None or self.index is None:
            return ScanResult(decision=system_error_decision(self.dataset_failure or SystemFailure.DATASET_INTEGRITY))

        try:
            validated = load_image(image_bytes)
        except ImageRejected as rej:
            return ScanResult(rejection=rej, elapsed_seconds=time.monotonic() - started)

        try:
            variants = make_variants(validated.image)
            passes, engine = run_ocr(variants)
        except OCREngineUnavailable:
            return ScanResult(decision=system_error_decision(SystemFailure.OCR_ENGINE_UNAVAILABLE), elapsed_seconds=time.monotonic() - started)
        except OCRTimeout:
            return ScanResult(decision=system_error_decision(SystemFailure.OCR_TIMEOUT), elapsed_seconds=time.monotonic() - started)

        extraction = extract(passes)
        match = None
        if extraction.batch.state is FieldState.READ:
            match = match_batch(self.index, extraction.batch.key, extraction.product_text)

        expiry = self._expiry(extraction)
        anomaly = (
            extraction.expiry.state is FieldState.READ
            and extraction.manufacturing.state is FieldState.READ
            and manufacture_after_expiry(extraction.manufacturing.raw, extraction.expiry.raw)
        )
        decision = decide(
            system_failure=None,
            batch_state=extraction.batch.state,
            match=match,
            expiry=expiry,
            dataset_period=self.dataset.reporting_period,
            expiry_anomaly=anomaly,
        )
        record = self._records.get(decision.matched_serial) if decision.matched_serial is not None else None
        return ScanResult(
            decision=decision,
            extraction=extraction,
            match=match,
            matched_record=record,
            expiry=expiry,
            engine_version=engine.version,
            variants_used=tuple(sorted({p.variant_id for p in passes})),
            ocr_passes=len(passes),
            elapsed_seconds=time.monotonic() - started,
        )

    def _expiry(self, ex: ExtractionResult) -> ExpiryAssessment:
        if ex.expiry.state is FieldState.AMBIGUOUS:
            return ExpiryAssessment(ExpiryOutcome.NOT_READ, None, "Expiry readings conflicted between passes, so the expiry date is not used.")
        return assess_expiry(ex.expiry.raw, self._today(), config.EXPIRY_POLICY_APPROVED)
