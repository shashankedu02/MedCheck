# Agent Instructions

- Read root `CLAUDE.md` and `README.md` first, then the relevant `docs/` specification.
- Inspect the repository before assuming implementation structure.
- Distinguish existing behavior from planned behavior in every report.
- Do not implement unresolved policy choices without asking the owner.
- Use deterministic, testable functions for normalization, matching, expiry parsing, and decision logic.
- Preserve source evidence and explain every abstention.
- Test negative cases and false-positive boundaries, not just successful matches.
- Never represent a dataset snapshot as current or comprehensive regulatory coverage.
- Report commands actually run; do not state “verified” based only on reading documentation.
