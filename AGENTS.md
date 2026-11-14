# Agent Instructions

`CLAUDE.md` is the single authoritative instruction file for this repository; read it first. This file only adds guidance for **other agents** (for example Antigravity acting as reviewer).

- Reviewers read and report; they do not edit files. Claude Code owns implementation, so the two never edit the same files at once.
- Follow `docs/REVIEW_PROCESS.md` for how to review a milestone and how to report findings.
- Distinguish existing behaviour (proven by a test run) from planned behaviour in every report.
- Report commands you actually ran and their real output; never write "verified" based only on reading documentation.
- Do not weaken abstention or safety rules; flag any code path that could produce `Alert found` without a unique exact batch plus corroborating identity, or `No alert found` after a system failure.
