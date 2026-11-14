# Implementation Blueprint

## Build order
1. Repository and environment inspection.
2. Dataset loader and integrity checks.
3. Pure normalization functions.
4. Exact batch candidate retrieval and collision handling.
5. Decision engine and table-driven tests.
6. OCR field extraction on representative images.
7. Image preprocessing improvements measured against a baseline.
8. Streamlit UI and error handling.
9. End-to-end evaluation on a fixed, labelled image set.

## Proposed data models
- `OCRCandidate`: raw text, field type, OCR pass identifier, confidence as returned by OCR, optional bounding box.
- `ExtractedField`: raw value, normalized comparison value, source candidates, extraction status, ambiguity reason.
- `MedicineScan`: product, batch, expiry, manufacturing date, optional manufacturer.
- `DatasetRecord`: exact source columns, preserving source values.
- `MatchCandidate`: dataset row reference, exact/fuzzy batch evidence, product evidence, collision flag.
- `Decision`: status, primary reason, evidence, snapshot identity, expiry caveat.

These are conceptual contracts, not existing classes.

## Error categories
Distinguish invalid upload, image decode failure, no readable text, field ambiguity, OCR executable missing, OCR timeout, dataset missing, dataset schema mismatch, dataset digest mismatch, matching collision, and unexpected internal error.

## Dependency policy
The previously reported environment includes Python 3.13.5 and Tesseract 5.5.3. Streamlit, Pillow, OpenCV, pytesseract, pandas, RapidFuzz, and pytest are proposed dependencies; exact compatible versions and pins have not been validated here. Verify package compatibility in a clean virtual environment before pinning `requirements.txt`.

## Performance and limits
Do not hardcode upload-size, pixel-count, OCR-timeout, or confidence thresholds from illustrative examples. Measure on representative devices/images, document the hardware and sample, then set conservative limits.
