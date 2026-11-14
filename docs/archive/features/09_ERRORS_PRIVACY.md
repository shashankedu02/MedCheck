# Error Handling, Privacy and Safety

**Feature ID:** F09  
**Project:** MedCheck: Photo-Based Medicine Batch Verification Using OCR and Fuzzy Matching  
**Status:** Detailed specification; implementation is not verified.

## 1. Shared project context
MedCheck is a planned consumer-facing lookup aid that checks a medicine package batch against the CDSCO August 2026 NSQ Drugs snapshot only. It is not medicine authentication, counterfeit detection, quality testing or medical advice. The pipeline is image input → enhancement → Tesseract OCR → extraction → conservative normalization → batch-led matching → decision → evidence-rich result. The four outcomes are **Alert found**, **No alert found**, **Expired**, and **Unable to verify**. A negative result is not proof of safety.

## 2. Goal
Make technical failures explicit, prevent sensitive image retention and avoid misleading medical interpretations.

## 3. Scope and non-goals
**In scope:** Validate at boundary; classify errors; stop unsafe processing; clean temporary data; show actionable message; keep technical diagnostics separate from user-facing details.

**Out of scope:** authentication/counterfeit claims, clinical advice, live regulator feeds, multi-month support, user accounts, cloud history, payment, external OCR APIs, telemetry and unapproved features.

## 4. Inputs and outputs
**Inputs:** All user input, file/decode/OCR/dataset/runtime exceptions and deployment configuration.

**Outputs:** Typed error categories, safe user messages, diagnostic logs without sensitive content, cleanup actions.

## 5. Detailed workflow
Validate at boundary; classify errors; stop unsafe processing; clean temporary data; show actionable message; keep technical diagnostics separate from user-facing details.

## 6. Functional and safety requirements
No image persistence by default; no external OCR; no telemetry; bounded resource use; dataset errors distinct from No alert; no raw image or full OCR logs; user can retry; safety disclaimer always available; hosted server processing disclosed.

## 7. Edge cases
Corrupt upload, malicious file, huge image, OCR executable absent, timeout, CSV altered, disk full, unexpected exception, hosted request interruption.

## 8. Failure handling and abstention
Fail closed; do not continue with partial dataset; avoid stack traces in public UI; preserve useful developer diagnostics without personal/package data.

## 9. Acceptance criteria
Temporary files cleaned; invalid inputs rejected; system errors are not normal negative results; logs are privacy-minimal; hosted/local distinction is accurate.

## 10. Test plan
Failure injection for every boundary; cleanup after exception; log redaction; missing CSV; schema mismatch; OCR timeout; upload limit; unexpected exception.

## 11. Privacy and medical safety
Local app processes locally; hosted app processes on server. No claim of on-device privacy after deployment.

Always preserve original user/source evidence. Never imply that an unlisted batch is safe or genuine. If the user is uncertain, advise consulting a pharmacist or doctor; do not tell them to start or stop medication based on the app.

## 12. Unresolved decisions
Final upload/time limits, logging retention and hosting policy require explicit review.

## 13. Related documentation
- [Project context](../PROJECT_CONTEXT.md)
- [Architecture](../ARCHITECTURE.md)
- [Dataset](../DATASET.md)
- [Decision log](../DECISIONS.md)
- [Testing guidelines](../TESTING_GUIDELINES.md)
- [Security guidelines](../SECURITY_GUIDELINES.md)
