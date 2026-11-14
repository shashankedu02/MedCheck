# Expiry Policy (D-007 OPEN)

The dataset and most packaging print month-year expiry (`Jun-2026`, `06/2026`). No authoritative day-level interpretation has been established, so **MedCheck never emits `Expired`** (`config.EXPIRY_POLICY_APPROVED = False`).

## Implemented behaviour (`medcheck/dates.py`, `medcheck/decision.py`)
- Parsing supports only month-year formats (MM/YYYY, MM-YY, MMM YYYY, YYYY-MM, ...). Day-level dates, month > 12 and anything else are reported as *unparseable*, never guessed.
- Policy off (current): a parsed expiry yields `UNDETERMINED` with the note "How month-only expiry dates are interpreted has not been approved".
- Expiry never affects `Alert found`; it only adds a caveat.
- With no NSQ match, expiry cannot change the result while the policy is off: the result is `No alert found` plus the caveat.
- An expiry earlier than the manufacturing date is surfaced as a possible misread.

## Implemented but disabled option
If the owner approves, setting the flag enables: valid through the last day of the printed month; strictly after that day -> `EXPIRED`. Boundary tests exist (`tests/test_normalization_dates.py`). Alternatives (first of month, never expire month-only dates) are not implemented.

## To approve
Provide authoritative guidance (e.g. Drugs and Cosmetics Rules labelling text), timezone/date source, and confirm the rule. Then flip the flag, update this file and `docs/DECISIONS.md`.
