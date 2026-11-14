# Technology Stack (as built)

| Layer | Choice | Notes |
|---|---|---|
| UI | Streamlit 1.67.0 | `app.py`; `.streamlit/config.toml` binds to localhost, disables telemetry, caps uploads at 10 MB |
| Language | Python 3.13.5 | tested on Windows 11 |
| Image I/O | Pillow 13.0.0 | decode, format by content, EXIF orientation, pixel limits |
| Image processing | opencv-python-headless 5.0.0.93, numpy 2.5.4 | grayscale, CLAHE, Otsu, adaptive threshold |
| OCR engine | Tesseract 5.5.3 (native executable, `eng` + `osd` data) | called directly with the image on stdin; found via `MEDCHECK_TESSERACT_CMD`, PATH, then the default Windows path |
| Similarity | RapidFuzz 3.14.6 | edit distance for near-batch retrieval, token/brand similarity; never confirms an alert |
| Tests | pytest 9.2.0 | |

Pinned in `requirements.txt` (the versions verified together). Tesseract is installed separately and is not a pip package.

## Deviations from the original plan
- `pytesseract` is not used: it writes every image to a temp file. Calling `tesseract` with stdin keeps images in memory (privacy rule).
- `pandas` is not used: the standard `csv` module keeps every value an exact string; it was removed from requirements as an unnecessary dependency.

## Not in the stack (by design)
Cloud OCR, accounts, payments, analytics/telemetry, databases, barcode/QR scanning.
