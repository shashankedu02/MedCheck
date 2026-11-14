# Product, Batch and Expiry Field Extraction

**Feature ID:** F04  
**Project:** MedCheck: Photo-Based Medicine Batch Verification Using OCR and Fuzzy Matching  
**Status:** Detailed specification; implementation is not verified.

## 1. Shared project context
MedCheck is a planned consumer-facing lookup aid that checks a medicine package batch against the CDSCO August 2026 NSQ Drugs snapshot only. It is not medicine authentication, counterfeit detection, quality testing or medical advice. The pipeline is image input → enhancement → Tesseract OCR → extraction → conservative normalization → batch-led matching → decision → evidence-rich result. The four outcomes are **Alert found**, **No alert found**, **Expired**, and **Unable to verify**. A negative result is not proof of safety.

## 2. Goal
Turn OCR observations into explicit candidate fields with confidence, provenance and ambiguity rather than guessing.

## 3. Scope and non-goals
**In scope:** Identify label cues such as Batch/Batch No./B.No./Lot and Mfg/Exp labels; associate nearby text spatially; distinguish manufacturing and expiry labels; infer product name from prominent text only as a candidate; compare across OCR variants; retain alternatives when multiple candidates exist.

**Out of scope:** authentication/counterfeit claims, clinical advice, live regulator feeds, multi-month support, user accounts, cloud history, payment, external OCR APIs, telemetry and unapproved features.

## 4. Inputs and outputs
**Inputs:** OCR text, word-level boxes, confidence, variant IDs and known package layout cues.

**Outputs:** Candidate product name, batch number and expiry date; each includes raw text, source tokens/coordinates, confidence indicator, parse state and ambiguity reasons.

## 5. Detailed workflow
Identify label cues such as Batch/Batch No./B.No./Lot and Mfg/Exp labels; associate nearby text spatially; distinguish manufacturing and expiry labels; infer product name from prominent text only as a candidate; compare across OCR variants; retain alternatives when multiple candidates exist.

## 6. Functional and safety requirements
No fabricated field; no silent correction of ambiguous glyphs; batch punctuation/leading zeros retained; expiry and manufacturing labels not swapped; source tokens traceable; field confidence separate from match confidence; allow missing fields; multiple plausible batch candidates trigger ambiguity.

## 7. Edge cases
Batch label absent, batch split across lines, two batches on carton and strip, expiry next to manufacturing, best-before wording, OCR reading O/0, product text with many ingredients, batch printed on fold.

## 8. Failure handling and abstention
If batch cannot be uniquely established, downstream status must be Unable to verify. Do not fall back to product name alone for alert detection.

## 9. Acceptance criteria
Known fixtures extract correct field or explicitly abstain; raw text retained; ambiguous alternatives visible; expiry/Mfg confusion tested; every extracted field has provenance.

## 10. Test plan
Label variations; multi-line identifiers; two candidate batches; Mfg/Exp swap; ambiguous characters; product name false positives; missing field; cross-variant disagreement.

## 11. Privacy and medical safety
Keep extracted text transient; do not store package details or OCR output in analytics.

Always preserve original user/source evidence. Never imply that an unlisted batch is safe or genuine. If the user is uncertain, advise consulting a pharmacist or doctor; do not tell them to start or stop medication based on the app.

## 12. Unresolved decisions
Supported label vocabulary and any language coverage; do not assume all Indian package layouts are uniform.

## 13. Related documentation
- [Project context](../PROJECT_CONTEXT.md)
- [Architecture](../ARCHITECTURE.md)
- [Dataset](../DATASET.md)
- [Decision log](../DECISIONS.md)
- [Testing guidelines](../TESTING_GUIDELINES.md)
- [Security guidelines](../SECURITY_GUIDELINES.md)
