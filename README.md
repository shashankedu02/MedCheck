# MedCheck — Documentation Knowledge Base

**Project:** MedCheck: Photo-Based Medicine Batch Verification Using OCR and Fuzzy Matching  
**Documentation status:** Revised research specification; not evidence of implemented software.

## Start here
1. Read [project context](docs/PROJECT_CONTEXT.md) and [project specification](docs/PROJECT_SPEC.md).
2. Read [architecture](docs/ARCHITECTURE.md), [dataset specification](docs/DATASET.md), and [matching decision matrix](docs/MATCHING_DECISION_MATRIX.md).
3. Read [expiry policy](docs/EXPIRY_POLICY.md) before implementing expiry output.
4. Follow [Claude Code instructions](CLAUDE.md) and [agent instructions](AGENTS.md).
5. Use [decisions and approvals](docs/DECISIONS.md) to resolve open policy questions before coding.

## Truth labels used throughout
- **Verified input fact:** directly supported by supplied project files or prior environment checks.
- **Proposed:** a design recommendation, not implemented or approved.
- **Unresolved:** requires project-owner decision or authoritative evidence.
- **Not verified:** cannot be confirmed without the complete application source or a reproducible run.

## Project boundary
The initial prototype compares OCR-read medicine packaging details against the supplied August 2026 NSQ dataset. It is not a medicine authentication service, counterfeit detector, laboratory quality test, or medical advice system. “No alert found” means only that no qualifying match was found in the configured snapshot; it does not establish safety.

## Repository placement
Copy the contents of this package into the project root only after reviewing the proposed instructions. The package describes a proposed architecture; it does not assert that any listed Python module currently exists.
