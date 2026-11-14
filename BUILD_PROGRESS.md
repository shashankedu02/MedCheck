# MedCheck Build Progress

Single source of truth for resuming development. Update at the end of every milestone/session.
Run tests with: `.venv\Scripts\python.exe -m pytest -q`

## Current state
**M11 (D-026 confirmation policy)** is done: no clean negative (`No alert found` / `Expired`) is shown for any batch string until the user has compared it with the pack and confirmed; `Alert found` is never delayed. Triggered by a loosely cropped T003 read as `HLA50019` by both engines (true `HLAS0019`).

**M10 (V2 manual-testing review)** is done: see `docs/V2_REVIEW.md` and D-025. No safety rule changed; held-out photographs still untouched.

**V2 (M9) is implemented**: RapidOCR primary engine with Tesseract as extra evidence/fallback, glue-aware parser, rotation/crop cascade, manual batch entry (D-022..D-024). Real-photograph accuracy is still **not** evaluated (diagnostic runs on 20 development photos only; 7 photos are reserved and untouched).

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

**M7 (real-photograph evaluation workflow)** - `medcheck/real_eval.py`, `scripts/run_evaluation.py`, `scripts/set_ground_truth.py`, `tests/test_real_eval.py` (10 tests). Runs `evaluation/incoming_photos/` through the unchanged pipeline; per-run folders under `evaluation/results/runs/` (never overwritten), latest copies in `evaluation/results/`; ground truth separate (`evaluation/ground_truth.csv`, all Pending). Photos and results are git-ignored (private). Command: `.\.venv\Scripts\python.exe scripts\run_evaluation.py`.
- First real run (`run_20261114_200938`): 27 files, 27 produced a verification outcome, 0 failures, originals unchanged. **All 27 = Unable to verify** (25 no batch label found, 2 ambiguous batch). OCR text on these photos is mostly noise. No ground truth exists, so nothing is scored; no thresholds or rules were changed in response.

**M8 (OCR investigation, no production change)** - see `docs/OCR_INVESTIGATION.md`; scripts in `experiments/ocr_investigation/` (outputs git-ignored). Held-out T009/T012/T015/T018/T021/T024/T027 never opened. Finding: engine (Tesseract vs a detector-based engine such as RapidOCR) dominates; orientation and crop are secondary; preprocessing/scale/denoise did not matter. Needs owner decision D-022 (new dependency) before implementing.

**M9 (V2: RapidOCR, parser, cascade, manual entry)** - `medcheck/ocr_rapid.py`, `regions.py`, parser/guards in `extraction.py`, cascade + `verify_manual` in `pipeline.py`, `BatchSource` provenance in `models.py`/`decision.py`, manual-entry UI in `app.py`, `requirements-ocr.txt` (pinned, `--no-deps`), model SHA-256 pins in `config.py`, `docs/OCR_ENGINES.md`, tests `test_v2_*.py` (+ additions to `test_app.py`, `test_pipeline.py`, `test_real_eval.py`). Safeguards unchanged: strict agreement, near-neighbour abstention (edit distance 2), O/0 collision (38/157), product corroboration, expiry disabled.
- **Diagnostic comparison on the same 20 development photos** (baseline `run_20261114_200938` rescored as `run_20261114_224752`; V2 final `run_20261114_224212`; the two earlier V2 runs `..._222616` and `..._223449` were pre-guard and are kept as history):

| | Baseline (Tesseract) | V2 |
|---|---|---|
| Outcomes | 20 x Unable to verify | 15 x Unable to verify, 5 x No alert found |
| Batch state | 18 not found, 2 ambiguous | 5 read, 9 ambiguous, 6 not found |
| Exact vs the 7 certain references | 0 | 3 (T006, T013, T014) |
| Incorrect reads accepted (certain refs) | 0 | 0 |
| Ambiguous (abstained) on certain refs | 1 | 4 (T003, T010, T011, T026: conflicting or single-pass readings) |
| Dates read (expiry / mfg) | 0 / 0 | 7 / 7 (not scored; expiry disabled) |
| Seconds per photo (mean / median / max) | 6.7 / 6.8 / 9.4 | 14.0 / 13.7 / 23.2 |

- **Safety findings during the diagnostic runs (fixed, with tests):** `30 deg C. Protect` (sentence fragment after a stray label) was accepted as a batch in the second V2 run and produced `No alert found` (T023); parser now rejects characters never seen in a listed batch and letter runs longer than 5, and ignores lines touching the image/crop edge. T019 was wrongly suspected to be cut off (erratum in `docs/OCR_INVESTIGATION.md`); its `SIH1166A` looks complete.
- **Open items for the owner:** (1) T008 returns `25S3GTA4` from both views and gives `No alert found`, but an embossed dimple may hide a further character; check T008 on the pack. (2) The seven certain references were read by eye by an AI model and need confirming on the physical packs. (3) Remaining `No alert found` results on development photos: T006, T013, T014 (exact), T008 (unverified), T019 (plausible).
- **Not done (by instruction):** the 7 reserved photographs were not opened or processed; no 60-image evaluation.

**M10 (V2 manual-testing review)** - `docs/V2_REVIEW.md`, scripts in `experiments/v2_review/`. Findings: startup `ImportError` = stale running server (reproduced, not a defect; app now shows a restart message); strict agreement is the only policy that accepted zero wrong batches in replay; dropped-`F` (`MG.JUL.2025`) caused both the missing manufacturing date and the date glued into the batch; erratic times were the engine's default ONNX threading (10.9 s vs 0.5 s per pass, identical text). Changes: bounded ONNX threads, warm-up, Tesseract concurrent (interleaved A/B: 52.8 s -> 38.9 s over 8 photos, identical decisions in 72 runs), date/glue fixes, look-alike conflict explanation, confirmation cleared on edit. Tested and rejected: looser agreement, early-stop rotations, batch-line re-read.
- Dev run `run_20261115_004829` vs the previous V2 run on the same 20 photos: outcomes and batch results identical (5 No alert found, 3 exact, 0 wrong, 4 abstained on the certain references); dates read 7 -> 8 (manufacturing) and 7 -> 8 (expiry). That run was slower (mean 21 s, max 63 s) because of background load, not the changes (see the interleaved A/B).

**M11 (D-026: clean negatives need the user's confirmation)** - `decision.py` (gate and wording), `models.py` (`Decision.batch_confirmed`), `app.py` (label "agreed by the OCR passes - not yet checked against the pack", checkbox and caption explaining that confirmation checks the printed number only), `real_eval.py` (withheld negative scored Inconclusive, counted as awaiting confirmation), tests, docs (`PROJECT_SPEC`, `UI_UX_GUIDELINES`, `MATCHING`, `README`, `CLAUDE`, `ARCHITECTURE`, `OCR_ENGINES`, `EVALUATION`, `TESTING_GUIDELINES`, `DECISIONS` D-026, `V2_REVIEW` addendum).
- **Reproduced** with the reporter's file (read-only): both RapidOCR views read `HLA50019` on every run; strict agreement accepted it; nearest listed batch is 4-5 edits away, so no match and `No alert found`. Root cause: the look-alike safeguards are relative to listed batches or to disagreement between readings; they cannot see two engines agreeing on the same wrong character, and automatic S/5 substitution is forbidden. My earlier review had overstated strict agreement's protection ("correctly conservative") and the UI said "read consistently"; both corrected.
- **After the fix, same file:** `Unable to verify [ocr_batch_unconfirmed]`; user cannot confirm -> stays Unable; correct to `HLAS0019` and confirm -> `No alert found` (user_corrected); ticking `HLA50019` without looking -> recorded as the user's confirmation (no software can prevent that).
- **Dev run `run_20261115_013421`** (same 20 photos, reserved 7 untouched): 20 x Unable to verify; the 5 clean negatives (T006, T008, T013, T014, T019) are withheld as `ocr_batch_unconfirmed`; batch results unchanged (3 exact, 0 incorrect, 4 abstained on the certain references). Alerts are unaffected (none occur in the dev set).
- Tests: the old xfail for the gap now passes as a normal test; 12 existing tests updated for the new policy; one vacuous UI assertion (matched the page disclaimer) made strict; new tests for every batch source, `Expired`, alerts never delayed, grid invariant, UI wording and evaluation scoring.

## Test results (last run)
- **After M11, main venv:** `pytest -q` -> **343 passed** (70 s).
- (Older) After M10: 322 passed.
- **After M10, main venv:** `pytest -q` -> **322 passed** (217 s on a loaded machine).
- (Older) **V2 before the review, fresh venv**: 294 passed.
- **V2, fresh venv built only from `requirements.txt` + `requirements-ocr.txt --no-deps`**: `pytest -q` -> **294 passed** (140 s). `pip check` reports only the expected `opencv-python` note for rapidocr-onnxruntime.
- (Older) **Main venv after M7**: `pytest -q` -> **204 passed** (about 117 s). Earlier fresh-venv run before M7: 194 passed.
- (Older) **Fresh venv built only from `requirements.txt`** (before M7): `pytest -q` -> **194 passed** (about 34 s).
- Live app: `streamlit run app.py` started, `/_stcore/health` = ok, socket on 127.0.0.1 only.
- Not run: any evaluation on real photographs.

## Known blockers
None.

## What remains (needs the owner or real data)
1. **Confirm the reference batches and T008 on the physical packs** (see M9 open items), then add `ground_truth.csv` labels (`scripts/set_ground_truth.py`) and rescore.
2. **D-007 expiry policy**: unchanged (disabled). Dates are being read (7/7 on the development set) but not used.
3. **Held-out run**: after the design is frozen, run `scripts/run_evaluation.py --include-heldout` once on T009, T012, T015, T018, T021, T024, T027 and report as is.
4. **D-014 60-image evaluation** per `docs/EVALUATION.md` before any accuracy claim.
5. **Antigravity review** per `docs/REVIEW_PROCESS.md` (suggest M3, M5 and M9).
6. Possible improvements (need evidence from labelled photos): deskew/perspective, speed (the cascade costs about 14 s per photo), reading batches hidden by embossing, a dark-ink-on-gold strategy.

## Verified environment
Windows 11, Python 3.13.5, Tesseract 5.5.3 (`eng`, `osd` only), Git 2.56.1, streamlit 1.67.0, opencv-python-headless 5.0.0.93, numpy 2.5.4, pillow 13.0.0, RapidFuzz 3.14.6, pytest 9.2.0.

## Next action
Owner: confirm the reference batches and T008 on the packs; then decide whether to run the held-out photographs.

(Older) Owner: decide D-022 (RapidOCR dependency) and confirm the 7 reference batches against the physical packs. Then implement V2 per `docs/OCR_INVESTIGATION.md` section 9 (parser first).

(Older) 
Owner decisions D-007 and D-014 (above); then the Antigravity review.
