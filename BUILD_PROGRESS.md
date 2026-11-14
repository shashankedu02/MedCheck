# MedCheck Build Progress

Single source of truth for resuming development. Update at the end of every milestone/session.
Run tests with: `.venv\Scripts\python.exe -m pytest -q`

## Current milestone
M5 - Pipeline, Streamlit UI, privacy/error handling (next)

## Milestones
| ID | Milestone | Status |
|---|---|---|
| M0 | Repo baseline, .gitignore/.gitattributes, venv, pinned deps | DONE |
| M1 | Reproducible dataset pipeline, manifest/hashes, fail-closed loader | DONE |
| M2 | Normalization, date parsing, decision engine (truth-table tests) | DONE |
| M3 | Product parsing and batch matching incl. serial 38/157 collision | DONE |
| M4 | Image validation, preprocessing, OCR adapter, field extraction | DONE |
| M5 | Pipeline + Streamlit UI + privacy/error handling | todo |
| M6 | Evaluation tooling, docs reconciliation, review guide, final README | todo |

## Reports
**M0** - baseline commit `78cc8d6` (byte-identical data blobs; `.gitattributes` stops CRLF conversion); legacy CSV backup in `data/archive/` (hash-verified); `.venv` + pinned `requirements.txt`; imports verified.

**M1** - `medcheck/config.py`, `dataset.py`, `scripts/build_dataset.py`, `data/dataset_manifest.json`, `tests/test_dataset.py`; canonical `data/cdsco_august_2026_nsq.csv` (sha256 `980efb50...1036`, 220 records) built from the pinned official extraction; `docs/DATASET.md` rewritten. 18 tests.

**M2** - `models.py`, `normalization.py`, `dates.py`, `decision.py`; tests for keys, dates, exhaustive decision grid; `docs/DECISIONS.md`, `docs/EXPIRY_POLICY.md` rewritten. `Expired` never emitted (D-007 OPEN). Tests found and fixed a real parser gap ("Sept").

**M3** - `product.py`, `matching.py`, `tests/test_matching.py`, `docs/MATCHING.md` (replaces MATCHING_LOGIC.md + MATCHING_DECISION_MATRIX.md, removed via git rm; recoverable from git history). Serials 38/157 collision enforced in both directions. Tests found and fixed a real gap (serial 145 `DEC-Plus`: a brand-only dataset name produced no identity signal).
Simulated (no OCR) results: full label text -> 218/220 confirm; product name only -> 204 confirm, 14 short-batch rows need more evidence, 38/157 abstain.

**M4** - `image_input.py`, `preprocessing.py`, `ocr.py`, `extraction.py`; tests `test_image_input.py`, `test_extraction.py`, `test_ocr_preprocessing.py`, `tests/helpers.py`; `docs/ARCHITECTURE.md` rewritten; `requirements.txt` drops pytesseract. Deviation: Tesseract is called directly with the image on stdin so nothing touches disk (pytesseract writes temp files). Real Tesseract ran on a synthetic rendered label (plumbing only, not an accuracy result). Known limit: 2-char batches (serials 24, 26) never extracted.

## Test results (last run)
`pytest -q` -> **148 passed** (after M4, ~6 s).

## Known blockers
None.

## Open owner decisions (safe defaults in force)
- D-007 month-only expiry interpretation: `Expired` is never emitted until approved.
- D-014 60-image evaluation not performed; no accuracy claims allowed.

## Docs debt (do in M6)
- `CLAUDE.md`, `README.md`, `MANIFEST.md` still link the removed MATCHING_LOGIC/MATCHING_DECISION_MATRIX files.
- Consolidate/archive redundant meta-reports; MANIFEST.md hashes are stale (delete or regenerate).
- Reconcile AGENTS.md/CLAUDE.md; write review guide for Antigravity.

## Verified environment
Windows 11, Python 3.13.5, Tesseract 5.5.3 (`eng`, `osd` only), Git 2.56.1, streamlit 1.67.0, opencv-python-headless 5.0.0.93, pandas 3.1.1.

## Next action
M5: `medcheck/pipeline.py` (bytes -> Decision, system errors mapped), `app.py` (Streamlit: upload + camera, status, evidence, period, disclaimers), privacy tests, then launch the app for real and verify with AppTest/HTTP.
