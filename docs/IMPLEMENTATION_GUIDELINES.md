# Implementation Guidelines and Sequence

## Phase 0 — inspect, do not code yet
- Inspect repository and Git status.
- Confirm canonical CSV path and compare it with this document.
- Check Python/Tesseract versions and imports.
- Resolve month-year expiry policy with project owner.
- Agree on exact corroboration requirements for an alert.

## Phase 1 — dataset contract
Implement CSV loading and validation first. Test exact headers, text-preserved batch IDs, serial uniqueness, blank identifiers, reporting month and failure modes. No UI matching until this passes.

## Phase 2 — safe result and decision skeleton
Define typed result models and four statuses. Implement status precedence independently of OCR. Test alert-plus-expired precedence and dataset-error behavior.

## Phase 3 — image input and OCR vertical slice
Accept one image, validate it, apply orientation correction, run one baseline Tesseract pass, display OCR evidence and extracted candidate fields. If uncertain, abstain.

## Phase 4 — field extraction and normalization
Extract product, batch and expiry with source locations/confidence. Keep raw and normalized forms. Preserve leading zeros/punctuation and ambiguous characters.

## Phase 5 — conservative matching
Exact batch candidate retrieval first. Require product/manufacturer corroboration. Fuzzy similarity may surface possible candidates but cannot auto-confirm. Multiple candidates or conflicting evidence -> Unable to verify.

## Phase 6 — adaptive preprocessing
Add bounded image variants only after a baseline benchmark. Evaluate each transformation's effect on field-level accuracy; avoid expensive or destructive operations without evidence.

## Phase 7 — UI, errors, evaluation
Build clear status views, dataset limitations, privacy notices and user guidance. Run tests and a labelled image evaluation. Report actual results only.

## Phase 8 — deployment (separate approval)
Local operation first. Deployment requires privacy review, environment setup, OCR engine installation, image retention review and explicit user approval.
