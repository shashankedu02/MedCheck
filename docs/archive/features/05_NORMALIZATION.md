# Conservative Text Normalization

**Feature ID:** F05  
**Project:** MedCheck: Photo-Based Medicine Batch Verification Using OCR and Fuzzy Matching  
**Status:** Detailed specification; implementation is not verified.

## 1. Shared project context
MedCheck is a planned consumer-facing lookup aid that checks a medicine package batch against the CDSCO August 2026 NSQ Drugs snapshot only. It is not medicine authentication, counterfeit detection, quality testing or medical advice. The pipeline is image input → enhancement → Tesseract OCR → extraction → conservative normalization → batch-led matching → decision → evidence-rich result. The four outcomes are **Alert found**, **No alert found**, **Expired**, and **Unable to verify**. A negative result is not proof of safety.

## 2. Goal
Create comparison representations without changing the original OCR or source dataset values.

## 3. Scope and non-goals
**In scope:** Trim only clearly irrelevant outer whitespace for comparison; apply Unicode normalization consistently; case-fold where appropriate; collapse repeated whitespace for product-name comparison only; preserve raw values separately; retain punctuation and leading zeros in batch identifiers; generate alternate candidate keys only when explicitly reviewed and never use them to auto-confirm.

**Out of scope:** authentication/counterfeit claims, clinical advice, live regulator feeds, multi-month support, user accounts, cloud history, payment, external OCR APIs, telemetry and unapproved features.

## 4. Inputs and outputs
**Inputs:** Raw OCR field values and raw CSV field values.

**Outputs:** Raw value, display-cleaned value where safe, conservative normalized comparison key, and normalization trace.

## 5. Detailed workflow
Trim only clearly irrelevant outer whitespace for comparison; apply Unicode normalization consistently; case-fold where appropriate; collapse repeated whitespace for product-name comparison only; preserve raw values separately; retain punctuation and leading zeros in batch identifiers; generate alternate candidate keys only when explicitly reviewed and never use them to auto-confirm.

## 6. Functional and safety requirements
No destructive in-place edits; no numeric conversion of batch; preserve punctuation; preserve leading zeros; do not automatically map O/0, I/1, S/5, B/8; do not strip trailing commas from raw batch; record every transformation; date parsing must retain original string.

## 7. Edge cases
Unicode dashes, nonbreaking spaces, repeated spaces, question marks, source misspellings, trailing commas, leading zeros, mixed case, OCR confusable characters.

## 8. Failure handling and abstention
If normalization creates a collision or loses a meaningful distinction, mark ambiguity and abstain. Never normalize two distinct batches into a confirmed same key without review.

## 9. Acceptance criteria
Round-trip raw values unchanged; normalization is deterministic; leading zeros and punctuation survive; confusables remain distinct; test cases cover known source anomalies.

## 10. Test plan
Serial 72/152 odd product strings; serials 150/153 trailing commas; leading-zero batch; O/0 and I/1; Unicode punctuation; repeated whitespace; idempotence.

## 11. Privacy and medical safety
Do not expose normalized identifiers as if they were the original printed text; show raw and comparison forms distinctly when useful.

Always preserve original user/source evidence. Never imply that an unlisted batch is safe or genuine. If the user is uncertain, advise consulting a pharmacist or doctor; do not tell them to start or stop medication based on the app.

## 12. Unresolved decisions
Define precisely which whitespace/case transformations are allowed for each field. No universal normalization function for all fields.

## 13. Related documentation
- [Project context](../PROJECT_CONTEXT.md)
- [Architecture](../ARCHITECTURE.md)
- [Dataset](../DATASET.md)
- [Decision log](../DECISIONS.md)
- [Testing guidelines](../TESTING_GUIDELINES.md)
- [Security guidelines](../SECURITY_GUIDELINES.md)
