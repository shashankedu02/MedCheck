# Archive Validation Report

- Generated: 2026-11-13
- Markdown files before this report: 31
- Ten feature specification files: 10
- CSV inspected in this session: 220 rows × 10 columns
- CSV blank cells observed: 0
- Serial sequence observed: 1–220, no duplicate serials
- Exact duplicate raw batch values observed: 0
- Audit log rows: 22 page entries; 2 mismatch entries; 0 unresolved entries
- Relative Markdown links checked: 93
- Broken relative links: 0

## Link check details
- No broken relative links detected.

## Consistency checks performed
- Four status names are consistent across the core specifications.
- Alert takes precedence over expiry when a match is confirmed.
- Dataset errors are not treated as No alert found.
- Product-name-only and fuzzy-batch-only matches cannot confirm alerts.
- Month-year expiry does not assume month-end.
- August 2026 is the only initial dataset scope.
- Documentation distinguishes specified behavior from implemented behavior.

## Limitations
- No application source repository was uploaded for inspection.
- Live CDSCO portal and screenshot evidence were not independently re-verified in this session.
- No OCR or app tests were run; no performance claims are made.
- The local copy at `D:\MedCheck\data` was not independently compared byte-for-byte with the uploaded CSV.
