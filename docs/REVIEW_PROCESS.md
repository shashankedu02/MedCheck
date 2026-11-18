# Independent Review Process (Antigravity)

The maintainer implements; Antigravity reviews. They must never edit the same files at the same time. Antigravity works **read-only** and reports findings; the maintainer reconciles them and applies approved fixes.

## When to review
After each milestone is committed (`git log` shows `M<n>: ...`) and `BUILD_PROGRESS.md` says it is DONE. Review the commit range since the previous reviewed milestone: `git diff <previous-tag-or-commit>..HEAD`.

## How the owner runs a review
1. Open the repo in Antigravity. Tell it: "You are a read-only reviewer. Read `PROJECT_GUIDE.md`, `AGENTS.md`, `docs/REVIEW_PROCESS.md` and `BUILD_PROGRESS.md`. Review the milestone below. Do not edit any file."
2. Paste the milestone's checklist from this document.
3. Save the findings as `reviews/M<n>_antigravity.md` (create the folder if missing). Only the owner or the maintainer writes this file, never both reviewers and implementer at the same moment.
4. Tell the maintainer: "Reconcile `reviews/M<n>_antigravity.md`." The maintainer verifies each finding against the code, fixes confirmed defects with tests, records rejected findings with the reason, and updates `BUILD_PROGRESS.md`.

## Finding format
`ID | Severity (Critical/High/Medium/Low) | File:line | What is wrong | Concrete failing input or scenario | Suggested fix`. Findings without a concrete scenario are treated as questions, not defects.

## Always check (every milestone)
- Can any input produce `Alert found` without a unique exact batch key **and** corroborating product identity?
- Can any failure path (dataset, OCR engine, timeout, exception) end as `No alert found`?
- Is any O/0, I/1 (including L), S/5, B/8 substitution performed outside ambiguity detection, and can the folded key ever produce a match, an alert or a clean negative?
- Does any code, log line, test or UI text expose image bytes, filenames or OCR text, or write an image to disk?
- Does any user-facing text say safe, genuine, authentic, counterfeit-free or give medical advice?
- Are thresholds only in `medcheck/config.py`, labelled UNCALIBRATED, and never described as validated?
- Are claims in docs backed by tests that were actually run?

## Milestone checklists
- **M1 dataset:** rebuild with `scripts/build_dataset.py --check`; compare canonical vs official cell by cell; try tampering with the CSV/manifest and confirm the loader fails closed.
- **M2 decision/normalization:** read `decision.decide` as a truth table; look for a status reachable by a wrong path; test dates around month boundaries.
- **M3 matching:** attack the corroboration rule with short batches, repeated brand words, strength and form conflicts; confirm serials 38/157 abstain in both directions.
- **M4 input/OCR/extraction:** malformed, huge, animated and EXIF-rotated images; label formats that could capture the wrong field (MRP, "Mfd. by", two batches); confirm no temp files.
- **M5 pipeline/UI:** try odd files through the real uploader; check localhost binding, no telemetry, error text leakage, markup injection from OCR text.
- **M6 evaluation/docs:** verify metric definitions are not flattering (abstentions kept in denominators); check README claims against reality.

## Not in scope for reviewers
Approving OPEN decisions (D-007 expiry policy, D-014 evaluation), changing dataset files, or editing code.
