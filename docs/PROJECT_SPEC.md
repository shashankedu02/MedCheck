# Project Specification

## Purpose
Build a local-first demonstrator that reads medicine-packaging text from a user-supplied photograph and checks the extracted batch identity against a curated CDSCO August 2026 NSQ dataset.

## In-scope flow
1. Accept one medicine package/strip image.
2. Validate and preprocess the image.
3. Run local Tesseract OCR.
4. Extract product identity, batch number, expiry date, manufacturing date, and optional manufacturer where legible.
5. Preserve raw OCR evidence and create separate normalized comparison values.
6. Compare candidates against the validated August 2026 CSV.
7. Return one of four user-facing outcomes with evidence and limitations.

## Required statuses
- `Alert found`: the batch read from the photo matches exactly one row of the dataset (every row is an NSQ entry by construction of the CDSCO list) and corroborating product identity is present (`docs/MATCHING.md`).
- `No alert found`: a sufficiently readable, non-ambiguous batch was checked successfully, no qualifying row matched in the configured snapshot, **and the user confirmed that the batch string matches the one printed on the pack (D-026)**. Until then the result is `Unable to verify`. Confirming means the user checked the printed batch number; it does not show the medicine is genuine or safe.
- `Expired`: expiry has been reliably interpreted as expired under an owner-approved policy, and no confirmed NSQ alert takes precedence.
- `Unable to verify`: OCR, identity, dataset integrity, or policy evidence is insufficient or conflicting.

These statuses are not interchangeable with a medicine safety assessment.

## Out of scope
Counterfeit detection, authenticity certification, chemical/laboratory testing, diagnosis, treatment recommendations, dosage advice, prescribing, barcode/QR verification, user accounts, payment, cloud OCR, persistent scan history, and regulatory-site scraping.

## Safety language
Never call a product “safe,” “genuine,” “authentic,” or “free from defects.” Explain that the check covers only the supplied August 2026 snapshot. For uncertainty, direct the user to a pharmacist or qualified healthcare professional; do not advise starting or stopping medication.

## Evidence and provenance
The dataset is 220 records and 10 columns, extracted from the official CDSCO portal (`docs/DATASET.md`). It is a monthly snapshot extraction, not a regulatory certification or a complete regulatory record.

## Evaluation
Physical NSQ-listed packs cannot be obtained, so evidence is kept in separate categories that are never merged into one percentage: real photographs of ordinary packs, synthetic test fixtures, programmatic tests, verified real positives if any, and a human-confirmation study (`docs/EVALUATION.md`, `docs/EVALUATION_STRATEGY.md`). The formal study (D-014) has not been performed. No accuracy, precision, recall, F1, time-saving, or other performance claim may be presented until a recorded evaluation produces it, and a fixture pass rate is never an accuracy figure.
