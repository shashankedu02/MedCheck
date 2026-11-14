# Security, Privacy and Medical-Safety Guidelines

## Image and data privacy
- Do not persist user images by default. Implemented: images are decoded in memory and passed to Tesseract on stdin and to RapidOCR as arrays (no temp files); RapidOCR runs offline with hash-verified bundled models (`docs/OCR_ENGINES.md`); user-typed batch numbers are not logged; the Streamlit server binds to localhost, telemetry is off and uploads are capped (`.streamlit/config.toml`). Verified by tests.
- Prefer in-memory processing; if temporary files are unavoidable, use controlled random names and guaranteed cleanup.
- Do not log images, full OCR text, package identifiers or user-provided metadata.
- Limit upload bytes, pixel dimensions, decompression size, OCR time and preprocessing attempts.
- Treat image files and OCR text as untrusted input.
- Keep local configuration and secrets out of Git.

## 3D interface (frontend)
- The Components V2 stage runs trusted, project-owned JavaScript in the app page (Streamlit does not sandbox it). It is given only a phase and a status name (`medcheck_ui/scene.py`, `ALLOWED_FIELDS`); never the photo, filename, OCR text, batch number or record. `tests/test_ui_scene.py` fails if any of these reach the component payload.
- `server.enableStaticServing = true` serves only `./static/` (the vendored Three.js) from localhost. No CDN, no remote font, no remote asset: a test scans the assets for remote URLs. The Three.js file is pinned by SHA-256 (`static/vendor/three/VENDOR.json`) and stored byte-for-byte (`.gitattributes`).
- Nothing user-supplied is rendered as HTML by the presentation layer; the story text is static. A failure of the layer must never break a check: the app falls back to the plain interface (`MEDCHECK_PLAIN_UI=1` forces it).

## Deployment boundary
A local app processes images on the user's machine. A hosted Streamlit app receives and processes uploaded images on the hosting server. Never claim hosted processing is on-device. Before deployment, document provider processing, retention, access controls and deletion behavior and obtain approval.

## Data integrity
The official dataset is treated as reference data. Never silently alter source strings. Dataset parse failure must fail closed. Keep audit provenance and file hashes for releases.

## Medical-safety wording
MedCheck checks whether a batch appears in the specified NSQ snapshot. It does not test medicine quality or authenticity and cannot establish that an unlisted product is safe. Encourage consultation with a pharmacist/doctor when uncertain. Do not advise stopping or starting medicine based only on the result.

## Abuse and reliability
Do not accept arbitrary URLs or execute uploaded content. Validate MIME type and actual image decoding. Avoid rendering raw OCR text as HTML. Bound processing resources to reduce denial-of-service risk.
