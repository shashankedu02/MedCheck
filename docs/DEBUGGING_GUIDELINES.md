# Debugging Guidelines

## Start with evidence
Reproduce the issue with the smallest input. Capture exact command, traceback, app version, Tesseract version and whether the failure is deterministic. Do not upload package images to external services for debugging.

## Common setup checks
```powershell
python --version
git --version
tesseract --version
.\.venv\Scripts\python.exe -c "from medcheck.ocr import find_engine; print(find_engine())"
.\.venv\Scripts\python.exe -c "import cv2, PIL, rapidfuzz, streamlit; print('imports ok')"
```

The primary OCR engine and its model integrity can be checked with:
```powershell
.\.venv\Scripts\python.exe -c "from medcheck.ocr_rapid import RapidEngine; e=RapidEngine(); e.check_available(); print(e.version)"
```
If it raises `OCREngineUnavailable`, the app falls back to Tesseract alone and shows a note (see `docs/OCR_ENGINES.md`). If the page shows "updated while this page was running", stop and restart the server. If the 3D scene misbehaves, start with `MEDCHECK_PLAIN_UI=1` to separate a presentation problem from a pipeline problem (the plain interface uses the same pipeline).

If Tesseract is not found, verify installation and PATH or configure the executable path. MedCheck calls the `tesseract` executable directly (no pytesseract); set `MEDCHECK_TESSERACT_CMD` to its full path if PATH is not configured.

## OCR troubleshooting
- Confirm image opens and correct orientation.
- Inspect original and each preprocessing variant.
- Check OCR page segmentation mode and language data.
- Compare raw OCR tokens and bounding boxes.
- Do not fix a wrong batch by silently replacing similar-looking characters.
- If two variants disagree on a critical identifier, preserve the disagreement and abstain.

## Dataset troubleshooting
Read batch values as strings. Print headers and a small redacted sample; do not dump all product data into logs unnecessarily. Check encoding, exact column spelling and row counts. A load failure must stop matching.

## Reporting a fix
Include root cause, files changed, regression test, exact command/output and remaining limitations. Avoid broad exception catches that hide the real failure.
