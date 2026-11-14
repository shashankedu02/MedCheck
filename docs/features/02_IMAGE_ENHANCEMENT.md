# Adaptive Image Enhancement

**Feature ID:** F02  
**Project:** MedCheck: Photo-Based Medicine Batch Verification Using OCR and Fuzzy Matching  
**Status:** Detailed specification; implementation is not verified.

## 1. Shared project context
MedCheck is a planned consumer-facing lookup aid that checks a medicine package batch against the CDSCO August 2026 NSQ Drugs snapshot only. It is not medicine authentication, counterfeit detection, quality testing or medical advice. The pipeline is image input → enhancement → Tesseract OCR → extraction → conservative normalization → batch-led matching → decision → evidence-rich result. The four outcomes are **Alert found**, **No alert found**, **Expired**, and **Unable to verify**. A negative result is not proof of safety.

## 2. Goal
Improve legibility of printed product, batch and expiry text while preserving original evidence and avoiding transformations that create misleading characters.

## 3. Scope and non-goals
**In scope:** Assess resolution, blur, contrast, glare, skew and perspective. Generate only useful variants: grayscale; contrast/CLAHE; mild denoising; Otsu threshold; adaptive threshold; optional cautious sharpening. Deskew when angle estimate is reliable. Apply perspective correction only when package-plane corners are confidently detected. Keep original as a candidate. Limit variants and total processing time. OCR selected variants and compare extracted critical fields; do not choose solely by aggregate OCR confidence.

**Out of scope:** authentication/counterfeit claims, clinical advice, live regulator feeds, multi-month support, user accounts, cloud history, payment, external OCR APIs, telemetry and unapproved features.

## 4. Inputs and outputs
**Inputs:** Validated orientation-corrected image, quality metrics and configured resource limits.

**Outputs:** Original plus a bounded, labelled set of preprocessing variants; per-variant metadata describing transformations; quality assessment and warnings.

## 5. Detailed workflow
Assess resolution, blur, contrast, glare, skew and perspective. Generate only useful variants: grayscale; contrast/CLAHE; mild denoising; Otsu threshold; adaptive threshold; optional cautious sharpening. Deskew when angle estimate is reliable. Apply perspective correction only when package-plane corners are confidently detected. Keep original as a candidate. Limit variants and total processing time. OCR selected variants and compare extracted critical fields; do not choose solely by aggregate OCR confidence.

## 6. Functional and safety requirements
EXIF orientation before geometry; no destructive overwrite; bounded dimensions and variant count; deterministic settings; preserve a mapping to source; transformations must not invent strokes; perspective warp only with reliable quadrilateral; denoising/sharpening conditional; compare batch/product/expiry agreement across variants; conflicts cause abstention.

## 7. Edge cases
Glossy foil glare, curved blister, low resolution, motion blur, strong shadows, colored print, embossed text, transparent packaging, oblique angle, partial occlusion, tiny font, image already high quality.

## 8. Failure handling and abstention
If enhancement does not improve legibility, retain original and report uncertainty. If variants produce conflicting batch candidates, mark conflict; never auto-select the most convenient reading.

## 9. Acceptance criteria
Bounded pipeline completes within configured budget; original is preserved; each variant is traceable; no perspective warp on uncertain corners; critical-field disagreement is surfaced; ablation tests show whether each operation helps.

## 10. Test plan
Synthetic skew; perspective quadrilateral positive/negative; glare/blur samples; low contrast; over-sharpening regression; threshold variants; memory/time limits; repeatability; conflicting OCR variants.

## 11. Privacy and medical safety
Process in memory where possible; clear temporary buffers; do not write intermediate images to persistent user directories.

Always preserve original user/source evidence. Never imply that an unlisted batch is safe or genuine. If the user is uncertain, advise consulting a pharmacist or doctor; do not tell them to start or stop medication based on the app.

## 12. Unresolved decisions
Threshold values, quality cutoffs, maximum variants and processing budget require measurement on representative package images. Do not invent universal optimal settings.

## 13. Related documentation
- [Project context](../PROJECT_CONTEXT.md)
- [Architecture](../ARCHITECTURE.md)
- [Dataset](../DATASET.md)
- [Decision log](../DECISIONS.md)
- [Testing guidelines](../TESTING_GUIDELINES.md)
- [Security guidelines](../SECURITY_GUIDELINES.md)
