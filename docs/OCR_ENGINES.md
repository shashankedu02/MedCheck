# OCR Engines (authoritative for engine choice, installation, licensing and offline operation)

Decision record: D-022 (RapidOCR primary, approved by the owner on the condition of pinning, documentation, offline operation and safety preservation), D-023 (cascade and agreement rules), D-024 (manual entry). Evidence for the choice: `docs/OCR_INVESTIGATION.md`.

## Roles
| Engine | Role | Notes |
|---|---|---|
| **RapidOCR** (`rapidocr-onnxruntime` 1.2.3, ONNX models via `onnxruntime`) | Primary | Text detection plus recognition; reads small stamped print on embossed foil that Tesseract could not (investigation: 16/20 vs 0/20 labelled batch lines on the development photos). |
| **Tesseract** 5.5.3 | Additional evidence and fallback | Runs on the pack region (2 preprocessing variants x 2 page modes). Its readings take part in strict agreement: a disagreeing Tesseract reading makes the batch AMBIGUOUS. If RapidOCR is unavailable, Tesseract alone is used (with a visible note); if both are unavailable the result is a system error, never a status. |

Neither engine's score is evidence of identity. Scores are stored with the words only for display/diagnostics and are never read by extraction, matching or decision code (enforced by a test).

## Installation
```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pip install --no-deps -r requirements-ocr.txt
```
(D-034: `requirements.txt` now also carries these pins for Streamlit Community Cloud, with the same OpenCV version under the name `opencv-python`; see `docs/DEPLOYMENT.md`.) `--no-deps` is deliberate: `rapidocr-onnxruntime` declares `opencv-python`, which would install a second `cv2` build next to the project's `opencv-python-headless` (same 5.0.0.93 module). `pip check` therefore lists that one declared requirement as missing; this is expected. All real dependencies are pinned in `requirements-ocr.txt`. Without these packages the app still runs on Tesseract alone and says so.

## Size
`rapidocr_onnxruntime` 14 MB (including 13.7 MB of models), `onnxruntime` 54 MB, `shapely` 3.4 MB, plus small packages: about 72 MB added. `opencv` is already part of the project.

## Offline operation and model integrity
- The three model files ship **inside the pip wheel**; nothing is downloaded at run time. A test runs the real engine with `socket.connect` and name resolution disabled.
- Before every load, the SHA-256 of each model file is checked against `config.RAPIDOCR_MODEL_SHA256`: `ch_PP-OCRv3_det_infer.onnx` (3439588c...e526), `ch_PP-OCRv3_rec_infer.onnx` (897a3ede...e615), `ch_ppocr_mobile_v2.0_cls_infer.onnx` (e47acedf...215c). A missing or altered model makes RapidOCR unavailable (fail closed, tested) and the pipeline falls back to Tesseract with a note. Update the pins only together with a deliberate version change and a re-run of the evaluation.
- Images stay in memory; recognised text is not logged; adapter errors are generic (no engine text echoed).

## Licensing (verified from installed package metadata)
| Component | Licence |
|---|---|
| rapidocr-onnxruntime 1.2.3 (wrapper and bundled PaddleOCR-derived PP-OCRv3 / mobile cls models) | Apache-2.0 |
| onnxruntime 1.32.0 | MIT |
| pyclipper 1.4.0 | MIT |
| shapely 2.2.0 | BSD-3-Clause (bundles GEOS, LGPL-2.1, as a separately shipped library) |
| flatbuffers 25.12.19 | Apache-2.0 |
| PyYAML 6.0.3, six 1.17.0 | MIT |
| Tesseract 5.5.3 | Apache-2.0 |
Compatible with local, non-commercial and commercial use; redistribution requires keeping the licence notices. This is an engineering note, not legal advice.

## Known limits
- The recognition model is a general Chinese/English PP-OCRv3 model; accuracy on other scripts and print styles is unmeasured.
- Cost on the development machine (measured, `docs/V2_REVIEW.md` section 4): about 2 s per RapidOCR pass (the first call on new image content is about 2.8 times slower than a repeat call), Tesseract about 1 s per pass and run concurrently; typically 2.6-9.8 s per photo when a batch label is found, up to about 20 s when nothing is found and all three rotations run. ONNX threads are bounded to 4 (`config.RAPIDOCR_INTRA_OP_THREADS`) because the engine's default thread pool was up to 20 times slower and erratic under normal desktop load; wall-clock times vary with background load. The engine is warmed once when the app starts. Time budget: `config.OCR_TOTAL_BUDGET_SECONDS`.
- Engines produce confident wrong characters (for example `HLAS50019` for `HLAS0019`). Safety rests on strict agreement, near-neighbour abstention and, for every clean negative, the user's confirmation of the printed batch (D-026), not on the engine. Reproduced case: both RapidOCR views read `HLA50019` on a loosely cropped T003; the result is now `Unable to verify` until the batch is compared with the pack. See `docs/MATCHING.md`.
