# Architecture (authoritative; reflects code as built)

Status key: **built+tested** means code exists and automated tests were executed. Anything not listed there is not implemented.

## Pipeline
```
bytes -> image_input -> preprocessing (<=4 variants) -> ocr (variants x PSM modes)
      -> extraction (label-anchored fields, cross-pass reconciliation)
      -> matching (batch-led, vs. indexed dataset) -> decision -> UI
dataset (fail-closed loader) feeds matching; system failures bypass to a system-error result.
```

| Module | Role | State |
|---|---|---|
| `medcheck/config.py` | All paths, limits, thresholds (UNCALIBRATED ones labelled), expiry-policy flag | built+tested |
| `medcheck/dataset.py`, `scripts/build_dataset.py` | Canonical dataset build and fail-closed loader | built+tested (M1) |
| `medcheck/normalization.py`, `dates.py` | Comparison keys, month-year parsing, expiry assessment | built+tested (M2) |
| `medcheck/models.py`, `decision.py` | Status/enum contracts, four-status decision engine, system errors | built+tested (M2) |
| `medcheck/product.py`, `matching.py` | Product-name parsing, identity evidence, batch matching and collisions | built+tested (M3) |
| `medcheck/image_input.py` | In-memory validation: size, format by content, pixels, animation, EXIF, downscale | built+tested (M4) |
| `medcheck/preprocessing.py` | Grayscale, CLAHE, Otsu, adaptive threshold; upscale small; invert dark | built+tested (M4) |
| `medcheck/ocr.py` | Direct Tesseract call, image via stdin, TSV parsing, time budget | built+tested (M4) |
| `medcheck/extraction.py` | Batch/Exp/Mfg extraction, strict cross-pass agreement | built+tested (M4) |
| `medcheck/pipeline.py`, `app.py` | Orchestration and Streamlit UI | M5 |

## Deviations from the original plan (and why)
- **pytesseract is not used at runtime.** It writes every image to a temp file. Calling the `tesseract` executable with the image on stdin satisfies the "no persisted images" rule. Only the native engine is required.
- **pandas is not used by the loader.** The csv module preserves exact strings with no dtype coercion; pandas is retained only for evaluation tooling (M6) and may be dropped if unused.
- **Matching and abstention are stricter than a plain fuzzy matcher**: unanimity across OCR passes for the batch, confusable-collision abstention, two-signal rule for short batches.

## Design constraints
Pure deterministic logic for normalization/matching/decision; the UI contains no matching rules; dataset failures are explicit system errors; no network calls; no image or OCR text persisted or logged; thresholds centralised in `config.py`.

## Known limitations
- Extraction is label-anchored and heuristic; packs without a recognisable `Batch`/`B.No.`/`Lot` label are "Unable to verify".
- Batches shorter than 3 characters (serials 24 and 26) are never extracted.
- English only; no deskew/perspective correction yet; OCR accuracy on real photographs has **not** been evaluated.
