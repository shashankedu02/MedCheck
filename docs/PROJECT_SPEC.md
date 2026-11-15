# Project Specification

## Purpose
Build a local-first demonstrator that reads medicine-packaging text from a user-supplied photograph and checks the extracted batch identity against a curated CDSCO August 2026 NSQ dataset.

## In-scope flow
1. Accept one medicine package/strip image.
2. Validate the image in memory and detect the pack region.
3. Run local OCR: RapidOCR (primary) on the full frame and the pack region, with Tesseract as additional evidence and as the fallback; rotation and confirmation passes only under the rules in `docs/ARCHITECTURE.md` section 3.1 (engines: `docs/OCR_ENGINES.md`).
4. Extract the batch number, expiry date and manufacturing date from labelled lines; a batch is read only when the OCR passes agree (strict agreement). Product identity and the optional manufacturer come from the photo's text and only corroborate.
5. Preserve raw OCR evidence and create separate normalized comparison values.
6. Compare the batch against the validated August 2026 CSV.
7. Return one of four user-facing outcomes with evidence and limitations. The user may select one of the OCR's batch readings, correct it or type it; such a value is labelled as the user's, never counts as OCR evidence and is checked by the same rules.

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
The evaluation plan is **undecided (D-014 OPEN, pending further evaluation planning)**. The original proposal was 60 images (30 alert-listed, 30 non-alert). An engineering assessment judged that physical NSQ-listed packs probably cannot be obtained, and a revision is proposed that keeps evidence in separate categories never merged into one percentage (real photographs of ordinary packs, synthetic test fixtures, programmatic tests, verified real positives if any, a human-confirmation study); `docs/EVALUATION.md` lays out both proposals side by side. Neither is approved or executed, and no formal study has been performed. No accuracy, precision, recall, F1, time-saving, or other performance claim may be presented until a recorded evaluation produces it, and a fixture pass rate is never an accuracy figure.
