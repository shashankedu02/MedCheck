# Claude Code Project Instructions

## Before changing anything
1. Inspect the actual repository tree, `git status`, current branch, and existing files.
2. Read `README.md`, `AGENTS.md`, and the relevant documents under `docs/`.
3. Treat this documentation as a specification, not proof that implementation exists.
4. Do not invent existing modules, functions, tests, paths, package versions, or successful test results.
5. In Plan mode, list files to inspect/change, the intended behavior, risks, tests, and unresolved assumptions. Wait for explicit approval before implementation when the user requests approval-first work.

## Authority and conflict handling
- Safety and privacy constraints in `docs/PROJECT_SPEC.md` take precedence over convenience.
- `docs/DECISIONS.md` distinguishes approved, proposed, and unresolved decisions. An unresolved item is not permission to choose silently.
- `docs/MATCHING_DECISION_MATRIX.md` and `docs/EXPIRY_POLICY.md` define the intended decision boundary; do not weaken abstention or create alert matches from product-name similarity alone.
- If documents conflict, stop and report the conflict. Do not silently reconcile it.

## Implementation rules
- Preserve raw OCR strings; normalize separate comparison copies.
- Batch number is primary matching evidence. Fuzzy batch matching retrieves candidates only; it never confirms an alert.
- Never silently replace O/0, I/1, S/5, or B/8.
- Product name and optional manufacturer are corroborating evidence. Product strength/formulation must be considered where available.
- Dataset load, schema, or integrity failure is a system failure, never “No alert found.”
- Keep OCR confidence, field-extraction confidence, string similarity, and identity decision separate.
- Missing, ambiguous, conflicting, or weak critical evidence must produce abstention (`Unable to verify`) rather than optimistic guessing.
- Do not claim the app is safe, authentic, genuine, or free of quality defects.
- Do not persist uploaded images by default; do not log image bytes or sensitive OCR content.

## Required workflow
1. Inspect.
2. Plan.
3. Obtain approval if required.
4. Implement the smallest coherent change.
5. Add/update tests.
6. Run relevant tests and report exact commands/results.
7. Update documentation and decision log.
8. Summarize changed files, verification performed, limitations, and remaining decisions.

## Do not
- Do not add cloud OCR, accounts, payments, analytics, database, barcode/QR scanning, or unrelated features without approval.
- Do not change the supplied source dataset to make matching easier.
- Do not claim evaluation metrics until the 60-image evaluation has actually been conducted and recorded.
