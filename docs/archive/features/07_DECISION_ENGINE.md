# Four-Status Decision Engine

**Feature ID:** F07  
**Project:** MedCheck: Photo-Based Medicine Batch Verification Using OCR and Fuzzy Matching  
**Status:** Detailed specification; implementation is not verified.

## 1. Shared project context
MedCheck is a planned consumer-facing lookup aid that checks a medicine package batch against the CDSCO August 2026 NSQ Drugs snapshot only. It is not medicine authentication, counterfeit detection, quality testing or medical advice. The pipeline is image input → enhancement → Tesseract OCR → extraction → conservative normalization → batch-led matching → decision → evidence-rich result. The four outcomes are **Alert found**, **No alert found**, **Expired**, and **Unable to verify**. A negative result is not proof of safety.

## 2. Goal
Convert validated evidence into one of four user-facing outcomes with safe precedence and explicit abstention.

## 3. Scope and non-goals
**In scope:** Check dataset/system health first; check confirmed NSQ match; then assess expiry if policy is resolved; assess whether a usable identifier was checked; otherwise abstain. Alert has priority over expiry.

**Out of scope:** authentication/counterfeit claims, clinical advice, live regulator feeds, multi-month support, user accounts, cloud history, payment, external OCR APIs, telemetry and unapproved features.

## 4. Inputs and outputs
**Inputs:** Image validation, OCR/extraction states, dataset health, match assessment and expiry assessment.

**Outputs:** Status, secondary warnings, evidence summary, reason codes and user guidance.

## 5. Detailed workflow
Check dataset/system health first; check confirmed NSQ match; then assess expiry if policy is resolved; assess whether a usable identifier was checked; otherwise abstain. Alert has priority over expiry.

## 6. Functional and safety requirements
Exact status labels: Alert found, No alert found, Expired, Unable to verify. Dataset load failure is a system error. Confirmed alert + expired => Alert found plus expiry warning. No alert means no qualifying match only in August 2026 snapshot. Month-year expiry policy unresolved; no month-end assumption. Expiry before Mfg anomaly is surfaced.

## 7. Edge cases
Confirmed alert and expired; no alert but expiry ambiguous; batch missing; OCR disagreement; expired package with matching alert; dataset malformed; date anomaly; future current date.

## 8. Failure handling and abstention
Never force a negative result when evidence is insufficient. System errors are not normal statuses and must be presented distinctly.

## 9. Acceptance criteria
Decision table tests cover all precedence combinations; alert+expired retains Alert found; unresolved expiry does not mask alert; no dataset -> no No alert.

## 10. Test plan
All four statuses; dataset unavailable; OCR ambiguous; exact corroborated alert; negative lookup; alert+expired; expired without alert; source date anomaly; month-only boundary.

## 11. Privacy and medical safety
Do not imply medical advice or safety certification.

Always preserve original user/source evidence. Never imply that an unlisted batch is safe or genuine. If the user is uncertain, advise consulting a pharmacist or doctor; do not tell them to start or stop medication based on the app.

## 12. Unresolved decisions
Approval required for month/year expiry boundary and exact corroboration rules.

## 13. Related documentation
- [Project context](../PROJECT_CONTEXT.md)
- [Architecture](../ARCHITECTURE.md)
- [Dataset](../DATASET.md)
- [Decision log](../DECISIONS.md)
- [Testing guidelines](../TESTING_GUIDELINES.md)
- [Security guidelines](../SECURITY_GUIDELINES.md)
