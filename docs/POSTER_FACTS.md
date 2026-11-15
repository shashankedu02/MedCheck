# MedCheck: Verified Facts for the Poster and Demonstration

Every statement below comes from the code, the official dataset or a recorded run in this repository, and the source is named. Nothing here is an accuracy figure; MedCheck's real-world accuracy has **not** been evaluated (D-014 open). Keep the qualifiers when you copy text onto the poster.

## 1. Problem
- CDSCO publishes monthly lists of drug batches found **Not of Standard Quality (NSQ)** by government laboratories. Checking a pack in hand against such a list means finding the small batch number on a strip or carton and looking it up by hand.
- The August 2026 list used here has **220 records** (191 reported by State labs, 29 by CDSCO labs), each with product, batch, dates, manufacturer and the failed test (`docs/DATASET.md`).
- Batch numbers are short, mixed-character strings (`PAK-637`, `BKBP02601`, `0l25038`), printed in small dot-matrix or inkjet type on foil or card. Look-alike characters (O/0, I/1, S/5, B/8) make both manual and automatic reading error-prone.

## 2. Solution
A local, offline photo-lookup aid. The user photographs the batch area of a medicine pack. MedCheck reads the batch number, expiry and manufacturing dates with on-device OCR and checks the batch against the official August 2026 CDSCO NSQ list. It reports one of four outcomes:
- **Alert found**: an exact listed batch, corroborated by the product on the pack, with the official record shown and a "check before acting" prompt.
- **No alert found**: only after the user has compared the batch with the pack and confirmed it; it covers this one list only.
- **Unable to verify**: the deliberate safe default whenever the evidence is unclear.
- **Expired**: reserved and switched off until an expiry policy is approved.

It is a lookup aid. It is **not** an authenticity, counterfeit, quality or safety test and gives no medical advice.

## 3. System architecture (as built, `docs/ARCHITECTURE.md`)
```
Photo (in memory only)
  -> image validation (size, format, pixel limits)
  -> pack-region detection (crop is an extra view)
  -> OCR cascade: RapidOCR (full frame + pack crop) || Tesseract (crop) in parallel
       [rotations 90/180/270 only if no batch label was found]
       [one confirmation pass at another scale if only one pass read the batch]
  -> field extraction (label-anchored batch / Exp / Mfg; glued labels cut; strict agreement across passes)
  -> batch matching against the hash-verified NSQ dataset (exact key, look-alike collision check,
     near-neighbour abstention, product corroboration)
  -> decision engine (4 outcomes + separate system errors)
  -> Streamlit UI (review / correct / confirm the batch; provenance shown)
```

## 4. Technologies (pinned, `requirements.txt`, `requirements-ocr.txt`, `BUILD_PROGRESS.md`)
Python 3.13 · Streamlit 1.67 (localhost only, telemetry off) · RapidOCR 1.2.3 on ONNX Runtime 1.32 (PP-OCRv3 detection and recognition models, bundled, SHA-256 verified before loading) · Tesseract 5.5.3 (extra evidence and fallback) · OpenCV 5.0 (headless) · Pillow · NumPy · RapidFuzz (candidate retrieval only) · pytest.
Everything runs offline on a laptop. There are no network calls, no cloud OCR and no telemetry, and no image or OCR text is stored or logged.

## 5. OCR and image-processing workflow
- Upload is validated in memory: JPEG/PNG/WebP, 10 MB cap, decompression-bomb guard, EXIF orientation.
- Pack-region detection by print-texture energy. Two RapidOCR views run (full frame and pack crop), with Tesseract on the crop in a worker thread at the same time.
- Rotated views are tried only when no batch label is found. One extra confirmation pass is allowed when a single pass read the batch, never a retry until readings agree.
- Fields are taken only after a label (`B.No.`, `Batch`, `Lot`, `Mfg`, `Exp`, ...). The parser cuts labels glued on by OCR (`5BA1617MFD` -> `5BA1617`) and rejects text that cannot be a batch (characters never seen in a listed batch, long letter runs, lines touching the image edge).
- **Strict agreement:** every pass that reports a batch must agree, and at least two must support it; otherwise the batch is "uncertain".
- **Typical time on the development PC:** about 5-11 s per photo, longer (up to about 20 s) when no batch label is found. This is measured on one machine, not a benchmark.

## 6. Batch matching methodology (`docs/MATCHING.md`)
- **Comparison key:** Unicode-normalised, uppercase, letters and digits only. Raw strings are always preserved, and look-alike characters are **never** substituted.
- **Alert** only for a **unique exact** listed batch **plus** product corroboration from the photo: the brand, or all active-ingredient words, with no strength or form conflict. Short batches (under 6 characters) need two independent signals.
- **Collision:** if another listed batch differs only by look-alike characters (serials 38 `BKBP02601` and 157 `BKBP O2601`), the result is "Unable to verify".
- **Near-neighbour abstention:** a reading within 2 edits of a listed batch (6+ characters) is never treated as a clean negative.
- **Product name alone never alerts; a batch alone never alerts.**

## 7. Safety and abstention mechanisms
1. **Four outcomes only; system failures are separate.** A dataset integrity failure, a missing OCR engine or a timeout is never shown as "No alert found".
2. **Fail-closed dataset.** The official extraction is immutable and hash-pinned; the app's dataset is regenerated and hash-checked at every start.
3. **Confirmation before any clean negative (D-026).**
   - Two OCR engines can agree on the same wrong character. In a real test photo, `HLA50019` was read for the printed `HLAS0019`.
   - So "No alert found" appears only after the user compares the batch with the pack and ticks a confirmation.
   - Confirmation means the printed number was checked, not that the medicine is genuine or safe.
   - Editing the number clears the tick.
4. **Alert-side check (D-027).**
   - Every alert shows "Check before acting": compare the printed batch character by character, and the product, strength and manufacturer, with the listed record.
   - When another listed batch is within 2 characters, the alert names it.
   - Listed batches often come in sequences (22 listed pairs are within 2 edits).
   - Alerts are never delayed.
5. **Provenance.**
   - Every batch is labelled OCR-read, user-corrected or user-typed, and the decision records which one was used.
   - A typed batch never counts as OCR evidence.
6. **Wording rules.**
   - The app never says safe, genuine or authentic, and always states that only the August 2026 list was checked.
   - An automated test checks every decision text and the rendered page.
7. **Privacy.** Localhost only, in-memory processing, no image or text persistence, no telemetry.

## 8. Evaluation methodology and actual results
Evidence is kept in **separate categories and never merged into one percentage** (`docs/EVALUATION.md`).

| Category | What was done | Actual result | What it shows / does not show |
|---|---|---|---|
| Programmatic tests | Full automated suite (`pytest -q`), including all 220 listed records | **All tests passing** (count in `BUILD_PROGRESS.md`, "Test results"); with ideal text, 218 of 220 records alert and 38/157 abstain as designed | Rules behave as specified; says nothing about OCR on real photos |
| Synthetic test fixtures | 7 rendered fixtures with a "TEST FIXTURE" banner, run through the real OCR (`scripts/run_fixture_check.py`) | **7 of 7** gave their documented result, including `Alert found` for listed serials 4, 150 and 113 | The whole software path works on clean, known inputs; **not** accuracy; not real packs |
| Real photos, development set | 20 photos of ordinary (non-listed) packs, used during development (run `run_20261115_013421`) | Batch read 5 / uncertain 9 / not found 6. Against 7 reference readings: 3 exact, **0 wrong accepted**, 4 abstained. No clean negative without confirmation | Diagnostic only: photos were used for tuning; references are AI visual readings not yet checked on the packs |
| Real photos, reserved set | 7 photos set aside from tuning until the design was frozen, then run once by V2 (`docs/HELDOUT_EVALUATION.md`); they had been OCR'd earlier by the Tesseract-only baseline, so this is not an independent held-out test | Batch read 2 / uncertain 5. Against 4 reference readings: 1 exact, **0 wrong accepted**, 3 abstained. One consistent wrong reading (`UBO20` for `UB02051`) was withheld by the confirmation step. Dates read: expiry 5/7, manufacturing 3/7, none wrong | Too small for any rate; one photo shared a pack with the development set; references not physically verified; no listed pack |
| Earlier baseline (Tesseract only) | 27 photos (`BUILD_PROGRESS.md`, M7) | 25 not found, 2 uncertain | Why the OCR engine was changed to RapidOCR |
| Human factors | Owner's 4 browser tests of the correction and confirmation flow (`docs/EVALUATION.md`) | All behaved as designed | Workflow only; not a user study |

**Honest one-line summary for the poster:** in every recorded run, MedCheck never accepted a wrong batch against the available reference readings, and it showed no clean negative without the user's confirmation. It abstains often on real photos, and its real-world accuracy has not yet been measured.

## 9. Limitations (state them on the poster)
- **No accuracy figure exists.**
  - No photograph of a real NSQ-listed pack has been tested; such packs are assumed to be withdrawn and unobtainable (not verified with the owner).
  - `Alert found` has been exercised only on synthetic fixtures and programmatic tests.
- **Narrow scope.** One monthly list (August 2026) only; it does not cover other months, other regulators or spurious drugs.
- **Frequent abstention on real photos.**
  - It abstains on blur, glare, foil, embossing and dark ink on gold.
  - It needs a visible `B.No.`/`Batch`/`Lot` label.
  - One image per check, English only.
- **Possible false alert.** A one-character misread of an unlisted neighbouring batch could alert. The product check does not compare the manufacturer and uses all text in the photo; the alert-side check asks the user to verify.
- **Depends on the user's check.** The user's comparison is the last line of defence for misreads, and how reliably users do it has not been measured.
- **Unreadable batches.** Two listed batches have only 2 characters and are never read.
- **Uncalibrated thresholds.** They are engineering defaults.
- **Expiry verdicts are disabled.** The month-only expiry interpretation has not been approved.

## 10. Future scope
- A formal evaluation on fresh ordinary packs, labelled from the physical pack by two people, with dev/test split by pack.
- A user study of the confirmation step.
- Physical test fixtures photographed under real conditions.
- Monthly list updates.
- Region-restricted product evidence and a conflicting-manufacturer rule, only after evidence supports them.
- An expiry verdict once a policy is approved, with date agreement and confirmation.
- Multi-face capture, and support for more languages.

## Wording guide
- **Say:** "checks the batch against the August 2026 CDSCO NSQ list"; "test fixture"; "abstains when unsure"; "no accuracy figure yet".
- **Do not say:** "detects fake / spurious / unsafe medicines"; "X% accurate"; "verified safe"; "real affected medicine" (about a fixture).
- **On every fixture:** a printed fixture keeps its red banner in view.
