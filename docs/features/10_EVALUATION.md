# Evaluation and Validation Protocol

**Feature ID:** F10  
**Project:** MedCheck: Photo-Based Medicine Batch Verification Using OCR and Fuzzy Matching  
**Status:** Detailed specification; implementation is not verified.

## 1. Shared project context
MedCheck is a planned consumer-facing lookup aid that checks a medicine package batch against the CDSCO August 2026 NSQ Drugs snapshot only. It is not medicine authentication, counterfeit detection, quality testing or medical advice. The pipeline is image input → enhancement → Tesseract OCR → extraction → conservative normalization → batch-led matching → decision → evidence-rich result. The four outcomes are **Alert found**, **No alert found**, **Expired**, and **Unable to verify**. A negative result is not proof of safety.

## 2. Goal
Measure OCR and alert lookup performance honestly on labelled package photographs.

## 3. Scope and non-goals
**In scope:** Collect 60 images as proposed in abstract: 30 alert-listed and 30 non-alert. Define ground truth independently; record image conditions; freeze split and app version; run blind evaluation; compare extracted fields and final status; manually adjudicate errors; report uncertainty and limitations.

**Out of scope:** authentication/counterfeit claims, clinical advice, live regulator feeds, multi-month support, user accounts, cloud history, payment, external OCR APIs, telemetry and unapproved features.

## 4. Inputs and outputs
**Inputs:** Frozen app build, frozen dataset snapshot, labelled images, ground-truth fields, test protocol and environment metadata.

**Outputs:** Field accuracy, matching metrics, abstention rate, latency and error analysis report.

## 5. Detailed workflow
Collect 60 images as proposed in abstract: 30 alert-listed and 30 non-alert. Define ground truth independently; record image conditions; freeze split and app version; run blind evaluation; compare extracted fields and final status; manually adjudicate errors; report uncertainty and limitations.

## 6. Functional and safety requirements
Treat 60 images as a planned target, not completed results. Avoid tuning on held-out test images. Report false negatives and false positives separately; include Unable-to-verify rate; report field-level metrics; record hardware/software/dataset hash; no fabricated values.

## 7. Edge cases
Unbalanced categories, duplicate images, poor ground truth, multiple batches, partially visible labels, out-of-scope month, data leakage, OCR language mismatch.

## 8. Failure handling and abstention
If labels are uncertain or sample protocol compromised, disclose and do not claim validated performance. Do not hide abstentions from denominator.

## 9. Acceptance criteria
Reproducible protocol; every image labelled; results include confusion matrix, field accuracy, precision/recall, specificity, abstention and latency; errors discussed.

## 10. Test plan
Metric calculation unit tests; duplicate detection; split integrity; repeat run; audit of false-negative and false-positive examples.

## 11. Privacy and medical safety
Obtain permission for package images; redact personal information; store evaluation images securely and delete when no longer needed.

Always preserve original user/source evidence. Never imply that an unlisted batch is safe or genuine. If the user is uncertain, advise consulting a pharmacist or doctor; do not tell them to start or stop medication based on the app.

## 12. Unresolved decisions
Recruitment/source of 60 images, consent/privacy, image label adjudication and evaluation split require owner approval.

## 13. Related documentation
- [Project context](../PROJECT_CONTEXT.md)
- [Architecture](../ARCHITECTURE.md)
- [Dataset](../DATASET.md)
- [Decision log](../DECISIONS.md)
- [Testing guidelines](../TESTING_GUIDELINES.md)
- [Security guidelines](../SECURITY_GUIDELINES.md)
