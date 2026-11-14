# Matching Logic

## Principle
Batch number is the primary identity evidence. Product name, strength/formulation, and optional manufacturer are corroborating evidence. Product-name similarity alone must never trigger `Alert found`.

## Pipeline
1. Preserve raw OCR text and field provenance (whole image/crop, OCR pass, bounding box if available).
2. Generate candidate field values from labelled regions and patterns.
3. Normalize comparison copies only; retain raw values for display and audit.
4. Retrieve dataset candidates using exact normalized batch equality first.
5. Fuzzy batch similarity may retrieve candidates for review only.
6. Check product identity and any available strength/formulation.
7. Use manufacturer only as optional corroboration when legible; do not require it when packaging does not expose it.
8. Apply the decision matrix and expiry policy.
9. Return status, evidence, dataset snapshot, and abstention reason.

## Batch normalization
Proposed conservative normalization: trim outer whitespace, Unicode-normalize consistently, case-fold/uppercase, and remove only formatting characters explicitly approved as non-semantic. Keep a raw copy. Do not strip internal characters indiscriminately. Do not map confusable characters (O/0, I/1, S/5, B/8) automatically. Preserve leading zeroes.

Before implementing punctuation removal, evaluate source examples including the trailing commas at serials 150 and 153. Punctuation can be meaningful; a normalized collision must be detected and must not auto-confirm identity.

## Product identity
Compare normalized product name plus strength and dosage form where available. Similar brand names with different strengths/formulations are not equivalent. Missing or contradictory identity evidence must be handled conservatively.

## Confidence separation
Keep distinct values for OCR confidence, extraction confidence, batch similarity, product-identity evidence, and final decision confidence. Tesseract confidence is not a calibrated probability that the medicine identity is correct.

## Abstention
Conflicting batch readings across OCR passes, multiple plausible batch candidates, ambiguous confusable characters, normalized collisions, or conflicting product identity must yield `Unable to verify` unless a transparent user correction resolves the field and the complete decision pipeline is rerun.
