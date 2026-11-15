"""End-to-end orchestration: image bytes -> ScanResult. No UI, no persistence.

Failure taxonomy (kept distinct on purpose):
  * ImageRejected  -> the upload is unusable (user can retry); not a verification result
  * system failure -> dataset/OCR/internal problem; shown as "System error", never a status
  * Status         -> an actual verification outcome from the decision engine

OCR cascade (docs/OCR_INVESTIGATION.md, docs/ARCHITECTURE.md):
  1. RapidOCR on the full frame and on the detected pack region (two views);
  2. Tesseract on the pack region as additional evidence (also the fallback if RapidOCR is missing);
  3. ONLY if no batch label was found at all: RapidOCR on the pack region rotated 90/180/270.
All passes are reconciled by the strict-agreement rule; any disagreement is AMBIGUOUS (abstain).
Engine scores are never used as proof of identity.
"""
from __future__ import annotations

import logging
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field, replace
from datetime import date
from typing import Callable

import numpy as np
from PIL import Image

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
from .models import (
    BatchSource,
    Decision,
    ExpiryAssessment,
    ExpiryOutcome,
    FieldState,
    ManualEntry,
    MatchAssessment,
    Status,
    SystemFailure,
)
from .normalization import batch_key
from .ocr import EngineInfo, OCREngineUnavailable, OCRPass, OCRTimeout, find_engine, run_ocr
from .ocr_rapid import RapidEngine
from .preprocessing import make_variants
from .regions import crop_to, detect_pack_region

log = logging.getLogger("medcheck")


class ManualEntryError(ValueError):
    """The typed batch cannot be used. The message is safe to show the user."""


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
    engines: tuple[str, ...] = ()
    manual: ManualEntry | None = None
    # The result the PHOTO itself produced, kept unchanged once the user enters or corrects a batch. `decision`, `match` and
    # `matched_record` above then describe the user's batch; this keeps what the photo said (for example an alert) so a
    # manual entry can never erase it. None until a manual entry exists. Never itself holds a manual entry.
    photo_result: "ScanResult | None" = None

    @property
    def preserved_photo_alert(self) -> "ScanResult | None":
        """The photo's own result when it was `Alert found` and the user has since entered or corrected a DIFFERENT batch
        (so `decision` now describes the user's batch). Renderers must keep showing it. None when there is nothing to keep:
        no manual entry, the photo gave no alert, or the user only confirmed the same OCR reading."""
        photo = self.photo_result
        if photo is None or self.manual is None or self.manual.source is BatchSource.OCR:
            return None
        d = photo.decision
        if d is None or d.is_system_error or d.status is not Status.ALERT_FOUND:
            return None
        return photo

    def preserved_photo_alert_text(self, period: str) -> str:
        """Plain-language explanation shown with the preserved photo alert (one wording for every renderer). It states that the
        photo's batch matched a listed batch, that the user's batch gave a different (or also an alert) result, and that the
        user's result neither cancels nor disproves the photo's alert."""
        photo = self.preserved_photo_alert
        if photo is None or photo.decision is None or self.manual is None:
            return ""
        rec = photo.matched_record
        where = f"listed serial {rec.serial} ({rec.product_name})" if rec is not None else "a listed batch"
        cur = self.decision
        also = cur is not None and not cur.is_system_error and cur.status is Status.ALERT_FOUND
        then = (f"You then entered a different batch ({self.manual.raw}); that batch also gave an alert, shown below." if also else
                f"You then entered a different batch ({self.manual.raw}); that batch gave a different result, shown below.")
        return (f"The batch read from the photo ({photo.decision.batch_as_read}) matched {where} in the {period} CDSCO NSQ list, "
                f"and the product details from the photo corroborated it. {then} That result applies only to the batch you entered: "
                "it does not cancel, disprove or replace the alert for the batch read from the photo. "
                "Compare the batch printed on the pack with both numbers before acting.")


_DATASET_FAILURES = {
    DatasetMissingError: SystemFailure.DATASET_MISSING,
    DatasetSchemaError: SystemFailure.DATASET_SCHEMA,
    DatasetIntegrityError: SystemFailure.DATASET_INTEGRITY,
}
_UNSET = object()


class _Deferred:
    """Future-like wrapper that runs the job when .result() is called (sequential mode)."""

    def __init__(self, job):
        self._job = job

    def result(self):
        return self._job()


class MedCheckPipeline:
    def __init__(self, dataset: Dataset | None, dataset_failure: SystemFailure | None = None,
                 today: Callable[[], date] = date.today, *, rapid_engine=_UNSET, tesseract_engine=_UNSET):
        """`rapid_engine` / `tesseract_engine`: pass None to disable an engine (tests, fallbacks) or an
        object with the adapter interface to inject a stub. Default: discover lazily."""
        self.dataset = dataset
        self.dataset_failure = dataset_failure
        self._today = today
        self.index = DatasetIndex.build(dataset) if dataset is not None else None
        self._records = {r.serial: r for r in dataset.records} if dataset is not None else {}
        if rapid_engine is _UNSET:
            self._rapid = RapidEngine() if config.USE_RAPIDOCR else None
        else:
            self._rapid = rapid_engine
        self._tess = tesseract_engine

    @classmethod
    def load(cls, *, rapid_engine=_UNSET, tesseract_engine=_UNSET, **kwargs) -> "MedCheckPipeline":
        """Load the dataset once. Any dataset problem is remembered as a SYSTEM failure."""
        opts = dict(rapid_engine=rapid_engine, tesseract_engine=tesseract_engine)
        try:
            return cls(load_dataset(**kwargs), **opts)
        except DatasetError as exc:
            failure = next((v for k, v in _DATASET_FAILURES.items() if isinstance(exc, k)), SystemFailure.DATASET_INTEGRITY)
            log.error("dataset failure: %s", exc.code)
            return cls(None, failure, **opts)

    def warm_up(self) -> None:
        """Best effort: initialise OCR engines now (never raises; a real check reports any engine problem)."""
        try:
            if self._rapid is not None and hasattr(self._rapid, "warm_up"):
                self._rapid.warm_up()
        except Exception:  # noqa: BLE001
            log.error("warm-up failed")

    # ------------------------------------------------------------------
    def check(self, image_bytes: bytes) -> ScanResult:
        started = time.monotonic()
        try:
            return self._check(image_bytes, started)
        except Exception as exc:  # last resort: never crash the UI, never leak content
            log.error("internal error: %s", type(exc).__name__)
            return ScanResult(decision=system_error_decision(SystemFailure.INTERNAL), elapsed_seconds=time.monotonic() - started)

    def _tesseract(self) -> EngineInfo | None:
        if self._tess is _UNSET:
            try:
                self._tess = find_engine()
            except OCREngineUnavailable:
                self._tess = None
        return self._tess  # type: ignore[return-value]

    def _collect_passes(self, img: Image.Image, deadline: float, notes: list[str]):
        """Stages 1+2. Returns (passes, engine version strings, pack crop or None, RapidOCR views by name)."""
        passes: list[OCRPass] = []
        versions: list[str] = []
        views_by_name: dict[str, Image.Image] = {}
        try:
            region = detect_pack_region(img)
        except Exception:  # noqa: BLE001 - region detection is an optimisation, never a failure
            region = None
        crop = crop_to(img, region) if region else None
        if region is None:
            notes.append("No separate pack region was detected; the full photo was used.")

        # Tesseract (a separate process) runs concurrently with RapidOCR instead of after it: same passes, same
        # results, less waiting. Variants are prepared here, in the calling thread.
        tess = self._tesseract()
        tess_variants: list = []
        tess_limit = 0
        tess_pool: ThreadPoolExecutor | None = None
        tess_future = None
        if tess is not None:
            tess_variants = make_variants(crop or img)
            # RapidOCR is primary: Tesseract adds limited extra evidence (all variants only when it is the sole engine)
            tess_limit = config.TESSERACT_EVIDENCE_VARIANTS if self._rapid is not None else len(tess_variants)
            if config.TESSERACT_CONCURRENT:
                tess_pool = ThreadPoolExecutor(max_workers=1)
                tess_future = tess_pool.submit(run_ocr, tess_variants[:tess_limit], tess)
            else:  # sequential: the same job, run after RapidOCR
                tess_future = _Deferred(lambda: run_ocr(tess_variants[:tess_limit], tess))

        if self._rapid is not None:
            try:
                views = [("full_rot0", img)]
                if crop is not None:
                    views.append(("crop_rot0", crop))
                else:
                    f = config.CROP_UPSCALE_WHEN_NO_REGION
                    views.append((f"full_x{f}", img.resize((int(img.width * f), int(img.height * f)), Image.LANCZOS)))
                for name, view in views:
                    if time.monotonic() > deadline:
                        break
                    passes.append(self._rapid.run(np.asarray(view.convert("RGB")), name))
                    views_by_name[name] = view
                versions.append(self._rapid.version)
            except OCREngineUnavailable:
                notes.append("The RapidOCR engine is unavailable; only Tesseract was used.")
                self._rapid = None
                passes = []
                versions = []
                views_by_name = {}

        timed_out = False
        if tess_future is not None:
            try:
                tp, _ = tess_future.result()
                if self._rapid is None and tess_limit < len(tess_variants):  # RapidOCR failed: Tesseract is now the only engine
                    extra, _ = run_ocr(tess_variants[tess_limit:], tess)
                    tp = [*tp, *extra]
                passes.extend(tp)
                versions.append(tess.version)
            except OCRTimeout:
                timed_out = True
                notes.append("Tesseract timed out; its passes were not used.")
            except OCREngineUnavailable:
                notes.append("Tesseract is unavailable; it contributed no evidence.")
            finally:
                if tess_pool is not None:
                    tess_pool.shutdown(wait=True)
        elif tess is None:
            notes.append("Tesseract is not installed; it contributed no evidence.")
        if not passes:
            if timed_out:
                raise OCRTimeout("no OCR pass completed")
            raise OCREngineUnavailable("no OCR engine available")
        return passes, versions, crop, views_by_name

    def _check(self, image_bytes: bytes, started: float) -> ScanResult:
        if self.dataset_failure is not None or self.index is None:
            return ScanResult(decision=system_error_decision(self.dataset_failure or SystemFailure.DATASET_INTEGRITY))

        try:
            validated = load_image(image_bytes)
        except ImageRejected as rej:
            return ScanResult(rejection=rej, elapsed_seconds=time.monotonic() - started)

        img = validated.image
        notes: list[str] = []
        deadline = started + config.OCR_TOTAL_BUDGET_SECONDS
        try:
            passes, versions, crop, views = self._collect_passes(img, deadline, notes)
        except OCREngineUnavailable:
            return ScanResult(decision=system_error_decision(SystemFailure.OCR_ENGINE_UNAVAILABLE),
                              elapsed_seconds=time.monotonic() - started, notes=tuple(notes))
        except OCRTimeout:
            return ScanResult(decision=system_error_decision(SystemFailure.OCR_TIMEOUT),
                              elapsed_seconds=time.monotonic() - started, notes=tuple(notes))

        extraction = extract(passes)
        if self._rapid is not None and extraction.batch.state is FieldState.NOT_FOUND:
            # Stage 3: nothing labelled was found anywhere, so the text may be rotated. Retry rotations of
            # the pack region only. (AMBIGUOUS readings are never "retried until they agree".)
            base = crop if crop is not None else img
            view = "crop" if crop is not None else "full"
            try:
                for deg in config.RAPIDOCR_RETRY_ROTATIONS_DEG:
                    if time.monotonic() > deadline:
                        notes.append("Time budget reached before all rotations were tried.")
                        break
                    rotated = base.rotate(deg, expand=True)
                    name = f"{view}_rot{deg}"
                    passes.append(self._rapid.run(np.asarray(rotated.convert("RGB")), name))
                    views[name] = rotated
                extraction = extract(passes)
            except OCREngineUnavailable:
                notes.append("The RapidOCR engine failed during the rotation retry.")
                extraction = extract(passes)
        extraction = self._confirm_single_view(extraction, passes, views, deadline, notes)

        match = None
        if extraction.batch.state is FieldState.READ:
            match = match_batch(self.index, extraction.batch.key, extraction.product_text)

        expiry = self._expiry(extraction)
        decision = self._decide(extraction, match, expiry, BatchSource.OCR, extraction.batch.raw, False)
        return ScanResult(
            decision=decision,
            extraction=extraction,
            match=match,
            matched_record=self._record_for(decision),
            expiry=expiry,
            engine_version="; ".join(versions),
            variants_used=tuple(sorted({p.pass_id for p in passes})),
            ocr_passes=len(passes),
            elapsed_seconds=time.monotonic() - started,
            notes=tuple(notes),
            engines=extraction.engines,
        )

    def _confirm_single_view(self, extraction: ExtractionResult, passes: list[OCRPass], views: dict[str, Image.Image],
                             deadline: float, notes: list[str]) -> ExtractionResult:
        """If exactly ONE distinct batch reading exists but only one pass supports it, take ONE extra reading of the
        same view at another scale. Strict agreement still applies afterwards: a different reading makes the field
        AMBIGUOUS, and nothing is retried until the readings agree. Bounded to a single extra pass."""
        b = extraction.batch
        if (self._rapid is None or b.state is not FieldState.AMBIGUOUS or not b.reason.startswith("batch seen in only")
                or len({batch_key(r).key for r in b.readings}) != 1 or time.monotonic() > deadline):
            return extraction
        name = next((src.split(":", 1)[1] for _raw, src in b.reading_sources if src.startswith("rapidocr:")), None)
        view = views.get(name) if name else None
        if view is None:
            return extraction
        f = config.CROP_UPSCALE_WHEN_NO_REGION
        scaled = view.resize((int(view.width * f), int(view.height * f)), Image.LANCZOS)
        try:
            passes.append(self._rapid.run(np.asarray(scaled.convert("RGB")), f"{name}_x{f}"))
        except OCREngineUnavailable:
            notes.append("The RapidOCR engine failed during the confirmation pass.")
            return extraction
        notes.append("One confirmation pass was run at a different scale because only one pass had read the batch.")
        return extract(passes)

    # ------------------------------------------------------------------
    def verify_manual(self, prior: ScanResult, text: str, confirmed: bool) -> ScanResult:
        """Re-run the SAME matching/decision rules for a batch typed or corrected by the user.

        The typed value is never stored as OCR evidence: `prior.extraction` is returned unchanged and the
        manual value travels separately (`ScanResult.manual`, `Decision.batch_source`). Product
        corroboration still comes only from the photo's OCR text.
        """
        if self.index is None or self.dataset is None:
            return ScanResult(decision=system_error_decision(self.dataset_failure or SystemFailure.DATASET_INTEGRITY))
        if prior.extraction is None:
            raise ManualEntryError("Check a photo first; the entry is compared using the text read from that photo.")
        raw = (text or "").strip()
        if not raw:
            raise ManualEntryError("Enter the batch number as printed on the pack.")
        if len(raw) > config.MANUAL_BATCH_MAX_CHARS or any(not c.isprintable() for c in raw):
            raise ManualEntryError(f"Batch numbers are at most {config.MANUAL_BATCH_MAX_CHARS} printable characters.")
        bk = batch_key(raw)
        if len(bk.key) < config.MIN_BATCH_KEY_LENGTH or not any(c.isdigit() for c in bk.key):
            raise ManualEntryError(
                f"Enter at least {config.MIN_BATCH_KEY_LENGTH} letters/digits including a digit, as printed on the pack.")

        ocr = prior.extraction.batch
        if ocr.state is FieldState.READ and ocr.key is not None and ocr.key.key == bk.key:
            source = BatchSource.OCR  # the user only confirmed what OCR read
        elif ocr.readings:
            source = BatchSource.USER_CORRECTED
        else:
            source = BatchSource.USER_ENTERED
        match = match_batch(self.index, bk, prior.extraction.product_text)
        expiry = prior.expiry or self._expiry(prior.extraction)
        decision = self._decide(prior.extraction, match, expiry, source, raw, confirmed, batch_state=FieldState.READ)
        return replace(
            prior,
            decision=decision,
            match=match,
            matched_record=self._record_for(decision),
            manual=ManualEntry(raw, bk.key, source, confirmed),
            photo_result=prior.photo_result or prior,  # always the ORIGINAL photo result, also after repeated manual entries
        )

    # ------------------------------------------------------------------
    def _decide(self, extraction: ExtractionResult, match, expiry, source: BatchSource, raw: str | None,
                confirmed: bool, batch_state: FieldState | None = None) -> Decision:
        anomaly = (
            extraction.expiry.state is FieldState.READ
            and extraction.manufacturing.state is FieldState.READ
            and manufacture_after_expiry(extraction.manufacturing.raw, extraction.expiry.raw)
        )
        return decide(
            system_failure=None,
            batch_state=batch_state or extraction.batch.state,
            match=match,
            expiry=expiry,
            dataset_period=self.dataset.reporting_period,
            expiry_anomaly=anomaly,
            batch_source=source,
            batch_raw=raw,
            entry_confirmed=confirmed,
        )

    def _record_for(self, decision: Decision) -> DatasetRecord | None:
        return self._records.get(decision.matched_serial) if decision.matched_serial is not None else None

    def _expiry(self, ex: ExtractionResult) -> ExpiryAssessment:
        if ex.expiry.state is FieldState.AMBIGUOUS:
            return ExpiryAssessment(ExpiryOutcome.NOT_READ, None, "Expiry readings conflicted between passes, so the expiry date is not used.")
        return assess_expiry(ex.expiry.raw, self._today(), config.EXPIRY_POLICY_APPROVED)
