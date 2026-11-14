# MedCheck Build Progress

Single source of truth for resuming development. Update at the end of every milestone/session.

## Current milestone
M1 - Dataset pipeline and fail-closed loader (in progress)

## Milestones
| ID | Milestone | Status |
|---|---|---|
| M0 | Repo baseline, .gitignore/.gitattributes, venv, pinned deps | DONE |
| M1 | Reproducible dataset pipeline, manifest/hashes, fail-closed loader | in progress |
| M2 | Normalization, date parsing, decision engine (truth-table tests) | todo |
| M3 | Product parsing and batch matching incl. serial 38/157 collision | todo |
| M4 | Image validation, preprocessing, OCR adapter, field extraction | todo |
| M5 | Pipeline + Streamlit UI + privacy/error handling | todo |
| M6 | Evaluation tooling, docs reconciliation, review guide, final README | todo |

## M0 report (done)
- Baseline commit `78cc8d6` (docs + legacy CSV + official extraction, byte-identical blobs verified; `.gitattributes` stops CRLF conversion of data).
- Legacy CSV backup: `data/archive/cdsco_august_2026_nsq.legacy_local.csv`, SHA-256 `5123e163...afa15` (matches original).
- `.venv` created; `requirements.txt` pinned; imports verified (cv2 5.0.0, Tesseract 5.5.3 via pytesseract).
- Tests run: none yet (import smoke test only).

## Verified environment
Windows 11, Python 3.13.5, Tesseract 5.5.3 (`eng`, `osd` only), Git 2.56.1.

## Known blockers
None.

## Open owner decisions (safe defaults in force)
- Month-only expiry interpretation: `Expired` is never emitted until approved.

## Next action
Write `scripts/build_dataset.py`, manifest, `medcheck/dataset.py`, tests.
