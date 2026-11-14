# Expiry Policy — Unresolved

The CSV uses month-year values such as `Jun-2026`. No authoritative day-level interpretation has been established in the supplied evidence. A prior research draft suggested treating the whole printed month as valid, but explicitly lacked authoritative confirmation. That proposal is not approved.

Until approval:
- Do not classify month-year values as definitively expired/not expired.
- Display the parsed month-year as source evidence and mark expiry interpretation unresolved.
- Keep expiry separate from NSQ matching.
- A confirmed NSQ match remains `Alert found`, with expiry caveat.
- For no-match cases where expiry is unreadable or policy-dependent, abstain or display the owner-approved field-level caveat; do not invent a cutoff.

Approval must document authoritative guidance, timezone, date boundary, supported formats, ambiguity handling, and tests.
