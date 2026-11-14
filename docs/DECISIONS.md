# Decisions and Approval Register

| ID | Topic | Current state | Rule |
|---|---|---|---|
| D-001 | Dataset scope | Confirmed project scope | August 2026 snapshot only |
| D-002 | Primary identity evidence | Confirmed project requirement | Batch number primary; product name alone never alerts |
| D-003 | Fuzzy matching | Confirmed safety requirement | Candidate retrieval only, never automatic alert confirmation |
| D-004 | Raw OCR preservation | Confirmed requirement | Raw values retained separately from normalized copies |
| D-005 | Confusable characters | Confirmed requirement | No silent O/0, I/1, S/5, B/8 substitution |
| D-006 | Manufacturer | Proposed | Optional corroboration when visible; not mandatory |
| D-007 | Expiry cutoff for MMM-YYYY | **Unresolved** | Do not assign definitive Expired until authoritative policy approved |
| D-008 | Expiry mandatory for negative result | **Unresolved** | Decide whether unreadable expiry permits No alert found |
| D-009 | Multiple images | Proposed v1 constraint | Single image initially; multi-image deferred |
| D-010 | Language | Proposed | English guaranteed only; verify before configuring Hindi |
| D-011 | Barcode/QR | Out of scope | No barcode/QR interpretation in initial version |
| D-012 | Dataset digest | Proposed control | Compute and pin only after freezing approved CSV |
| D-013 | Thresholds and limits | Unresolved | Calibrate from representative data; do not invent values |
| D-014 | Evaluation | Not performed | 60-image study proposed, results not yet available |

## Approval protocol
For each unresolved item, record owner, date, decision, rationale, evidence/source, affected documents, and tests required. An agent must not convert an unresolved item into an approved decision.
