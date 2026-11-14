# Matching and Decision Specification (authoritative)

Status: **implemented and tested** (M2-M3). Code: `medcheck/normalization.py`, `product.py`, `matching.py`, `dates.py`, `decision.py`. Tests: `tests/test_normalization_dates.py`, `test_matching.py`, `test_decision.py`. Supersedes the earlier separate matching-logic and decision-matrix documents (preserved in git history).

## Principles (non-negotiable)
Batch number is the primary identity evidence. Product name, strength, form and (optionally) manufacturer only **corroborate**. Product-name similarity alone never alerts. Fuzzy/near-batch similarity retrieves candidates for abstention and display only. Raw strings are preserved; comparison copies are separate. Confusable characters are never silently substituted. OCR confidence, extraction confidence, string similarity and the identity decision are separate quantities and none is a probability.

## Comparison keys (D-017)
`batch_key(raw)`: Unicode NFKC, uppercase, keep only `A-Z0-9`. Spaces, hyphens, slashes and trailing commas are treated as formatting. Leading zeros and every letter/digit survive. A second key, `confusable_key`, additionally folds O->0, I->1, L->1, S->5, B->8 and is used **only** to detect ambiguity, never to confirm.
Validated on the dataset: no two rows share an exact key; exactly one confusable pair exists (serials 38 and 157).

## Match outcomes (`MatchOutcome`)
Evaluated in this order for a cleanly-read batch:
1. **COLLISION**: several rows share the exact key, **or** the exact row has a *different* row with the same confusable key (D-018). Example: `BKBP02601` (serial 38) vs `BKBP O2601` (serial 157, letter O): a reading of either cannot be tied to one entry, even with perfect product text.
2. Exact unique row, then identity (`product.score_identity`):
   - **CONFLICT**: strength or dosage form read from the photo contradicts the listed row.
   - **CONFIRMED**: corroborated (below).
   - **UNCORROBORATED**: otherwise.
3. No exact row: **FUZZY_ONLY** if a row is confusable-equivalent or within edit distance (keys shorter than 6 characters: exact-only retrieval; 6-9 characters: distance 1; 10+: distance 2). Else **NO_MATCH**.

### Corroboration rule (D-019)
Identity is corroborated when **brand** (a real brand name or alias from the dataset name, `NA` excluded, or the whole name when it contains no generic words, e.g. `DEC-Plus`) **or all required active-ingredient words** are found in the photo text, and there is no strength/form conflict. Salt words (sodium, potassium, hydrochloride...) are not required. **Short batches** (key shorter than 6 characters) need two independent signals: all ingredient words **and** (brand or manufacturer). Manufacturer alone never corroborates.
Simulated check on the real dataset (perfect text, no OCR involved): with the full label text 218/220 rows confirm and 38/157 abstain; with the product name only 204 confirm, 14 short-batch rows are uncorroborated and 38/157 abstain. This characterises the rules, not OCR accuracy.

## Extraction safeguards that feed matching (V2)
- A batch is read only from a label (`B.No.`, `Batch`, `Lot`, ...). The value ends at the next label even when OCR dropped the space (`5BA1617MFD` -> `5BA1617`); a value that is only label words, has no digit, is shorter than 3 or longer than 20 characters is rejected, not trimmed into something plausible.
- Strict agreement: all passes that report a batch must agree on the normalised key; any different reading is AMBIGUOUS. Tesseract readings take part; a disagreeing one makes the batch AMBIGUOUS. A single supporting pass is not enough; exactly one extra confirmation pass at another scale is allowed, never a retry until readings agree.
- Provenance: `BatchField.reading_sources` records every raw reading with `engine:view`. OCR scores are never used as evidence.
- Near-neighbour abstention (edit distance up to 2 for keys of 6+ characters) covers the misreads observed in the investigation (`HLAS50019`, `5BA13A7`, `INA26083`, `18261604K8`) whenever the true batch is listed (tested). It cannot cover a larger misread; the decision text therefore shows the batch checked.

## Confirmation of clean negatives (D-026)
Two engines can agree on the same wrong look-alike character (`HLA50019` read for `HLAS0019`). When the true batch is listed, that misread is a near-neighbour and abstains; when it is not near any listed batch nothing in the data can reveal it, and automatic S/5 substitution is forbidden. So **no clean negative (`No alert found`, `Expired`) is shown for any batch string until the user has compared it with the pack and confirmed it**; the confirmed result records `batch_confirmed` and `Batch checked: <string> (confirmed by you against the pack)`. `Alert found` is never delayed: it needs an exact listed batch plus product corroboration, which a misread rarely satisfies. If the user cannot or does not confirm, the result stays `Unable to verify`. Confirming means the user checked the printed batch number; it does not show the medicine is genuine or safe. If someone ticks without looking, the result records their confirmation; no software can prevent that.

## Manual entry (D-024)
A typed or corrected batch enters `match_batch` exactly like an OCR batch, with product corroboration taken only from the photo's OCR text. It is recorded as `BatchSource.USER_ENTERED` or `USER_CORRECTED` on the decision, adds a caveat saying so, and a clean negative (`No alert found`) requires the user's confirmation that the number was compared with the pack; otherwise the result is `Unable to verify` (`manual_entry_unconfirmed`). Since D-026 the same requirement applies to an OCR-read batch. Collision (38/157), near-neighbour, uncorroborated and conflict outcomes behave identically to OCR batches.

## Decision table (`decision.decide`)
| Condition | Result |
|---|---|
| Dataset missing/malformed/hash mismatch, OCR engine missing/timeout, internal error | **System error** (separate type, not a status) |
| Batch not found, or ambiguous/conflicting across OCR passes | Unable to verify |
| COLLISION, UNCORROBORATED, CONFLICT or FUZZY_ONLY | Unable to verify |
| CONFIRMED | **Alert found**; expiry adds only a caveat |
| NO_MATCH, batch **not yet confirmed** by the user against the pack | **Unable to verify** (`ocr_batch_unconfirmed` for an OCR reading, `manual_entry_unconfirmed` for a typed/corrected one) |
| NO_MATCH, confirmed, and expiry verdict EXPIRED (never while D-007 is open) | Expired |
| NO_MATCH, confirmed, otherwise | No alert found (period-limited wording, batch checked shown) |

`Expired` is never emitted while `EXPIRY_POLICY_APPROVED` is false (see `EXPIRY_POLICY.md`). `Expired` can never replace or hide an abstention. An alert always takes precedence over expiry.

## Wording rules
Never "safe", "genuine", "authentic", "counterfeit" or "free of defects" except in explicit negation. Always state the dataset period. No medical advice; refer to a pharmacist or doctor when unsure. Enforced by a test over every decision text.

## Known limitations
- Product corroboration relies on OCR text containing the brand or all ingredient words; labels that print only a different trade name will abstain.
- Confusable folding is limited to the four named pairs plus lowercase L; other OCR confusions (e.g. 5/6, 2/Z) are handled only by the edit-distance retrieval (abstention), not by folding.
- Thresholds in `config.py` are UNCALIBRATED.
