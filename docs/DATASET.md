# Dataset Specification (authoritative)

Status: **implemented and tested** (milestone M1). Code: `scripts/build_dataset.py`, `medcheck/dataset.py`, tests in `tests/test_dataset.py`.

## Files
| File | Role | SHA-256 |
|---|---|---|
| `data/cdsco_august_2026_nsq_official_extraction.csv` | **Immutable source reference.** 220 records from the official CDSCO portal (22 pages, NSQ Drugs, Aug-2026, source "All"), with a leading `Portal Page` column. Never edit. | `1eb25a9f6de052cc0be926c5785ad4a6b918ce8d06e030dc3552869d333edcef` (pinned in `medcheck/config.py`) |
| `data/cdsco_august_2026_nsq.csv` | **Canonical application dataset**, generated from the source. The only file the app reads. | recorded in `data/dataset_manifest.json` |
| `data/dataset_manifest.json` | Provenance, hashes, record count, columns, transformation, known anomalies. | - |
| `data/archive/cdsco_august_2026_nsq.legacy_local.csv` | Backup of the earlier hand-prepared CSV (hash-verified copy; also in git commit `78cc8d6`). Kept for history only; not used. | `5123e1632708290a0c64b0db1ea4cc3e1bd758fe03b093120528132da05afa15` |
| `data/cdsco_august_2026_nsq_{extraction_log,discrepancy_report,unresolved_items}.md` | Evidence of the official extraction and of the comparison with the legacy CSV. | - |

## Approved transformation (source -> canonical)
1. Drop the `Portal Page` column.
2. Replace every embedded line break (CRLF, CR or LF) inside a cell with **one** ordinary space.
3. Change nothing else: no trimming, case change, punctuation change, or repair of source errors.

Output: UTF-8 without BOM, LF row endings, 10 columns, all values text. Rebuild with
`python scripts/build_dataset.py`; verify with `python scripts/build_dataset.py --check`.
If the source hash or structure checks fail, generation stops and writes nothing.

`.gitattributes` marks `data/**` as non-text so Git never converts line endings (this was a real problem: with `core.autocrlf=true` the committed bytes differed from the files until fixed).

## Runtime validation (fail closed)
`load_dataset()` raises a typed `DatasetError` (never returns partial data) when: manifest or CSV is missing/malformed, SHA-256 differs from the manifest, bytes are not strict UTF-8 or carry a BOM, headers differ, row count differs, a serial is duplicated or non-numeric, product or batch is blank, or a row is outside `AUG-2026`. The pipeline reports these as **system errors**, never "No alert found".

## Verified content facts (re-checked against the official extraction)
- 220 records, serials 1-220, 191 State Lab / 29 CDSCO Labs, all `AUG-2026`, no blank cells, ASCII only.
- All 220 rows are NSQ by construction of the source list; the `NSQ Result` column is free text naming the failed test, not a classifier.
- 12 source cells contained line breaks (serials 53, 72, 73, 74, 75 x2, 80, 129, 131, 132, 135, 155).

## Source anomalies (preserved, never corrected)
| Serial | Anomaly | Handling |
|---|---|---|
| 72 | `Potass um`, `?` in brand | preserved; product matching must tolerate it |
| 152 | `?`, double space, unclosed `(` | preserved |
| 136 | expiry `Jun-2025` before manufacture `Jul-2025` | preserved; surfaced as a source caveat if matched |
| 150, 153 | batch ends with `,` | preserved; comparison key ignores punctuation |
| 121 | batch `0l25038` (lowercase L) | preserved; confusable-aware ambiguity handling |
| 38, 157 | `BKBP02601` vs `BKBP O2601` (zero vs letter O, space); same product and dates | collision test case, see `docs/MATCHING.md` |

The earlier claim that serials 72/152 were "corrected in the audited dataset" is **false**: the official portal itself carries these strings (see the discrepancy report). Whether `?` is a literal character or a lost symbol upstream cannot be determined from the portal.

## Limits
- This is an extraction of one monthly list, not a regulatory database. A negative result never implies safety.
- A server-side character substitution before the portal rendered the page would not be visible to the extraction.
- No page screenshots were saved; evidence is per-page counters and a content hash (see the extraction log).
