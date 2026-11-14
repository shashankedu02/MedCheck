# MedCheck

**Photo-based medicine batch verification using local OCR and conservative matching.**
Upload or capture a photo of a medicine strip or box. MedCheck reads the batch number with Tesseract OCR and checks it against the **CDSCO August 2026 NSQ (Not of Standard Quality) alert list** (220 records). It then reports one of four outcomes:

| Outcome | Meaning |
|---|---|
| **Alert found** | The batch read from the photo matches one NSQ entry **and** the product details corroborate it. The matched record is shown. |
| **No alert found** | A batch was read clearly and no qualifying entry exists in the August 2026 list. This does **not** mean the medicine is safe, genuine or free of defects. |
| **Expired** | Reserved. **Never shown yet**: how month-only expiry dates should be interpreted is an open owner decision (see `docs/EXPIRY_POLICY.md`). |
| **Unable to verify** | The batch could not be read consistently, or the evidence is ambiguous, conflicting or too weak. This is the deliberate safe default. |

Separate from these outcomes, **system errors** (dataset failed its integrity check, OCR engine missing, timeout, internal error) are shown as "System error" and are never reported as "No alert found".

MedCheck is **not** an authenticity or counterfeit detector, a laboratory test, or medical advice. If unsure about a medicine, ask a pharmacist or doctor.

## Requirements
Windows (developed on Windows 11), Python 3.13, and Tesseract OCR 5.x with English data (`tesseract --version` must work, or set `MEDCHECK_TESSERACT_CMD`).

## Setup and run
```powershell
cd D:\MedCheck
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run app.py
```
The app opens at http://localhost:8501 and listens on localhost only. Photos are processed in memory and are not saved, logged or sent anywhere.

## Tests
```powershell
.\.venv\Scripts\python.exe -m pytest -q
```
The latest recorded results are in `BUILD_PROGRESS.md`.

## Demonstration (reproducible)
```powershell
.\.venv\Scripts\python.exe scripts\make_demo_images.py
.\.venv\Scripts\python.exe -m streamlit run app.py
```
Upload the images from `demo_images\` one at a time and press **Check this photo**:

| Image | Expected result | Why |
|---|---|---|
| `1_alert_found.png` | Alert found (serial 4) | listed batch plus matching product |
| `2_alert_found_trailing_comma.png` | Alert found (serial 150) | published batch ends with a comma; punctuation is ignored |
| `3_no_alert_found.png` | No alert found | batch not in the list |
| `4_unable_batch_alone.png` | Unable to verify | listed batch, wrong product: a batch alone never alerts |
| `5_unable_collision.png` | Unable to verify | serials 38 and 157 differ only by 0 vs letter O |
| `6_unable_no_batch.png` | Unable to verify | no batch number present |

These demo images are **synthetic rendered text**, built from public dataset values. They show how the software behaves; they are not evidence of accuracy on real photographs. `tests/test_demo.py` verifies every row above.

## How matching stays cautious
Exact normalized batch is the only route to an alert, and a product brand or all active-ingredient words must corroborate it (short batches need two independent signals). Look-alike characters (O/0, I/1/L, S/5, B/8) are never substituted; if another listed batch differs only by such characters, MedCheck abstains. Near-matches only ever lead to "Unable to verify". Details: `docs/MATCHING.md`.

## Dataset
The immutable official CDSCO extraction (`data/cdsco_august_2026_nsq_official_extraction.csv`) is the source; the app reads a generated canonical file whose SHA-256 is checked on every start. Source anomalies (for example serials 72, 121, 136, 150, 152, 153) are preserved verbatim, not corrected. See `docs/DATASET.md`.

## Known limitations
- **OCR accuracy on real photographs has not been evaluated.** No performance claims are made; the 60-image protocol (`docs/EVALUATION.md`) is not yet run.
- Extraction needs a recognisable label (`B.No.`, `Batch No.`, `Lot`); strict agreement across OCR passes means blurry or glary photos often end as "Unable to verify".
- Batches shorter than 3 characters (serials 24 and 26) are never read; they always end as "Unable to verify".
- English only; no deskew or perspective correction; one image per check; no barcode/QR support.
- Covers only the August 2026 list, not other months, other regulators or the full regulatory record.
- Thresholds in `medcheck/config.py` are uncalibrated engineering defaults.
- Local use only. Public hosting would send photos to a server and needs a separate privacy review (`docs/DEPLOYMENT.md`).

## Project documents
`CLAUDE.md` (instructions and document map), `BUILD_PROGRESS.md` (state of the build), `docs/` (specifications and decisions), `docs/archive/` (superseded history).
