# Reserved-photo evaluation (one-time, 2026-11-15)

**Not an accuracy study.** Seven photographs, a reference read by eye by an AI model, no physical-pack verification, no listed (NSQ) pack among them. It records what the unchanged system did on photos that had not been used during development. Raw per-photo records (with recognised text) are in the git-ignored run folder `evaluation/results/runs/heldout_run_20261115_020638/`; this document is the committed summary.

## Protocol (as executed)
1. Commit verified as `c83ecf3`, working tree clean (`git status` empty) before the run and after it.
2. Photos hashed (SHA-256) before the run: T009, T012, T015, T018, T021, T024, T027.
3. The production pipeline, unchanged (`MedCheckPipeline.check`, engines RapidOCR + Tesseract, dataset SHA-256 `980efb50e79c...`), processed only those seven photos with `scripts/run_heldout_evaluation.py` (byte-identical to the file that was run; it was run from outside the repository so the tree stayed clean). The engine was warmed first, so no photo's time includes model start-up. Its output was written to a file and **not read** until the next step was finished.
4. **Reference batches were read by eye after the run but before its results were viewed**: each full photo, then a zoomed rotate-and-crop (no OCR involved). The reference file `evaluation/reference_batches_heldout.csv` was written first. Tiers: `certain` (4), `probable` (2: T009, T018), `unreadable` (1: T012). Only `certain` is scored.
5. Results were read and scored with the existing evaluation code; nothing was re-run, tuned or changed. No threshold, matching rule, dataset file or integrity check was touched.
6. Photos re-hashed after the run: byte-identical to the "before" hashes **and to the hashes recorded in the original baseline run (2026-11-14 20:09)**. No historical run was modified; this run has its own folder.

| Test | SHA-256 |
|---|---|
| T009 | `dfeff2bc337cf871ca43c30cc850a4f2636238bb2a1f01c4758e0ee5c70707e6` |
| T012 | `5765ae3f288ecc8854f8a98af769831b6b6bff981a832b8161946883e0421626` |
| T015 | `584a92186073a8e4d7fa7c62bbcc3ab3c7f3a9d70e0d80300f200e7bc6676bf9` |
| T018 | `a3f479ffef6f163dc37e375194f8f41f2d4b51ad43544e86811f12a761f29c1b` |
| T021 | `e18257aad722abee0d5c40fe918a5813ad4c66f387af0dc1353e7bc082484527` |
| T024 | `f3f3f942268e8f62b39cc033d1940015091155cc93b59a6c31b22bd22d6db79b` |
| T027 | `115a9ddbd445977397b536d8a8cc2006f141f716ebabbc1eceb1d84b11f57150` |

## Results per photo
| Test | My visual reading (tier) | What the system read (engine passes) | Batch state | Result shown | Time |
|---|---|---|---|---|---|
| T009 | `UB02051` (probable; inverted print, B/8 and O/0 doubtful) | **`UBO20`** (two passes agree: crop rotated 90 and 270) | read | Unable to verify, awaiting confirmation (`ocr_batch_unconfirmed`) | 10.7 s |
| T012 | not reliably readable (reads like `H?NS0027`) | `H50027MEG.` (one pass only) | ambiguous (1 pass, 2 required) | Unable to verify (`batch_ambiguous`) | 4.8 s |
| T015 | `GPD0826002BH` (certain) | `GPD0826002BH` (full frame and crop agree) | read, **exact** | Unable to verify, awaiting confirmation (`ocr_batch_unconfirmed`) | 4.8 s |
| T018 | `GPE0825002BH` (probable; blurred) | `GPE0828002BH.` (full) vs `GPE0825002BH..` (crop) | ambiguous (conflict) | Unable to verify (`batch_ambiguous`) | 6.2 s |
| T021 | `K2600572` (certain) | `K2600572MD.` (crop) vs `K2600572` (crop, other scale) | ambiguous (conflict) | Unable to verify (`batch_ambiguous`) | 7.8 s |
| T024 | `HLAS0019` (certain; **same pack and batch as dev photo T003**) | `HLAS0019MF6` (one pass only) | ambiguous (1 pass, 2 required) | Unable to verify (`batch_ambiguous`) | 8.7 s |
| T027 | `18262495A` (certain; printed ten times on the strip) | `18262495A` (rot 90), `1826245A` and `18262` (rot 180), `18262495A` (rot 270) | ambiguous (conflict) | Unable to verify (`batch_ambiguous`) | 11.3 s |

No photo was rejected and no processing error or system error occurred. No `Alert found` (none of these batches is in the August 2026 list, so the alert path was **not exercised**), and no `No alert found` appeared without confirmation (D-026).

## Counts
- **Readable batch numbers (my visual reading):** 4 certain (T015, T021, T024, T027), 2 probable (T009, T018), 1 not reliably readable (T012).
- **What the system accepted as read:** 2 (T015 exact; T009 a likely wrong, truncated reading). **Ambiguous:** 5. **Not found:** 0.
- **Against the 4 certain references:** exact 1 (T015), **incorrect 0**, abstained 3 (T021, T024, T027). In all three abstentions the correct value was among the readings; the abstention came from a conflicting or glued variant or from a single supporting pass.
- **OCR disagreements:** 3 photos with conflicting readings (T018, T021, T027); 2 with a single supporting pass (T012, T024). **Abstentions on the batch:** 5 of 7. **Clean negatives awaiting a person's confirmation:** 2 of 7. Total `Unable to verify`: 7 of 7.
- **Time (warm engine, this machine):** mean 7.8 s, median 7.8 s, min 4.8 s, max 11.3 s.
- **Dates (compared with my visual reading; display-only, expiry verdicts remain disabled):** expiry read in 5 of 7 (T012 `OCT2028`, T018 `MAR.2027`, T021 `FEB.2028`, T024 `JUN2028`, T027 `05/2029`), all consistent with the visual reading; manufacturing date read in 3 of 7 (T012 `NOV.2025`, T021 `MAR.2026`, T024 `JUL.2025`), all consistent; **no wrong date was read**. Not read: both dates in T009 and T015, manufacturing date in T018, and T027's manufacturing date was withheld because the passes disagreed (`06/2029` vs `06/2026`). The cause for T009 and T015 was not investigated (no tuning allowed); the stored text is truncated.

## Potentially dangerous readings and unexpected behaviour
1. **T009: two passes agreed on a likely wrong, truncated batch (`UBO20` for `UB02051`).** Nothing listed is near it, so without D-026 this would have been a clean `No alert found` for a wrong batch string. Under D-026 it is withheld until the user compares it with the pack. This is the failure class the confirmation policy exists for, now seen on a photo that was not used in development. It also shows that agreement between passes does not prove correctness (the reference is only `probable`, so it is not counted as an incorrect read in the scores).
2. **Glued, misread labels were not cut from the batch** (`MEG.` in T012, `MF6` in T024, `MD.` in T021). Result: abstention (safe), but exact reads were lost in T021 and T024, where the correct value appeared in at least one pass. Observed only; not fixed (no improvements during this evaluation).
3. **T027's ten copies read differently** (`18262495A` twice, `1826245A`, `18262`). The strict rule abstained; a vote would have been right here and wrong for T009, so this does not argue for loosening the rule.
4. **T018's full-frame reading differed from the crop by one character (`8` vs `5`)**; it was caught only because the second view disagreed.
5. No unexpected exceptions, rejections or slowdowns.

## Comparison with the development photos (different datasets: do not merge the numbers)
| | Development: 20 photos, run `run_20261115_013421` (same code) | Reserved: 7 photos, run `heldout_run_20261115_020638` |
|---|---|---|
| Batch read / ambiguous / not found | 5 / 9 / 6 | 2 / 5 / 0 |
| Exact against certain references | 3 of 7 (0 incorrect, 4 abstained) | 1 of 4 (0 incorrect, 3 abstained) |
| Result shown | 20 x Unable to verify (5 awaiting confirmation, 15 abstentions) | 7 x Unable to verify (2 awaiting confirmation, 5 abstentions) |
| Expiry / manufacturing date read | 8 of 20 / 8 of 20 | 5 of 7 / 3 of 7 |
| Time mean / median / min / max | 6.6 / 6.0 / 2.0 / 11.4 s | 7.8 / 7.8 / 4.8 / 11.3 s |
The populations differ: the development set contains photos with no batch on the visible face, cluttered shelf backgrounds and partly cut-off blocks (6 "not found"); every reserved photo shows a batch block. The numbers are therefore **not comparable as rates**, and the sample sizes (7 and 20; 4 and 7 scored) allow no statistical statement.

## What this establishes
- On seven photos the system never accepted a wrong batch among those with a certain reference, never showed `No alert found` without confirmation, produced no errors, and its date readings agreed with the visual readings wherever dates were read.
- The confirmation policy (D-026) met a real consistent misread (T009) on an unseen photo.
- Typical time on this machine was 5 to 11 s.

## What it does not establish
- **No accuracy, sensitivity, false-negative or false-positive figure.** None of the seven packs is on the NSQ list, so alert detection and the corroboration logic were not exercised on real photos.
- **Not independent of development in two cases:** T024 is a second photograph of the pack behind dev photo T003 (the batch `HLAS0019` drove several fixes), and T027 shares manufacturer, print style and batch prefix with dev photo T026. T015 and T018 are two strengths of the same product family. The set was reserved by taking every third photo, not at random.
- **The reference is not ground truth:** an AI model's visual reading of re-encoded photos, not a check against the physical packs or the official records. The owner should confirm the references (and T009, T012, T018 especially).
- Seven photos from one phone, one table and one operator say nothing about other phones, lighting, packs or users.
- The reserved photos are now **used**: they must not guide further tuning. A fresh, labelled set is needed for any future held-out claim. D-014 remains open: `docs/EVALUATION.md` records the original 60-image proposal and a proposed evidence-category revision, neither approved nor executed (wording corrected in the post-M16 documentation baseline).

## Reproducing the records
`scripts/run_heldout_evaluation.py` writes a new run folder each time and never touches earlier runs, but running it again would look at the reserved photos a second time; do not use it for tuning.
