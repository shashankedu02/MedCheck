# Testing Guidelines

## Unit tests
- Batch normalization preserves leading zeroes and raw value.
- Confusable characters are not auto-substituted.
- Punctuation handling does not collapse distinct identifiers.
- Product comparison distinguishes strength and dosage form.
- Date parser accepts only explicitly supported formats.
- Month-year expiry remains unresolved until policy approval.
- Exact batch plus corroborating identity can match.
- Product-name-only similarity never triggers an alert.
- Fuzzy batch candidate alone never triggers an alert.
- Duplicate normalized keys cause abstention.
- Dataset load/schema/digest failures fail closed.
- Confirmed NSQ plus expiry uncertainty retains `Alert found` with caveat.

## OCR and image tests
Use labelled sample images with ground truth for batch, product, strength, expiry, manufacturing date, and manufacturer when visible. Include blur, glare, rotation, curved foil, low contrast, perspective, tiny print, split lines, multiple labelled dates, and multiple batch-like strings. Record raw OCR outputs for each preprocessing pass.

## Integration tests
- Valid image through complete pipeline.
- No readable text.
- Conflicting OCR passes.
- Manual correction followed by complete rematch.
- Missing/corrupt CSV.
- CSV header drift and digest mismatch.
- Session cleanup and no image persistence.

## Evaluation protocol
The abstract proposes 60 images (30 alert-listed and 30 non-alert). This remains a proposed sample, not completed evaluation. Freeze and label the sample before testing. Separate development/tuning images from held-out evaluation images. Report field-level exact accuracy, alert sensitivity/recall, specificity, precision, false-negative count, false-positive count, abstention rate, coverage, and processing-time median/p95. Report confidence intervals where sample size permits. Include every failed/abstained sample in denominators appropriate to each metric.

## Claims
Never report target metrics or assumed results as achieved. Retain per-image ground truth, raw OCR, corrections, final status, error/abstention reason, and timestamps in a privacy-safe evaluation record.
