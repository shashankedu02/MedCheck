# Evaluation Protocol (D-014 OPEN: not yet performed)

**No accuracy, sensitivity, specificity or time-saving claim may be made about MedCheck until this protocol has been run and the raw per-image results are kept.** The automated test suite proves behaviour on synthetic labels and logic cases; it is not an evaluation of real-world OCR.

## Evidence categories (proposed revision of D-014; owner approval pending)
The original target (60 photographs, 30 of them NSQ-listed) cannot be met: listed batches are withdrawn and must not be obtained. Evidence is therefore kept in separate categories, each reported on its own and **never merged into one percentage** (rationale and test matrix: `docs/EVALUATION_STRATEGY.md`):

| Category | Can show | Cannot show | Rate allowed |
|---|---|---|---|
| C1 Real photos of ordinary packs, labelled from the physical pack by two people before the run, split dev/test by pack | batch-string reading, false alerts on non-listed packs, abstention mix, date reading, time | detection of listed batches | yes, test split only, with Wilson intervals; 0 false alerts in n gives an upper bound of about 3/n |
| C2 Synthetic test fixtures (`scripts/make_demo_images.py`, `scripts/run_fixture_check.py`) | the whole software path including `Alert found`, on clean known inputs | real-world accuracy | fixture pass rate only |
| C3 Programmatic tests (pytest) | rule compliance for all 220 listed rows | anything about OCR | pass/fail only |
| C4 Verified real positives (photos of quarantined NSQ stock, if ever available) | real alert-path behaviour | rates | case counts only |
| C5 Human-confirmation study (planted misreads) | whether users catch misreads before confirming (D-026 depends on it) | OCR accuracy | catch rate, separately |

With n = 30, confidence intervals are wide (for example 27/30 has a 95% Wilson interval of roughly 74-97%); report them, do not round them away.

## Collection (owner decisions still needed)
- Source of packs/photos, permission to photograph, and removal of personal information.
- Realistic conditions: curved foil, glare, blur, low light, rotation, small print, multiple dates, carton plus strip.
- Ground truth from the physical pack and the official list, labelled **before** running the software: `expected_alert`, `expected_serial`, `true_batch` (exactly as printed).
- Split into `dev` (used to tune thresholds in `medcheck/config.py`) and `heldout` (run once, report as is). Never tune on heldout images. Freeze the code version and the dataset hash before the heldout run.
- Store images outside version control (`eval_private/` and `eval_images/` are git-ignored) and delete them when no longer needed.

## Running
```powershell
.\.venv\Scripts\python.exe scripts\evaluate.py --manifest eval_private\manifest.csv --split heldout --out eval_private\results.csv
```
The manifest format is documented in the script header. The script refuses missing or duplicate images and prints, with confidence intervals: alert sensitivity (abstentions count as misses), false negatives (wrong clean negatives) separately from abstentions, false positives, alert precision, abstention rate, decisive coverage, system errors, batch exact accuracy (compared on the comparison key: formatting ignored, look-alikes not folded), median and p95 latency.

Because an automated run never confirms a batch (D-026), clean negatives arrive as `Unable to verify` awaiting confirmation. `medcheck/evaluation.py` counts them in their own category and never as correct: on a non-listed pack they are split into "correct string offered" (ready for the user's confirmation) and "wrong string offered" (the user must catch it); on a listed pack they are reported as **potential misses**, the most dangerous automated outcome, never hidden among abstentions. "Clean No alert found on non-alert images" can only be non-zero when user confirmations are recorded (category C5).

## Reporting rules
Keep every abstained or failed image in the denominators. Report false negatives and false positives separately and discuss each. Record hardware, OS, OCR engine versions (RapidOCR package and Tesseract; both are in each run's `run_info.json`), dataset SHA-256 (from `data/dataset_manifest.json`) and git commit. If the protocol is compromised (labels uncertain, tuning on heldout, leakage), say so and do not claim validated performance.

## Automated real-photograph run (records only, no accuracy claim)
Photographs placed in `evaluation/incoming_photos/` (git-ignored, read-only to the tool) are processed through the unchanged `MedCheckPipeline.check()` with one command:
```powershell
.\.venv\Scripts\python.exe scripts\run_evaluation.py
```
Code: `medcheck/real_eval.py` (no matching logic of its own), `scripts/run_evaluation.py`, `scripts/set_ground_truth.py`. It is separate from the app and from the 60-image metric script above.
- **Test IDs** come from filenames (`7.jpeg` -> `T007`). Duplicate content is flagged (`duplicate_of`); a second file with the same ID, unsupported types and corrupt files get a recorded non-result and never stop the run. The run verifies by SHA-256 that originals are unchanged.
- **Outputs** (git-ignored: they hold OCR text): every run writes `evaluation/results/runs/<run_id>/` (`evaluation_results.csv`, `evaluation_report.md`, `run_info.json` with git commit, dataset hash and period, Tesseract version). Run IDs never collide, so history is never overwritten. `evaluation/results/evaluation_results.csv` and `evaluation_report.md` are copies of the latest run.
- **Three separate fields**: actual outcome (what MedCheck said), expected outcome (ground truth), evaluation status (`Correct`, `Incorrect`, `Pending`, `Inconclusive`). Everything is `Pending` until a label exists; a system error or rejected image is `Inconclusive`; an abstention where a decisive answer was expected is `Incorrect` (a miss).
- **Ground truth** lives in `evaluation/ground_truth.csv` (tracked: labels only). It must come from the physical pack and the official list, never from MedCheck's output:
```powershell
.\.venv\Scripts\python.exe scripts\set_ground_truth.py T005 "Alert found" --serial 4 --batch <as printed> --verified-by "<who/what established it>"
.\.venv\Scripts\python.exe scripts\run_evaluation.py --rescore <run_id>
```
`--rescore` re-applies current labels to a past run's recorded outputs as a new run, without re-processing.
- Extracted product/manufacturer information is only the raw OCR text (truncated, in the CSV); there is no manufacturer extractor. The matched dataset record's product and manufacturer are shown separately when an alert fires.
- Do not tune thresholds on these photographs unless they are designated `dev` under the protocol above.
- **Held-out set (spent on 2026-11-15, see `docs/HELDOUT_EVALUATION.md`).** `evaluation/heldout_ids.txt` reserved T009, T012, T015, T018, T021, T024, T027. `run_evaluation.py` skips them by default: the files are not opened, no placeholder label is created and the report names the exclusion. They are processed only with `--include-heldout`, once, after the design is frozen. Rescoring also excludes them.
- **Independent batch reference.** `evaluation/reference_batches.csv` holds batches read by eye from zoomed crops (not from MedCheck output). Only tier `certain` is scored (`exact`, `incorrect`, `ambiguous`, `not_found`); `probable` rows are shown as `unscored`. The reference was produced by an AI model reading re-encoded photos and is **awaiting owner confirmation against the physical packs**; these counts are diagnostics, not accuracy figures.
- **Clean negatives (D-026).** The tool cannot confirm a batch against a pack, so a clean negative is recorded as `Unable to verify` with reason `ocr_batch_unconfirmed` (the match outcome column still shows `no_match`). Against a `No alert found` label this is scored `Inconclusive`, not a miss; the batch string itself is scored through `batch_result`. The report counts these as "awaiting confirmation".
- Records include engine provenance (`engines`, `batch_sources`: every raw reading with the engine and image view that produced it).

## Manual browser tests performed by the owner (build `c83ecf3`, 2026-11-15)
Recorded as **user-performed** tests: the owner ran them in the browser and reported the observations; they were not run or observed by the assistant, and they do not establish OCR accuracy. Photo: the owner's loosely cropped T003 (`D:\3_loosely-croped.jpeg`, not stored in the repository). The assistant's own read-only reproduction of the same file (same extraction, same decision, 2 runs) is separate and is recorded in `docs/V2_REVIEW.md`.

| # | What the owner did | What the owner observed | Result |
|---|---|---|---|
| 1 | Checked the loosely cropped T003 photo | Batch `HLA50019`, expiry `JUN.2028`, manufacturing `JUL.2025` extracted and shown as separate fields, apart from the surrounding packaging text. The printed batch appeared to be `HLAS0019`; both OCR passes agreed on the wrong `HLA50019`. The app returned `Unable to verify` (D-026) | Field separation worked; the S/5 misread was real; abstention as designed |
| 2 | Left the OCR reading uncorrected | `Unable to verify`; the S/5 look-alike risk was explained; the app asked for a comparison with the pack; `No alert found` was not shown before confirmation | Passed |
| 3 | Replaced `HLA50019` with `HLAS0019`, ticked the confirmation, submitted | Original OCR reading preserved; corrected batch displayed separately and identified as user-corrected; `No alert found` for the corrected batch against the configured dataset; limitations of the result explained | Passed |
| 4 | Entered `HLAS0019`, ticked the confirmation, then changed the batch to `HLAS0020` | The checkbox cleared by itself; pressing the button without confirming the new number returned `Unable to verify` | Passed |

What these show: the review fixes behave as intended in a real browser session, including the confirmation policy and the edit-clears-confirmation rule (also covered by an automated test). What they do not show: any OCR accuracy figure, correctness of the dataset match for other packs, or that the medicine is genuine or safe. Historical evaluation runs are unchanged.

## Reserved-photo evaluation
The seven reserved photographs were processed once on 2026-11-15 with the unchanged pipeline at commit `c83ecf3`; see `docs/HELDOUT_EVALUATION.md` (protocol, hashes, per-photo results, limits). They are now **used** and must not guide tuning.

## Synthetic test fixtures (category C2; never real-world evidence)
`scripts/make_demo_images.py` renders 7 fixtures from public list values; each carries a red in-frame banner "TEST FIXTURE - SYNTHETIC - NOT A REAL MEDICINE" and is listed in `fixtures_manifest.csv`. `scripts/run_fixture_check.py` runs them through the unchanged pipeline and writes `evaluation/results/fixtures/fixture_run_<timestamp>/` (results, report headed "SYNTHETIC FIXTURES - NOT REAL-WORLD EVIDENCE"), never `evaluation/results/runs/`. `tests/test_demo.py` requires every fixture to give its documented result and the banner to be legible to OCR. A fixture pass rate says the software path works on clean rendered text; it is not an accuracy figure and is never combined with real-photo numbers. Fixtures may be printed and photographed for a live demonstration only with the banner visible.

## What is already verified (not an evaluation)
Unit and integration tests, including synthetic-label runs through real Tesseract and the Streamlit widgets, are described in `docs/TESTING_GUIDELINES.md`.
