# UI/UX Guidelines

## Main screen
Explain in one short paragraph that the tool checks an image against the August 2026 CDSCO NSQ Drugs list only. Offer two input methods: upload and camera capture. State supported image formats and size limits after they are implemented.

## Results
Show the primary status prominently, followed by:
- extracted product name, batch number and expiry date;
- whether each field was clear, uncertain or unavailable;
- relevant OCR evidence without overwhelming the user;
- matched dataset record and its source serial number, only when a candidate is established;
- reason for abstention or mismatch;
- dataset period and scope limitation;
- safety guidance.

## Status wording
- **Alert found:** say that the extracted batch and corroborating fields matched an entry in the August 2026 NSQ snapshot. Show source row and NSQ result.
- **No alert found:** explicitly say no qualifying match was found in this one-month snapshot; this does not establish safety or authenticity.
- **Expired:** show the parsed expiry basis and policy; if month-only ambiguity remains unresolved, do not make a definitive claim.
- **Unable to verify:** explain what is missing/conflicting and suggest a clearer photo or pharmacist consultation.

## Accessibility and trust
Use readable contrast, clear labels, keyboard-operable controls, plain language and visible uncertainty. Do not use green “safe” indicators for No alert found. Avoid fear-inducing language. Never hide the August-only limitation in a footer.
