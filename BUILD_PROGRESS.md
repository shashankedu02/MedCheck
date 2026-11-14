# MedCheck Build Progress

Single source of truth for resuming development. Update at the end of every milestone/session.

## Current milestone
M3 - Product parsing and batch matching (next)

## Milestones
| ID | Milestone | Status |
|---|---|---|
| M0 | Repo baseline, .gitignore/.gitattributes, venv, pinned deps | DONE |
| M1 | Reproducible dataset pipeline, manifest/hashes, fail-closed loader | DONE |
| M2 | Normalization, date parsing, decision engine (truth-table tests) | DONE |
| M3 | Product parsing and batch matching incl. serial 38/157 collision | todo |
| M4 | Image validation, preprocessing, OCR adapter, field extraction | todo |
| M5 | Pipeline + Streamlit UI + privacy/error handling | todo |
| M6 | Evaluation tooling, docs reconciliation, review guide, final README | todo |

## M0 report (done)
- Baseline commit `78cc8d6` (docs + legacy CSV + official extraction, byte-identical blobs verified; `.gitattributes` stops CRLF conversion of data).
- Legacy CSV backup: `data/archive/cdsco_august_2026_nsq.legacy_local.csv`, SHA-256 `5123e163...afa15` (matches original).
- `.venv` created; `requirements.txt` pinned; imports verified (cv2 5.0.0, Tesseract 5.5.3 via pytesseract).
- Tests run: none yet (import smoke test only).

## M1 report (done)
- Created: `medcheck/config.py`, `medcheck/dataset.py`, `scripts/build_dataset.py`, `data/dataset_manifest.json`, `tests/test_dataset.py`; regenerated canonical `data/cdsco_august_2026_nsq.csv` (sha256 `980efb50...1036`, 220 records); rewrote `docs/DATASET.md`.
- Legacy CSV replaced only after verified backup (archive + git baseline).
- Tests: `.venv\Scripts\python.exe -m pytest -q` -> **18 passed**. Build `--check` OK.
- Limits: official extraction trusted via pinned hash + the extraction log; no screenshots exist.

## M2 report (done)
- Created: `medcheck/models.py`, `normalization.py`, `dates.py`, `decision.py`; `tests/test_normalization_dates.py`, `tests/test_decision.py`; rewrote `docs/DECISIONS.md`, `docs/EXPIRY_POLICY.md`.
- Tests: `.venv\Scripts\python.exe -m pytest -q` -> **71 passed** (one real parser gap, 'Sept', found by tests and fixed).
- Behaviour: `Expired` never emitted (D-007 OPEN); system errors are not statuses; exhaustive grid test over all input combinations.

## Verified environment
Windows 11, Python 3.13.5, Tesseract 5.5.3 (`eng`, `osd` only), Git 2.56.1.

## Known blockers
None.

## Open owner decisions (safe defaults in force)
- Month-only expiry interpretation: `Expired` is never emitted until approved.

## Next action
Write `medcheck/product.py`, `medcheck/matching.py`, `docs/MATCHING.md`, matching tests (incl. serials 38/157).
