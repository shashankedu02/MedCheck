# Evidence-Rich Result Interface

**Feature ID:** F08  
**Project:** MedCheck: Photo-Based Medicine Batch Verification Using OCR and Fuzzy Matching  
**Status:** Detailed specification; implementation is not verified.

## 1. Shared project context
MedCheck is a planned consumer-facing lookup aid that checks a medicine package batch against the CDSCO August 2026 NSQ Drugs snapshot only. It is not medicine authentication, counterfeit detection, quality testing or medical advice. The pipeline is image input → enhancement → Tesseract OCR → extraction → conservative normalization → batch-led matching → decision → evidence-rich result. The four outcomes are **Alert found**, **No alert found**, **Expired**, and **Unable to verify**. A negative result is not proof of safety.

## 2. Goal
Explain what the app read, what it compared, why it returned a status and what the user should do next.

## 3. Scope and non-goals
**In scope:** Show status and short explanation; show product/batch/expiry extraction; identify uncertain fields; show matching source serial and dataset row only for confirmed match; display August 2026 coverage; show retake/help guidance for abstention.

**Out of scope:** authentication/counterfeit claims, clinical advice, live regulator feeds, multi-month support, user accounts, cloud history, payment, external OCR APIs, telemetry and unapproved features.

## 4. Inputs and outputs
**Inputs:** Decision object, extracted fields, OCR evidence, candidate dataset row and warnings.

**Outputs:** Accessible Streamlit result screen with status, evidence, limitation and safe next steps.

## 5. Detailed workflow
Show status and short explanation; show product/batch/expiry extraction; identify uncertain fields; show matching source serial and dataset row only for confirmed match; display August 2026 coverage; show retake/help guidance for abstention.

## 6. Functional and safety requirements
Never use green safe badge for No alert; show source period prominently; distinguish OCR text from dataset text; show confidence as qualitative/technical evidence not probability; do not overwhelm; accessible contrast and keyboard controls; alert+expired secondary warning.

## 7. Edge cases
Very long NSQ result text; missing manufacturer; uncertain field; multiple candidates; narrow screen; user wants to retake; dataset/system error.

## 8. Failure handling and abstention
If rendering matched row fails, retain status and explain evidence unavailable; never invent source fields.

## 9. Acceptance criteria
Each status has distinct wording; no-alert disclaimer visible; matched row is traceable; unable-to-verify explains uncertainty; accessible labels and keyboard navigation.

## 10. Test plan
Snapshot/UI tests for four statuses; long text; no match disclaimer; alert+expiry; missing values; narrow layout; error screen.

## 11. Privacy and medical safety
Do not retain results or images in history; do not expose internal server paths.

Always preserve original user/source evidence. Never imply that an unlisted batch is safe or genuine. If the user is uncertain, advise consulting a pharmacist or doctor; do not tell them to start or stop medication based on the app.

## 12. Unresolved decisions
Final visual design, supported image formats/limits and wording review.

## 13. Related documentation
- [Project context](../PROJECT_CONTEXT.md)
- [Architecture](../ARCHITECTURE.md)
- [Dataset](../DATASET.md)
- [Decision log](../DECISIONS.md)
- [Testing guidelines](../TESTING_GUIDELINES.md)
- [Security guidelines](../SECURITY_GUIDELINES.md)
