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
- `Alert found`: identity is sufficiently confirmed against a dataset row that is explicitly classified as NSQ.
- `No alert found`: a sufficiently readable, non-ambiguous batch was checked successfully and no qualifying row matched in the configured snapshot.
- `Expired`: expiry has been reliably interpreted as expired under an owner-approved policy, and no confirmed NSQ alert takes precedence.
- `Unable to verify`: OCR, identity, dataset integrity, or policy evidence is insufficient or conflicting.

These statuses are not interchangeable with a medicine safety assessment.

## Out of scope
Counterfeit detection, authenticity certification, chemical/laboratory testing, diagnosis, treatment recommendations, dosage advice, prescribing, barcode/QR verification, user accounts, payment, cloud OCR, persistent scan history, and regulatory-site scraping.

## Safety language
Never call a product “safe,” “genuine,” “authentic,” or “free from defects.” Explain that the check covers only the supplied August 2026 snapshot. For uncertainty, direct the user to a pharmacist or qualified healthcare professional; do not advise starting or stopping medication.

## Evidence and provenance
The supplied dataset is described as 220 records and 10 columns. This is an inspected input artifact, not independent proof of regulatory authenticity. The audit report's page/field reconciliation figures are reported by that audit; they are not an independent regulatory certification.

## Evaluation
A 60-photo evaluation (30 alert-listed, 30 non-alert) is proposed in the abstract. It has not been performed based on the available evidence. No accuracy, precision, recall, F1, time-saving, or other performance claim may be presented as a result until the protocol is executed and raw outcomes are retained.
