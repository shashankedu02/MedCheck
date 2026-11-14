# CDSCO August 2026 NSQ — Unresolved Items

Run date: 2026-11-14. These are items where the official value was captured exactly, but its meaning or intended value cannot be confidently established from the official portal alone. No third-party source was consulted. None is a record that failed to load: **0 records were inaccessible**, all 220 extracted.

| # | Serial | Page | Field | Official value | What is unresolved | Confidence in capture |
|---|---|---|---|---|---|---|
| 1 | 72 | 8 | Name of Product | `Diclofenac Potass um & Serratiopeptidase Tablets (Brand Name : Wyser?M.K)` | (a) `Potass um` is a space inside "Potassium" — a typo in the source, high-confidence reading of the intent but not ours to apply. (b) `?` between `Wyser` and `M.K`: is it a literal question mark in the source or a symbol lost by an encoding step upstream? | High that the portal serves ASCII `?` (0x3F); low on what the source intended |
| 2 | 152 | 16 | Name of Product | `Amoxycillin & Potassium Clavulanate Tablets IP (MOXIPILTM  ? CV625 (Brand Name : NA)` | Same `?` question; also two spaces before `?` and an unclosed `(`. Looks like a ™/® or dash that was replaced, but the portal does not say. | High / low |
| 3 | 136 | 14 | Manufacturing Date / Expiry Date | Mfg `Jul-2025`, Exp `Jun-2025` | Expiry is one month before manufacture. Either date may be a source typo (e.g. expiry `Jun-2027`/`Jun-2028`), or the two were swapped; the portal's NSQ Result text for this serial says the Mfg. date is not mentioned on the sample blisters, which does not explain or resolve the inverted dates. The record is also already past expiry at the Aug-2026 report month. | High / unknown intent |
| 4 | 121 | 13 | Batch Number | `0l25038` | Second character is lowercase `l` (0x6C). Intended character could be `I`, `1` or `l`; cannot be determined. The portal did not alter it. | High / unknown intent |

## Verified as official, no interpretation needed (kept for completeness)
- **Serial 150** batch `GTF2327C,` and **serial 153** batch `GBT26241,`: trailing comma exists on the portal. Preserve as-is unless you decide to normalise (a normalisation decision, not a verification gap).

## Extraction-level limits that affect confidence
- No page screenshots saved (see extraction log); evidence is counters + content hash.
- A character substitution that happens on the server before the page is built would be invisible to this extraction.

## Counts
Unresolved records: **4** (serials 72, 121, 136, 152). Inaccessible records: **0**.
