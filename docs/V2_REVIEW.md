# V2 Manual-Testing Review (diagnosis, experiments, changes)

Status: written during the review of commit `a735acb`. Evidence scripts: `experiments/v2_review/` (outputs git-ignored). Scope rules kept: the 7 held-out photographs were never opened or processed; the dataset, its hashes, historical runs, thresholds, matching rules and the disabled `Expired` status are untouched; everything runs locally and offline. No accuracy is claimed: the references are visual readings by an AI model, not physical-pack ground truth (`evaluation/reference_batches.csv`, tiers `certain` / `probable`). `HLAS0019` is recorded there as `certain` only in the sense of "clearly legible in the photo"; it is **not** physical-pack verification.

## 1. Review of the browser-test observations
| Observation | Finding |
|---|---|
| A. `ImportError: cannot import name 'BatchSource'` | Transient, reproducible, **not a code defect** (section 2). |
| B-C. Photo accepted, tight crop rejected (300 px minimum), loose crop noisy | Matches the investigation: the minimum applies to the whole upload; the engine reads the loose crop but the batch line is small. Crop-and-resize in the app is not needed because the pipeline already crops the pack automatically (section 8). |
| D. Readings `HLA50019MG.JUL.2025` (full) and `HLA50019` (crop), 6 passes, 34.8 s | Two separate causes: the engine dropped the `F` of `MFG` (so the date stayed inside the batch), and S was read as 5. Strict agreement correctly returned `Unable to verify`. Time: section 4. |
| E. Expiry read, manufacturing date missing | Same dropped-`F` cause (section 5). |
| F. Manual entry of `HLAS0019` | Worked as designed; reviewed (section 7), one real shortcoming fixed. |

## 2. Startup import error
Reproduced exactly with `experiments/v2_review/repro_import_error.py`: a Python process that has imported the OLD package (`ea045e7`), then has the files replaced by the NEW version (`HEAD`), and re-runs the app script, raises `cannot import name 'BatchSource' from 'medcheck.models'`. A fresh process with the same new files runs cleanly. This is the situation of a long-running Streamlit server holding old modules in memory while the code is updated. (Two servers from `.venv` were running during the review.) Fix: restart the server. Change: `app.py` now shows an explicit restart instruction instead of a traceback when its imports are stale (tested by deleting `BatchSource` from the loaded module).

## 3. Exact batch extraction (Priority 1)
- **Is strict agreement too restrictive?** Replaying the recorded readings of the final dev run under alternative policies (`exp_agreement_policies.py`, 7 certain + 4 probable references):

| Policy | Exact | **Wrong accepted** | Abstained |
|---|---|---|---|
| strict (current) | 3 | **0** | 4 |
| accept a lone reading | 4 | 0 | 3 |
| plurality vote | 4 | **3** | 0 |
| prefer the crop view | 5 | **2** | 0 |
| look-alikes count as agreeing | 3 | 0 (1 wrong on a probable reference) | 4 |

Every looser policy that increases coverage accepts wrong batches (`HLAS50019`, `INA26083`, `5BA13A7`, `18261604K8` ...). A wrong accepted batch can become a false `No alert found`. The current rule is **the most conservative of those tested**; it is unchanged. (Correction, see the addendum: strict agreement cannot catch both engines making the *same* wrong reading; I overstated its protection here.) (7 scored photos: a replay of recorded readings, not an accuracy estimate. "Accept a lone reading" gained T010 here, but lone readings were wrong in earlier runs, so it was not adopted.)
- **S/5, O/0, I/1.** Nothing is ever substituted. New: when conflicting readings differ **only** by look-alike characters, the explanation now says which characters (for `HLAS0019` vs `HLA50019`: "differ only by look-alike characters (5 or S); check exactly these characters on the pack"), and both raw readings stay visible. The outcome is still `Unable to verify`.
- **Batch joined to MFG/EXP.** Fixed at the parser (section 5).
- **Different readings between full frame and crop.** Expected and useful: the second view exposed the misreads in T003, T011 and T026 that a single view would have accepted.
- **Field-specific re-read (tested, not adopted).** Cropping only the batch line and re-reading it (`exp_line_reread.py`): T003 became exact at every scale, but T010 and T013 gained look-alike misreads (`BEC110O6`, `2553GCA146`) next to the correct value, T011 got worse, T004/T026 found no label line. Under strict agreement it would resolve one conflict and create two, with no demonstrated safety gain.

## 4. Processing time (Priority 2)
Measured with `time_breakdown.py`, `exp_threads.py`, `exp_shape_cost.py`, `exp_tess_threads.py`, `exp_concurrency_ab.py`.
- **Model initialisation was included in the reported time.** Cold: first check 10.0 s, second 6.1 s, so about 3.9 s of one-off start-up (ONNX session creation; the model hash check is 0.02 s). The app now warms the engine once when it starts, so no user check pays it.
- **Where the time goes** (20 dev photos, before the changes): RapidOCR 64%, Tesseract 36%, region detection + preprocessing + image loading + extraction + matching under 1%. A RapidOCR pass averages 2.1 s; the first call on new image content costs about 2.8 times a repeat call (3.1 s vs 1.1 s), a first-touch cost inside the engine that cannot be removed from outside.
- **Why the times were erratic (7 s to 88 s, and your 34.8 s):** the engine's default ONNX thread pool is unstable on this 16-thread hybrid CPU under ordinary desktop load. The same pass on the same frame took **10.9 s with the default and 0.5 s with 4 threads, with identical recognised text**. Threads are now bounded (`config.RAPIDOCR_INTRA_OP_THREADS = 4`, switchable). This removed the extreme outliers (worst photo 88 s -> 11.6 s) but **did not change the typical time** (mean 13.6 s vs 14.0 s on a quiet machine). Tesseract's thread count made no difference (1.0 s per pass at every setting), so it is untouched.
- **Redundant passes.** Tesseract contributed no batch reading on any dev photo in any run, but it is the fallback when RapidOCR is unavailable and a possible veto on a clean read; removing or skipping it in the clean-read case would drop that veto exactly where definitive results come from, so it stays. Instead it now runs **concurrently** with RapidOCR (same passes, same evidence). Controlled A/B, interleaved so load affected every mode equally, 8 photos x 3 rounds: sequential 52.8 s, concurrent **38.9 s (-26%)**, concurrent with Tesseract limited to 2 OpenMP threads 38.9 s (no extra gain); the decision, batch state and batch string were identical in all 72 runs; every photo was faster.
- **Rotation cascade.** It runs only when no batch label was found anywhere (verified by tests). Order 90, 180, 270 matches where readings came from (rot90: T002, T004, T007, T016, T019; rot180: T016; rot270: T002, T023). **Stopping early was rejected on evidence:** in T002 the conflict between `5707486` (rot90) and `51P07486` (rot270) is visible only because the later rotation also ran; early stop would hide it. Photos with no readable batch pay for all three rotations (about 10 s extra).
- **One dev run was slower** (mean 21.1 s, maximum 63.4 s, decisions identical) than the one before (14.0 s / 23.2 s). It was run under background load; the later interleaved A/B shows the opposite effect of the change. I could not identify which other process caused it, so wall-clock numbers from single runs on this machine vary with load; compare only interleaved or repeated measurements.
- **Typical time now** (A/B photos, concurrent): 2.6 to 9.8 s per photo when a batch label is found; up to about 20 s when nothing is found and all rotations run.
- **Not adopted / not tested:** skipping Tesseract on a clean RapidOCR read (weakens the veto); fewer rotations (loses readings); smaller input images (changes what the engine can read; untested); fixed canonical input shapes to reduce first-touch cost (untested, would need its own accuracy check).

## 5. Manufacturing / expiry extraction (Priority 3)
Root cause for the browser test: the engine read `MFG.JUL.2025` as `MG.JUL.2025`; the label was not recognised (no manufacturing date) and the batch parser had no label to stop at (the date stayed in the batch). Fixes in `extraction.py`, all narrow and tested, dates remain display-only (expiry verdicts stay disabled):
- `MG` counts as a dropped-`F` label **only** when a month and a 4-digit year follow it with no whitespace (`MG.JUL.2025`); `500 MG JAN 2025`, `500 MG. JUL.2025` and similar are not dates. (One contrived form, `500 MG.JUL.2025`, is accepted; dates are display-only.)
- A month glued to the batch is cut off it (`XYZ123JUL.2025` -> `XYZ123`); a batch that merely starts like a month (`DEC1234`, `JAN2501`) is kept.
- Month name + 2-digit year without a separator (`JUN25`, `MAY 27`) and glued labels (`MfgDt:04/2026Exp.Dt.:03/2029`) are read. Month names must be real month names.
- Dev run before/after the changes: manufacturing dates read 7 -> 8, expiry dates read 7 -> 8; no batch result or outcome changed. Dates were not scored (no date reference).
- Why dates behaved differently from batches: labels were matched with rigid word boundaries and a rigid year form, and the engine's most common error (dropping or gluing characters) breaks exactly those.

## 6. Crop and region detection (Priority 4)
`exp_crop_assessment.py` on the 20 dev photos: a pack region was found in 20/20 (median 36% of the frame); of 110 label lines (`B.No`, `MFG`, `EXP`) located by full-frame OCR at four rotations, **109 lie inside the region**; no label line touches the crop edge (so the edge guard costs nothing on crops). The one failure is T025 (busy chocolate-shelf background), where the detector selected a lower-left area. Per view, the crop did not add a photo the full frame could not read at rotation 0, and it missed T010 that the full frame read; its value is as a **second, independent-scale reading that exposes disagreement**, and it makes the rotation retries cheaper. Keep full frame + crop. Not changed. Open: a second candidate region for busy backgrounds.

## 7. Manual entry (Priority 5)
Reviewed against the code and tests: source labels, same matching, confirmation for clean negatives (typed/corrected batches at the time; extended to OCR-read batches by D-026), validation, no logging all behave as specified. One genuine shortcoming fixed: the confirmation checkbox stayed ticked after the number was edited, so a different number could be confirmed without a fresh look. Editing the number now clears the tick (tested). Nothing else was redesigned.

## 8. Limits that remain
Photo quality (glare, embossing hiding a character, batch on the other face) is not fixable in software; guidance and manual entry are the remedies. T008's `25S3GTA4` may be incomplete (an embossed dimple may hide a character): check it on the pack.

## Addendum 2026-11-15: a consistent look-alike misread (D-026)
**Report.** A loosely cropped T003 was read as `HLA50019` (true `HLAS0019`), shown as "read consistently", and gave `No alert found`.
**Reproduced** with the reporter's file, read-only (`experiments/v2_review/repro_user_crop.py`): both RapidOCR views returned `HLA50019` on every run, strict agreement accepted it, the batch is nowhere near a listed batch (nearest listed `V250519`, 4 to 5 edits away), so the matcher returned no match.
**Root cause.** The look-alike safeguards are relative to the dataset (a look-alike or near-neighbour of a *listed* batch abstains) or to disagreement between readings. Neither can see two engines agreeing on the same wrong character when no listed batch is nearby, and automatic S/5 substitution is forbidden. The outcome happened to be the same as for the correct string (`HLAS0019` is not listed either), so no listed batch was missed, but the app showed a wrong batch string as "read consistently" and offered a clean negative.
**What was wrong in my own review.** I described strict agreement as "correctly conservative" without stating this limit, and the interface said "read consistently". Both overstated what two agreeing passes prove. The code matched its tests; the claim went beyond them.
**Fix (D-026, owner-approved).** No clean negative for any batch string until the user compares it with the pack and confirms; `Unable to verify` until then; `Alert found` never delayed; the label now reads "agreed by the OCR passes - not yet checked against the pack"; confirmation is explained as checking the printed number only. Re-run with the same file: `Unable to verify [ocr_batch_unconfirmed]`; correcting to `HLAS0019` and confirming gives `No alert found` (labelled user-corrected); ticking `HLA50019` without looking is recorded as the user's confirmation (no software can prevent that).
**Evaluation effect.** Clean negatives in evaluation runs are now `Unable to verify` / `ocr_batch_unconfirmed`, scored Inconclusive against a `No alert found` label.
