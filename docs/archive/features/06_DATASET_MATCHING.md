# August 2026 Dataset Matching

**Feature ID:** F06  
**Project:** MedCheck: Photo-Based Medicine Batch Verification Using OCR and Fuzzy Matching  
**Status:** Detailed specification; implementation is not verified.

## 1. Shared project context
MedCheck is a planned consumer-facing lookup aid that checks a medicine package batch against the CDSCO August 2026 NSQ Drugs snapshot only. It is not medicine authentication, counterfeit detection, quality testing or medical advice. The pipeline is image input → enhancement → Tesseract OCR → extraction → conservative normalization → batch-led matching → decision → evidence-rich result. The four outcomes are **Alert found**, **No alert found**, **Expired**, and **Unable to verify**. A negative result is not proof of safety.

## 2. Goal
Find a reliable NSQ record candidate using batch-led evidence and conservative corroboration.

## 3. Scope and non-goals
**In scope:** Load and validate full dataset; search exact batch candidates first; compare product name and manufacturer as corroborating evidence; optionally use RapidFuzz to retrieve possible near-name candidates; present fuzzy batch candidates only as review/abstention evidence; require explicit corroboration; retain source serial and raw row.

**Out of scope:** authentication/counterfeit claims, clinical advice, live regulator feeds, multi-month support, user accounts, cloud history, payment, external OCR APIs, telemetry and unapproved features.

## 4. Inputs and outputs
**Inputs:** Validated August 2026 CSV records and extracted field candidates with raw/normalized forms, provenance and ambiguity.

**Outputs:** Candidate list, evidence breakdown, corroboration result, ambiguity state and explanation; no final status decision inside this module.

## 5. Detailed workflow
Load and validate full dataset; search exact batch candidates first; compare product name and manufacturer as corroborating evidence; optionally use RapidFuzz to retrieve possible near-name candidates; present fuzzy batch candidates only as review/abstention evidence; require explicit corroboration; retain source serial and raw row.

## 6. Functional and safety requirements
Batch is primary key; product name alone never alerts; fuzzy batch never auto-confirms; do not discard punctuation/leading zeros; duplicate or ambiguous candidate identity abstains; do not use fuzzy score as probability; dataset load failure blocks matching; match only August 2026 rows.

## 7. Edge cases
No exact batch; two rows share a batch; trailing comma; OCR confusable glyph; product spelling anomaly; same product multiple batches; manufacturer variation; candidate scores close; missing product field.

## 8. Failure handling and abstention
Insufficient corroboration or unresolved candidate collision -> Unable to verify. Dataset failure -> explicit system/data error, not No alert found.

## 9. Acceptance criteria
Synthetic tests prove name-only and fuzzy-batch-only cannot alert; exact batch with corroboration can retrieve a candidate; duplicate ambiguity abstains; raw row values remain visible.

## 10. Test plan
Exact match; no match; duplicate batch; product-only similarity; fuzzy-only batch; punctuation; leading zeros; ambiguous OCR; malformed CSV; reporting-month mismatch.

## 11. Privacy and medical safety
No network requests; no telemetry; avoid logging complete package text.

Always preserve original user/source evidence. Never imply that an unlisted batch is safe or genuine. If the user is uncertain, advise consulting a pharmacist or doctor; do not tell them to start or stop medication based on the app.

## 12. Unresolved decisions
Owner must approve corroboration policy and any candidate-retrieval thresholds after test data review. Thresholds cannot independently confirm alerts.

## 13. Related documentation
- [Project context](../PROJECT_CONTEXT.md)
- [Architecture](../ARCHITECTURE.md)
- [Dataset](../DATASET.md)
- [Decision log](../DECISIONS.md)
- [Testing guidelines](../TESTING_GUIDELINES.md)
- [Security guidelines](../SECURITY_GUIDELINES.md)
