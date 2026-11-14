# Image Input: Upload and Camera Capture

**Feature ID:** F01  
**Project:** MedCheck: Photo-Based Medicine Batch Verification Using OCR and Fuzzy Matching  
**Status:** Detailed specification; implementation is not verified.

## 1. Shared project context
MedCheck is a planned consumer-facing lookup aid that checks a medicine package batch against the CDSCO August 2026 NSQ Drugs snapshot only. It is not medicine authentication, counterfeit detection, quality testing or medical advice. The pipeline is image input → enhancement → Tesseract OCR → extraction → conservative normalization → batch-led matching → decision → evidence-rich result. The four outcomes are **Alert found**, **No alert found**, **Expired**, and **Unable to verify**. A negative result is not proof of safety.

## 2. Goal
Provide a safe, predictable entry point for a medicine package photograph while retaining enough image fidelity for small batch and expiry text.

## 3. Scope and non-goals
**In scope:** Present upload and camera options; enforce byte and pixel limits before expensive decoding; inspect actual format; decode safely; apply EXIF orientation; assess whether image is blank, corrupt or implausibly small; provide retake guidance; pass a normalized image object to enhancement.

**Out of scope:** authentication/counterfeit claims, clinical advice, live regulator feeds, multi-month support, user accounts, cloud history, payment, external OCR APIs, telemetry and unapproved features.

## 4. Inputs and outputs
**Inputs:** User-selected file or camera-captured image bytes; optional filename/MIME metadata. Do not trust filename or declared MIME type as proof of content.

**Outputs:** Validated image object with original dimensions, detected format, orientation-corrected working image and structured validation outcome. Keep original bytes only in transient memory unless explicit approved temporary storage is required.

## 5. Detailed workflow
Present upload and camera options; enforce byte and pixel limits before expensive decoding; inspect actual format; decode safely; apply EXIF orientation; assess whether image is blank, corrupt or implausibly small; provide retake guidance; pass a normalized image object to enhancement.

## 6. Functional and safety requirements
Accept common raster formats supported by the decoder; reject unsupported/animated or malformed inputs unless explicitly tested; cap upload size and decoded pixel count; prevent decompression bombs; handle portrait/landscape; never silently crop away batch text; do not persist by default; give clear errors.

## 7. Edge cases
Corrupt file, wrong extension, zero bytes, huge dimensions, unsupported format, rotated EXIF, glare, partial package, multiple medicine packs, cropped-off batch, camera permission denial, browser camera unavailable.

## 8. Failure handling and abstention
Reject unsafe/corrupt files with actionable guidance. If image is valid but unreadable, pass to quality assessment and allow later abstention. Never infer an identifier from filename.

## 9. Acceptance criteria
Valid upload and camera images enter the same downstream contract; EXIF orientation is correct; invalid files fail safely; size/pixel limits enforced; original file is not written to disk by default; errors do not crash the app.

## 10. Test plan
Valid JPEG/PNG; incorrect extension; corrupt bytes; zero-byte file; EXIF-rotated photo; oversized byte/pixel input; camera cancellation; duplicate upload; image with multiple packages; cleanup behavior.

## 11. Privacy and medical safety
No persistent image history. Avoid logging filenames if they may contain personal information. Hosted deployments process images on the server.

Always preserve original user/source evidence. Never imply that an unlisted batch is safe or genuine. If the user is uncertain, advise consulting a pharmacist or doctor; do not tell them to start or stop medication based on the app.

## 12. Unresolved decisions
Final byte and pixel ceilings; supported formats; browser camera behavior; whether HEIC support is needed. Do not add HEIC or PDF without approval.

## 13. Related documentation
- [Project context](../PROJECT_CONTEXT.md)
- [Architecture](../ARCHITECTURE.md)
- [Dataset](../DATASET.md)
- [Decision log](../DECISIONS.md)
- [Testing guidelines](../TESTING_GUIDELINES.md)
- [Security guidelines](../SECURITY_GUIDELINES.md)
