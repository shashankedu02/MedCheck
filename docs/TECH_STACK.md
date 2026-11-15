# Technology Stack (as built)

| Layer | Choice | Notes |
|---|---|---|
| UI | Streamlit 1.67.0 | `app.py`; `.streamlit/config.toml` binds to localhost, disables telemetry, caps uploads at 10 MB |
| 3D interface | Three.js 0.170.0 (MIT), vendored in `static/vendor/three/` (no npm, no CDN); Streamlit Components V2 (`st.components.v2`) | decorative five-scene story (D-030) in `medcheck_ui/assets/`, mounted by `medcheck_ui/scene.py`; the page receives only a phase and a status name; integrity-verified download, hash and licence in `VENDOR.json`; served locally by Streamlit static serving; see `docs/UI_UX_GUIDELINES.md` |
| Result screen | `medcheck_ui/result.py` (HTML/CSS through `st.html`, every dynamic value escaped) and native Streamlit widgets for the batch form | presentation only (D-031, D-032); basic native rendering is the fallback |
| Language | Python 3.13.5 | tested on Windows 11 |
| Image I/O | Pillow 13.0.0 | decode, format by content, EXIF orientation, pixel limits |
| Image processing | opencv-python-headless 5.0.0.93, numpy 2.5.4 | grayscale, CLAHE, Otsu, adaptive threshold |
| OCR engine (primary) | RapidOCR 1.2.3 + onnxruntime 1.32.0 (`requirements-ocr.txt`, installed with `--no-deps`) | models ship in the wheel; offline; hash-verified; see `docs/OCR_ENGINES.md` |
| OCR engine (extra evidence / fallback) | Tesseract 5.5.3 (native executable, `eng` + `osd` data) | called directly with the image on stdin; found via `MEDCHECK_TESSERACT_CMD`, PATH, then the default Windows path |
| Similarity | RapidFuzz 3.14.6 | edit distance for near-batch retrieval, token/brand similarity; never confirms an alert |
| Tests | pytest 9.2.0 (listed in `requirements.txt` with the runtime packages) | 443 tests; Streamlit `AppTest` for the UI. No coverage tool, browser-automation tool or linter is installed (`docs/ARCHITECTURE.md` section 9) |

Pinned in `requirements.txt` and `requirements-ocr.txt` (the versions verified together). Tesseract is installed separately and is not a pip package.

## Deviations from the original plan
- `pytesseract` is not used: it writes every image to a temp file. Calling `tesseract` with stdin keeps images in memory (privacy rule).
- `pandas` is not used: the standard `csv` module keeps every value an exact string; it was removed from requirements as an unnecessary dependency.

## Not in the stack (by design)
Cloud OCR, accounts, payments, analytics/telemetry, databases, barcode/QR scanning.
