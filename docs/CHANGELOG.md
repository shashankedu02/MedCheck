# Changelog

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
