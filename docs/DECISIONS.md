# Decisions Register (authoritative)

States: **Confirmed** (owner requirement), **Adopted** (engineering default chosen under the autonomy mandate; documented, reversible), **OPEN** (needs owner approval; a safe default is in force and isolated).

| ID | Topic | State | Rule / current behaviour |
|---|---|---|---|
| D-001 | Dataset scope | Confirmed | August 2026 CDSCO NSQ snapshot only; period always shown to the user |
| D-002 | Primary identity evidence | Confirmed | Batch number is primary; product-name similarity alone never alerts |
| D-003 | Fuzzy matching | Confirmed | Candidate retrieval only; can force abstention, never confirms |
| D-004 | Raw preservation | Confirmed | Raw OCR/dataset strings kept; normalized copies separate |
| D-005 | Confusables | Confirmed | No silent O/0, I/1, S/5, B/8 substitution; folding used only to detect ambiguity |
| D-006 | Manufacturer | Adopted | Optional corroboration when legible; never required, never alone sufficient |
| D-007 | Month-only expiry interpretation | **OPEN** | `Expired` is never emitted (`config.EXPIRY_POLICY_APPROVED = False`). The end-of-printed-month rule is implemented and tested behind the flag only |
| D-008 | Unreadable expiry | Adopted | Expiry is independent of the NSQ lookup; unreadable expiry does not block `No alert found`, it adds a caveat. Because `Expired` is disabled this never hides an alert. Revisit with D-007 |
| D-009 | Single image | Adopted | One image per check |
| D-010 | Language | Adopted | English only (`eng`, `osd` installed) |
| D-011 | Barcode/QR | Confirmed | Out of scope |
| D-012 | Dataset hash | Adopted | Source SHA-256 pinned in `config.py`; canonical hash in `data/dataset_manifest.json`; loader fails closed |
| D-013 | Thresholds and limits | Adopted (UNCALIBRATED) | Values live in `medcheck/config.py`, labelled UNCALIBRATED; never presented as validated |
| D-014 | 60-image evaluation | OPEN | Not performed; no metrics may be claimed. Tooling provided in M6 |
| D-015 | Canonical dataset | Confirmed | Official extraction is the immutable source; canonical CSV built by `scripts/build_dataset.py` (drop `Portal Page`, each embedded line break -> one space, nothing else) |
| D-016 | Source anomalies | Confirmed | Serials 72, 121, 136, 150, 152, 153 preserved verbatim; never corrected |
| D-017 | Batch comparison key | Adopted | NFKC, uppercase, keep only letters and digits (punctuation/spaces/trailing commas are formatting). Validated: no collisions among the 220 dataset batches |
| D-018 | Confusable collisions | Adopted | An exact key match is not confirmable if a *different* dataset row has the same confusable-folded key (e.g. serials 38 and 157). Result: `Unable to verify` |
| D-019 | Alert corroboration | Adopted | See `docs/MATCHING.md`: unique exact key + product identity evidence (brand or active-ingredient match, no strength conflict); short batches need stronger evidence |
| D-020 | System errors | Adopted | System failures are a separate result type (`Decision.system_failure`), never a status |
| D-021 | Manual correction UI | Superseded by D-024 | Was out of scope for v1; adopted in V2 with provenance and safeguards |
| D-022 | RapidOCR as primary OCR engine | Approved by owner (conditions met, see below) | Evidence: `docs/OCR_INVESTIGATION.md`. Conditions: pinned dependencies, documented installation/model/licence/size/offline operation, Tesseract retained as additional evidence and fallback, no weakening of safeguards. Details: `docs/OCR_ENGINES.md` |
| D-023 | Cascade, agreement and misread safeguards | Adopted | Two RapidOCR views (full frame, pack crop) plus Tesseract on the crop; rotation retries only when no batch label was found; one bounded confirmation pass when exactly one reading has single-pass support; strict agreement unchanged (any disagreement is AMBIGUOUS); near-neighbour abstention unchanged (edit distance 2 for keys of 6+ characters); engine scores never used as evidence; `No alert found` shows the batch checked; model files hash-verified before loading |
| D-024 | Manual batch entry | Adopted | `BatchSource` = ocr / user_corrected / user_entered kept on every decision; the typed value never becomes OCR evidence and never corroborates the product; same matching, collision and abstention rules; a clean negative for a typed batch needs the user's confirmation |

## Approval protocol for OPEN items
Record owner, date, decision, rationale, affected docs and tests. Agents must not turn an OPEN item into an approved one.
