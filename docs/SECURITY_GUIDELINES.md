# Security, Privacy and Medical-Safety Guidelines

## Image and data privacy
- Do not persist user images by default. Implemented: images are decoded in memory and passed to Tesseract on stdin and to RapidOCR as arrays (no temp files); RapidOCR runs offline with hash-verified bundled models (`docs/OCR_ENGINES.md`); user-typed batch numbers are not logged; the Streamlit server binds to localhost, telemetry is off and uploads are capped (`.streamlit/config.toml`). Verified by tests.
- Prefer in-memory processing; if temporary files are unavoidable, use controlled random names and guaranteed cleanup.
- Do not log images, full OCR text, package identifiers or user-provided metadata.
- Limit upload bytes, pixel dimensions, decompression size, OCR time and preprocessing attempts.
- Treat image files and OCR text as untrusted input.
- Keep local configuration and secrets out of Git.

## Deployment boundary
A local app processes images on the user's machine. A hosted Streamlit app receives and processes uploaded images on the hosting server. Never claim hosted processing is on-device. Before deployment, document provider processing, retention, access controls and deletion behavior and obtain approval.

## Data integrity
The official dataset is treated as reference data. Never silently alter source strings. Dataset parse failure must fail closed. Keep audit provenance and file hashes for releases.

## Medical-safety wording
MedCheck checks whether a batch appears in the specified NSQ snapshot. It does not test medicine quality or authenticity and cannot establish that an unlisted product is safe. Encourage consultation with a pharmacist/doctor when uncertain. Do not advise stopping or starting medicine based only on the result.

## Abuse and reliability
Do not accept arbitrary URLs or execute uploaded content. Validate MIME type and actual image decoding. Avoid rendering raw OCR text as HTML. Bound processing resources to reduce denial-of-service risk.
