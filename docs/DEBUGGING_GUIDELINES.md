# Debugging Guidelines

## Start with evidence
Reproduce the issue with the smallest input. Capture exact command, traceback, app version, Tesseract version and whether the failure is deterministic. Do not upload package images to external services for debugging.

## Common setup checks
```powershell
python --version
git --version
tesseract --version
python -c "import pytesseract; print(pytesseract.get_tesseract_version())"
python -c "import cv2, pandas, streamlit; print('imports ok')"
```

If Tesseract is not found, verify installation and PATH or configure the executable path. Remember `pytesseract` is only a wrapper.

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
