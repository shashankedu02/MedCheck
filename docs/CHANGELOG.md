# Changelog

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
