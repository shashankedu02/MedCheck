# Development Guidelines

## Working style
Build one tested vertical slice at a time. Prefer small modules and explicit data contracts over a large monolithic Streamlit script. The user is a beginner; agents must explain the purpose of each change and provide exact PowerShell commands.

## Repository hygiene
- Keep source, tests, docs and data in clear directories.
- Keep `.venv`, caches, temporary images, local secrets and generated test artifacts out of Git.
- Do not move or overwrite the canonical CSV without approval.
- Avoid duplicate copies of the canonical dataset in the repository.
- Use UTF-8 for source and Markdown.
- Use descriptive names and avoid unexplained abbreviations.

## Code quality
- Type public function inputs/outputs.
- Keep OCR and matching deterministic and testable.
- Separate pure functions from I/O.
- Use structured errors rather than broad silent exception handling.
- Avoid magic thresholds; centralize and document them.
- Do not convert OCR confidence into probability of a correct match.
- Never log raw uploaded image bytes.

## Change process
1. State the goal and acceptance criteria.
2. Inspect relevant files and current Git diff.
3. Propose a small plan.
4. Implement only approved scope.
5. Add tests before or alongside logic.
6. Run tests and show exact output.
7. Update documentation and changelog.
8. Summarize limitations and next step.

## Git
Check `git status --short` before work. Use focused commits only after the user approves. Never push or publish without explicit permission.
