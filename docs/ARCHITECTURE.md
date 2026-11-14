# Proposed Architecture

## Status
This is a proposed architecture, not a description of inspected source code. The complete application repository was not supplied for source-level review.

## Logical components
1. **UI/input:** Streamlit page, single image upload, preview, clear/retake.
2. **Image validation:** file type, byte/pixel bounds, decode validation, EXIF orientation.
3. **Preprocessing:** grayscale, contrast enhancement, denoising, threshold variants, conditional deskew.
4. **OCR adapter:** local Tesseract through pytesseract; bounded attempts and explicit executable availability check.
5. **Field extraction:** labelled batch/EXP/MFG/product/manufacturer candidates, preserving source spans and OCR pass.
6. **Normalization:** separate pure functions for batch, product identity, manufacturer, and dates.
7. **Dataset repository:** load and validate the frozen CSV and manifest once per process/session as appropriate.
8. **Candidate matcher:** exact matching and fuzzy candidate retrieval; collision detection.
9. **Decision engine:** deterministic decision matrix with explicit abstention reasons.
10. **Result presenter:** status, extracted raw fields, matched source row, snapshot date, limitations, and next safe action.

## Proposed module boundaries
`app.py`, `medcheck/image_input.py`, `medcheck/preprocessing.py`, `medcheck/ocr.py`, `medcheck/extraction.py`, `medcheck/normalization.py`, `medcheck/dataset.py`, `medcheck/matching.py`, `medcheck/decision.py`, `medcheck/models.py`, `medcheck/config.py`, `tests/`.

These are suggested paths only. Inspect the actual repository before creating or editing them.

## Data flow
Image bytes → validation → preprocessing variants → OCR outputs → candidate fields with provenance → conservative normalization → dataset candidate retrieval → identity corroboration → decision matrix → evidence-rich UI.

## Design constraints
- Pure, deterministic logic for normalization/matching/decision.
- UI must not contain matching rules.
- Dataset load failures must be explicit.
- Avoid persisting uploaded images.
- No remote OCR/API dependency in the initial local prototype.
