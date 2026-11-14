# Architecture (authoritative; reflects code as built)

Status key: **built+tested** means code exists and automated tests were executed. Anything not listed there is not implemented.

## Pipeline
```
bytes -> image_input -> regions (pack crop) -> OCR cascade:
         RapidOCR(full frame) + RapidOCR(pack crop) + Tesseract(crop, 2 variants x 2 PSM)
         [only if no batch label found: RapidOCR(crop rotated 90/180/270)]
         [if exactly one reading has single-pass support: one confirmation pass at another scale]
      -> extraction (glue-aware label-anchored fields, strict cross-pass agreement, provenance)
      -> matching (batch-led, vs. indexed dataset) -> decision -> UI
user-typed batch -> pipeline.verify_manual -> the SAME matching and decision (marked with BatchSource)
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
| `medcheck/ocr.py` | Direct Tesseract call, image via stdin, TSV parsing, time budget; `OCRPass` carries engine/source provenance | built+tested (M4, V2) |
| `medcheck/ocr_rapid.py` | RapidOCR adapter (primary engine): in-memory, offline, model-hash check, generic errors | built+tested (V2) |
| `medcheck/regions.py` | Pack-region detection by foil/print texture energy; crop is an extra view, never a replacement | built+tested (V2) |
| `medcheck/extraction.py` | Batch/Exp/Mfg extraction (glued labels cut, value on next line, label words rejected), strict cross-pass agreement, reading provenance | built+tested (M4, V2) |
| `medcheck/pipeline.py`, `app.py` | Orchestration (cascade, manual verification) and Streamlit UI (review/correct/enter batch) | built+tested (M5, V2) |
| `medcheck/real_eval.py`, `scripts/run_evaluation.py` | Real-photo evaluation records; held-out photos excluded by default; batch scoring against an independent reference | built+tested |

## Deviations from the original plan (and why)
- **pytesseract is not used at runtime.** It writes every image to a temp file. Calling the `tesseract` executable with the image on stdin satisfies the "no persisted images" rule. Only the native engine is required.
- **pandas is not used by the loader.** The csv module preserves exact strings with no dtype coercion; pandas is retained only for evaluation tooling (M6) and may be dropped if unused.
- **Matching and abstention are stricter than a plain fuzzy matcher**: unanimity across OCR passes for the batch, confusable-collision abstention, two-signal rule for short batches.

## Design constraints
Pure deterministic logic for normalization/matching/decision; the UI contains no matching rules; dataset failures are explicit system errors; no network calls; no image or OCR text persisted or logged; thresholds centralised in `config.py`.

## Known limitations
- Extraction is label-anchored and heuristic; packs without a recognisable `Batch`/`B.No.`/`Lot` label are "Unable to verify".
- Batches shorter than 3 characters (serials 24 and 26) are never extracted.
- English only; no deskew/perspective correction yet; OCR accuracy on real photographs has **not** been evaluated (only diagnostic runs on development photos exist; see `docs/OCR_INVESTIGATION.md` and `docs/EVALUATION.md`).
- Two engines reading the same glyph pixels can make the same mistake, so agreement is not independence. Near-neighbour abstention covers errors up to edit distance 2 from a listed batch; a larger misread can still end as `No alert found` (the batch checked is shown so the user can compare it with the pack).
- A reading can be incomplete (truncated batch) and consistent across views; the same display-and-compare mitigation applies.
