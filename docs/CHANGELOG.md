# Changelog

## 2026-11-15 - completion sprint (M13)
- D-027: every `Alert found` shows "Check before acting" (batch character by character, product, strength, manufacturer) with the batch read beside the listed batch; listed neighbouring batches are named. Alerts are not delayed; no matching rule or threshold changed.
- D-028: `medcheck/evaluation.py` counts results awaiting confirmation separately; listed packs misread into unlisted strings are reported as potential misses.
- Synthetic fixtures carry an in-frame "TEST FIXTURE" banner and a manifest; new neighbour fixture; `scripts/run_fixture_check.py` records fixture runs apart from real-photo runs.
- Documentation reconciled; assessment `docs/EVALUATION_STRATEGY.md`; poster facts `docs/POSTER_FACTS.md`.

## 2026-11-15 - reserved-photo evaluation and owner browser tests
- One-time run of the unchanged pipeline (`c83ecf3`) on the 7 reserved photos: `docs/HELDOUT_EVALUATION.md`. 0 wrong batches among 4 certain references, 1 exact, 3 abstained; a likely wrong truncated reading (T009) was withheld by D-026. Records only; no tuning.
- The owner's four manual browser tests recorded in `docs/EVALUATION.md` (user-performed; not accuracy evidence).
- The reserved photographs are now spent.

## 2026-11-15 - D-026: clean negatives need the user's confirmation
- A loosely cropped T003 was read as `HLA50019` by both OCR views (true `HLAS0019`), shown as "read consistently" and gave `No alert found`. Reproduced; root cause and corrected claims in `docs/V2_REVIEW.md` (addendum).
- No `No alert found` / `Expired` for any batch string (OCR-read, corrected or typed) until the user has compared it with the pack and confirmed; `Unable to verify` until then; `Alert found` never delayed. Label "read consistently" replaced by "agreed by the OCR passes - not yet checked against the pack". Matching, thresholds, dataset unchanged; no automatic S/5 substitution.
- Evaluation tooling records withheld negatives (`ocr_batch_unconfirmed`) and scores them Inconclusive.

## 2026-11-15 - V2 manual-testing review (D-025)
- Diagnosed the startup `ImportError` (stale server modules after a code update; reproduced); the app now shows a restart instruction.
- Speed: bounded ONNX threads (removes 10-20x outliers, same text), engine warm-up at start, Tesseract concurrent with RapidOCR (-26% in an interleaved A/B).
- Dates: dropped-F `MG.JUL.2025` handled safely, glued month cut from the batch, `JUN25` / `MfgDt:` forms read.
- Look-alike-only conflicts explained (`5 or S`); manual-entry confirmation cleared on edit.
- Evidence and rejected alternatives: `docs/V2_REVIEW.md`.

## 2026-11-14 - V2: RapidOCR integration, glue-aware parser, manual batch entry (D-022..D-024)
- RapidOCR primary engine (pinned in `requirements-ocr.txt`, offline, model hashes verified), Tesseract retained as extra evidence and fallback; pack-region crop; rotation retries only when no batch label was found; one bounded confirmation pass; strict agreement, near-neighbour abstention, O/0 collision and product corroboration unchanged.
- Batch parser cuts glued labels (`5BA1617MFD`, `...146M.R`), reads a value on the next line, rejects label words; every reading keeps engine/view provenance.
- Manual batch entry with `BatchSource` provenance and a confirmation requirement for typed clean negatives; `No alert found` shows the batch checked.
- Evaluation: held-out photographs excluded by default, independent batch reference scoring. Details: `docs/OCR_ENGINES.md`, `docs/OCR_INVESTIGATION.md`.

## 2026-11-14 - real-photograph evaluation workflow
- `scripts/run_evaluation.py`, `scripts/set_ground_truth.py`, `medcheck/real_eval.py`: per-run, non-overwriting CSV/Markdown records for photos in `evaluation/incoming_photos/`; ground truth kept separate and initially Pending. See `docs/EVALUATION.md`.

## 2026-11-14 - first implementation (milestones M0-M6)
- Baseline commit of the pre-implementation documentation and datasets; `.gitattributes` keeps data byte-exact.
- Canonical dataset generated reproducibly from the official CDSCO extraction (pinned SHA-256), manifest, fail-closed loader.
- Normalization, month-year parsing, four-status decision engine with separate system errors; `Expired` disabled pending owner policy (D-007).
- Product parsing and batch-led matching with confusable-collision handling (serials 38/157).
- Image validation, preprocessing, local Tesseract via stdin, label-anchored extraction with strict cross-pass agreement.
- Pipeline and Streamlit UI; localhost-only, no telemetry, no image persistence.
- Evaluation tooling and demo set; documentation consolidated (superseded documents moved to `docs/archive/`); review process for Antigravity.
- Test suite and results: see `BUILD_PROGRESS.md`.

## 2026-11-13 - pre-implementation documentation package
Documentation-only package (superseded; preserved in `docs/archive/`).
