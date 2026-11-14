# MedCheck Build Progress

Single source of truth for resuming development. Update at the end of every milestone/session.
Run tests with: `.venv\Scripts\python.exe -m pytest -q`

## Current state
All milestones M0-M6 are complete and committed. The application starts, accepts uploads, runs local OCR, extracts fields, matches against the dataset, and handles all four outcomes plus system errors. **Real-photograph accuracy has not been evaluated** (D-014 open), and `Expired` is intentionally disabled (D-007 open). See "What remains".

## Milestones
| ID | Milestone | Status |
|---|---|---|
| M0 | Repo baseline, .gitignore/.gitattributes, venv, pinned deps | DONE |
| M1 | Reproducible dataset pipeline, manifest/hashes, fail-closed loader | DONE |
| M2 | Normalization, date parsing, decision engine (truth-table tests) | DONE |
| M3 | Product parsing and batch matching incl. serial 38/157 collision | DONE |
| M4 | Image validation, preprocessing, OCR adapter, field extraction | DONE |
| M5 | Pipeline + Streamlit UI + privacy/error handling | DONE |
| M6 | Evaluation tooling, docs reconciliation, review guide, final README | DONE |

## Reports
**M0** - baseline commit `78cc8d6` (byte-identical data blobs; `.gitattributes` stops CRLF conversion that had corrupted the committed data bytes); legacy CSV backup in `data/archive/` (hash-verified); `.venv` + pinned `requirements.txt`.

**M1** - `medcheck/config.py`, `dataset.py`, `scripts/build_dataset.py`, `data/dataset_manifest.json`; canonical `data/cdsco_august_2026_nsq.csv` (sha256 `980efb50e79cca3590cf2de9510609cf282140bb193126a5451d756b1d581036`, 220 records) built from the pinned official extraction. The official extraction was independently re-checked first (220 rows, serials 1-220, 22 pages, ASCII, 12 line-break cells; matches the extraction log).

**M2** - `models.py`, `normalization.py`, `dates.py`, `decision.py`. `Expired` never emitted (D-007 OPEN). Tests found and fixed a parser gap ("Sept").

**M3** - `product.py`, `matching.py`, `docs/MATCHING.md`. Serials 38/157 collide in both directions. Tests found and fixed a gap (serial 145 `DEC-Plus`, a brand-only dataset name). Simulated (no OCR): full label text -> 218/220 rows confirm; product name only -> 204; 38/157 always abstain.

**M4** - `image_input.py`, `preprocessing.py`, `ocr.py`, `extraction.py`. Tesseract is called directly with the image on stdin (no temp files; pytesseract dropped). Known limit: 2-character batches (serials 24, 26) are never extracted.

**M5** - `pipeline.py`, `app.py`, `.streamlit/config.toml` (localhost only, no telemetry, 10 MB cap). Verified through real Tesseract and the real Streamlit widgets (upload, camera, button). A live server was launched: health 200, listening on 127.0.0.1 only. Bugs found by tests and fixed: server bound to all interfaces; a corrupt upload crashed the preview before the friendly rejection.

**M6** - `evaluation.py` + `scripts/evaluate.py` (abstentions stay in denominators, Wilson intervals), `scripts/make_demo_images.py` (+ test that every README demo row is true), `docs/EVALUATION.md`, `docs/REVIEW_PROCESS.md`; README, CLAUDE.md, AGENTS.md, TECH_STACK, TESTING_GUIDELINES, WORKFLOWS, CHANGELOG rewritten; superseded docs moved to `docs/archive/` with `git mv`; stale MANIFEST.md removed (hashes obsolete; in git history); pandas removed from requirements; docs link test added.

## Test results (last run)
- **Fresh venv built only from `requirements.txt`**: `pytest -q` -> **194 passed** (about 34 s).
- Live app: `streamlit run app.py` started, `/_stcore/health` = ok, socket on 127.0.0.1 only.
- Not run: any evaluation on real photographs.

## Known blockers
None.

## What remains (needs the owner or real data)
1. **D-007 expiry policy**: approve how month-only expiry dates are interpreted, then set `config.EXPIRY_POLICY_APPROVED = True` (logic and boundary tests already exist) and update `docs/EXPIRY_POLICY.md` and `docs/DECISIONS.md`.
2. **D-014 evaluation**: collect and label the 60 real photographs (source, consent, split), then run `scripts/evaluate.py` per `docs/EVALUATION.md`. Tune `config.py` thresholds on the `dev` split only. Until then make no accuracy claims.
3. **Antigravity review**: follow `docs/REVIEW_PROCESS.md` (suggest starting with M3 and M5), then ask Claude Code to reconcile the findings.
4. Possible improvements once real photos exist: deskew/perspective correction, relaxing the strict all-passes-agree batch rule if abstention is too high (must be justified by evaluation), more label vocabularies.

## Verified environment
Windows 11, Python 3.13.5, Tesseract 5.5.3 (`eng`, `osd` only), Git 2.56.1, streamlit 1.67.0, opencv-python-headless 5.0.0.93, numpy 2.5.4, pillow 13.0.0, RapidFuzz 3.14.6, pytest 9.2.0.

## Next action
Owner decisions D-007 and D-014 (above); then the Antigravity review.
