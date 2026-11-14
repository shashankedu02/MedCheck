# Tesseract OCR Engine Adapter

**Feature ID:** F03  
**Project:** MedCheck: Photo-Based Medicine Batch Verification Using OCR and Fuzzy Matching  
**Status:** Detailed specification; implementation is not verified.

## 1. Shared project context
MedCheck is a planned consumer-facing lookup aid that checks a medicine package batch against the CDSCO August 2026 NSQ Drugs snapshot only. It is not medicine authentication, counterfeit detection, quality testing or medical advice. The pipeline is image input → enhancement → Tesseract OCR → extraction → conservative normalization → batch-led matching → decision → evidence-rich result. The four outcomes are **Alert found**, **No alert found**, **Expired**, and **Unable to verify**. A negative result is not proof of safety.

## 2. Goal
Provide a controlled, testable interface to the installed Tesseract engine and preserve raw OCR observations with provenance.

## 3. Scope and non-goals
**In scope:** Check executable availability; invoke Tesseract through pytesseract; use appropriate page segmentation configurations for package regions; request text and word-level data; enforce timeout and attempt limits; retain raw output; map each observation to the source variant.

**Out of scope:** authentication/counterfeit claims, clinical advice, live regulator feeds, multi-month support, user accounts, cloud history, payment, external OCR APIs, telemetry and unapproved features.

## 4. Inputs and outputs
**Inputs:** Image variants and OCR configuration: language, page segmentation mode, engine mode, timeout and output formats.

**Outputs:** Structured OCR observations: raw text, token/word boxes, confidence values, variant ID, engine version and configuration.

## 5. Detailed workflow
Check executable availability; invoke Tesseract through pytesseract; use appropriate page segmentation configurations for package regions; request text and word-level data; enforce timeout and attempt limits; retain raw output; map each observation to the source variant.

## 6. Functional and safety requirements
Separate native Tesseract from Python wrapper; configure executable path without developer-specific hardcoding; record engine version; bound attempts; avoid hidden retries; expose stderr/errors safely; do not interpret confidence as probability; do not silently alter OCR characters.

## 7. Edge cases
Executable missing, incompatible language data, timeout, empty OCR, malformed output, low confidence, multiple columns, curved text, mixed fonts, batch with punctuation, OCR returns conflicting variants.

## 8. Failure handling and abstention
Missing engine is setup/system error. Empty or ambiguous text becomes Unable to verify after a bounded attempt budget. Do not use external OCR APIs.

## 9. Acceptance criteria
Engine health check works; structured tokens preserve text and coordinates; timeout enforced; raw output reproducible for fixture; errors are distinguishable from no-match.

## 10. Test plan
Engine missing; version retrieval; empty page; timeout; token bounding boxes; confidence range handling; punctuation; leading zeros; repeated calls; multiple variant provenance.

## 11. Privacy and medical safety
Do not log full package OCR text by default. No remote OCR transmission.

Always preserve original user/source evidence. Never imply that an unlisted batch is safe or genuine. If the user is uncertain, advise consulting a pharmacist or doctor; do not tell them to start or stop medication based on the app.

## 12. Unresolved decisions
Language packs, PSM selection, engine mode and timeout values must be validated on target images and deployment platform.

## 13. Related documentation
- [Project context](../PROJECT_CONTEXT.md)
- [Architecture](../ARCHITECTURE.md)
- [Dataset](../DATASET.md)
- [Decision log](../DECISIONS.md)
- [Testing guidelines](../TESTING_GUIDELINES.md)
- [Security guidelines](../SECURITY_GUIDELINES.md)
