# Deployment Plan

## Current recommendation
Build and test locally first. Deployment is not part of the verified current state and requires explicit approval.

## Local run
After code and dependencies exist:
```powershell
cd D:\MedCheck
.\.venv\Scripts\Activate.ps1
streamlit run app.py
```

## What a deployment would have to carry (as built)
The app needs the pinned Python packages (`requirements.txt`), the OCR packages (`requirements-ocr.txt`, installed with `--no-deps`, about 72 MB, models inside the wheel), the native Tesseract executable (optional but recommended as extra evidence and fallback), the `static/` folder (vendored Three.js, served by `server.enableStaticServing`) and the `data/` folder (immutable official extraction, canonical dataset and manifest; the loader fails closed if they do not match their pinned hashes). The 3D interface needs a browser with WebGL; without it, with reduced-motion, or with `MEDCHECK_PLAIN_UI=1`, a still or plain interface is used. Per-check time depends on the machine (a few seconds up to about 20 s on the development PC; measurements in `docs/V2_REVIEW.md`, not a guarantee).

## Hosted options
Streamlit Community Cloud may be a practical later option for a Streamlit application; Hugging Face Spaces is another possible route. Reassess current platform capabilities, resource limits, Tesseract installation and policies at deployment time rather than relying on this planning note as a current compatibility guarantee.

## Critical privacy distinction
Local execution processes the image on the user's computer. A hosted deployment uploads the image to and processes it on the hosting server. Before deployment:
- disclose the server-side image processing;
- define retention and cleanup;
- verify hosting provider policies;
- test native Tesseract installation and language data;
- set resource limits;
- avoid storing uploads;
- obtain explicit approval.

## Release checklist
Tests pass; dataset version/hash recorded; no secrets; app errors are safe; safety language visible; privacy review complete; deployment target verified; rollback plan prepared.
