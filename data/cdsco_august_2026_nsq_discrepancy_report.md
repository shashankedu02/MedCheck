# CDSCO August 2026 NSQ — Discrepancy Report (official portal vs local CSV)

Run date: 2026-11-14  
Official: `cdsco_august_2026_nsq_official_extraction.csv` (220 records, 22 pages)  
Local (read-only): `D:\MedCheck\data\cdsco_august_2026_nsq.csv` (220 data rows, UTF-8 with BOM, 10 columns)

## Summary
| Metric | Count |
|---|---|
| Total records extracted (official) | **220** |
| Total pages visited | **22** |
| Records in local CSV | 220 (serials 1–220, all present, none extra) |
| Records identical on all 10 fields (exact string match) | **209** |
| Records with ≥1 discrepancy | **11** (serials 53, 72, 73, 74, 75, 80, 129, 131, 132, 135, 155) |
| Field-level discrepancies | **12** |
| Records with items I could not confidently interpret | **4** (serials 72, 121, 136, 152) — see unresolved-items report |

**Headline finding:** every one of the 12 differences is about **line breaks inside a cell**. The portal's cell text contains embedded newlines; the local CSV has them flattened. No product name, batch number, date, result, source or lab differs in substance. 7 of the 12 are whitespace-only (a newline became a space, or was dropped). 5 are different in kind: the local file shows **punctuation that is not on the portal** (`, ` or `. ` where the portal has a bare line break), which means the earlier extraction or cleanup inserted characters.

## Your five previously identified anomalies
All five are **present on the official portal exactly as in your local CSV**. None is a local-extraction error.

| Serial | Anomaly | Official portal | Local CSV | Verdict |
|---|---|---|---|---|
| 72 | `Potass um` | `Diclofenac Potass um & Serratiopeptidase Tablets (Brand Name : Wyser?M.K)` (internal space present) | identical in Product Name | Source typo, faithfully preserved. Do not correct. (Serial 72 does have a separate line-break difference in *Manufactured By*, below.) |
| 152 | `MOXIPILTM ? CV625` | `…(MOXIPILTM  ? CV625 (Brand Name : NA)` (two spaces before `?`, `?` is ASCII 0x3F, no closing parenthesis) | identical | Faithful. Whether `?` is a literal question mark or a lost symbol (e.g. ®/™ separator) cannot be told from the portal — unresolved. |
| 136 | Mfg/expiry inversion | Mfg `Jul-2025`, Expiry `Jun-2025` | identical | Faithful. It is the only record in the 220 where expiry precedes manufacture (and it is already expired as of Aug-2026). Which date is wrong is unknowable from the portal — unresolved. |
| 150 | Trailing comma in batch | `GTF2327C,` | identical | Faithful. |
| 153 | Trailing comma in batch | `GBT26241,` | identical | Faithful. |
| 121 | Batch `0l25038` | Characters: `0`(0x30) `l`(0x6C, lowercase L) `2 5 0 3 8` | identical | Faithful. The portal serves a lowercase **l**, not `I` or `1`. What the manufacturer intended (`0I25038` / `0125038`) cannot be established from the portal — unresolved as to intent. |

## All field-level discrepancies
Notation: `⟦…⟧` marks the differing characters; `\n` is a line-feed. Portal page is from the portal's own pagination.

| Serial (local / official) | Field | Official value (excerpt at the change) | Local value (excerpt at the change) | Difference | Page | Recommendation | Confidence |
|---|---|---|---|---|---|---|---|
| 53 / 53 | Manufactured By | `…t. Ltd., E-2, Sara⟦\n ⟧ Industrial Estate…` | `…t. Ltd., E-2, Sara⟦⟧ Industrial Estate…` | whitespace-only (line break → space/none); 1 position | 6 | Correction is a policy choice, not an error fix: local text reads identically once whitespace is collapsed. Justified only if the production CSV is meant to preserve portal text byte-for-byte. | High (difference) / Medium (what to do) |
| 72 / 72 | Manufactured By | `…an Pharmaceuticals⟦\n⟧Plot No. 1018, Ker…`<br>`… No. 1018, Kerala,⟦\n⟧G.I.D.C., Bavla, D…` | `…an Pharmaceuticals⟦, ⟧Plot No. 1018, Ker…`<br>`… No. 1018, Kerala,⟦ ⟧G.I.D.C., Bavla, D…` | line break replaced by punctuation not present on portal; 2 positions | 8 | Correction appears justified if the goal is verbatim fidelity: local contains characters that do not exist in the official value. If the goal is a clean single-line display value, keep flattened text but without invented punctuation. | High |
| 73 / 73 | Manufactured By | `…eycross Healthcare⟦\n⟧Vill. Jolan Kalan,…`<br>`…, Distt. SAS Nagar⟦\n⟧(PB).…` | `…eycross Healthcare⟦, ⟧Vill. Jolan Kalan,…`<br>`…, Distt. SAS Nagar⟦ ⟧(PB).…` | line break replaced by punctuation not present on portal; 2 positions | 8 | Correction appears justified if the goal is verbatim fidelity: local contains characters that do not exist in the official value. If the goal is a clean single-line display value, keep flattened text but without invented punctuation. | High |
| 74 / 74 | Manufactured By | `…Vrindavan Global⟦\n⟧Plot No. 23-B & C,…`<br>`…Lodhimajra, Baddi,⟦\n⟧Distt. Solan (H.P)…` | `…Vrindavan Global⟦, ⟧Plot No. 23-B & C,…`<br>`…Lodhimajra, Baddi,⟦ ⟧Distt. Solan (H.P)…` | line break replaced by punctuation not present on portal; 2 positions | 8 | Correction appears justified if the goal is verbatim fidelity: local contains characters that do not exist in the official value. If the goal is a clean single-line display value, keep flattened text but without invented punctuation. | High |
| 75 / 75 | Manufactured By | `… Pvt Ltd (Unit-II)⟦\n⟧HS No 211, K. No.7…` | `… Pvt Ltd (Unit-II)⟦, ⟧HS No 211, K. No.7…` | line break replaced by punctuation not present on portal; 1 position | 8 | Correction appears justified if the goal is verbatim fidelity: local contains characters that do not exist in the official value. If the goal is a clean single-line display value, keep flattened text but without invented punctuation. | High |
| 75 / 75 | NSQ Result | `…osmetics Act, 1940⟦\n⟧and Rules there un…` | `…osmetics Act, 1940⟦ ⟧and Rules there un…` | whitespace-only (line break → space/none); 1 position | 8 | Correction is a policy choice, not an error fix: local text reads identically once whitespace is collapsed. Justified only if the production CSV is meant to preserve portal text byte-for-byte. | High (difference) / Medium (what to do) |
| 80 / 80 | Name of Product | `…Rabeprazole ⟦\n⟧Gastro-resistant T…` | `…Rabeprazole ⟦⟧Gastro-resistant T…` | whitespace-only (line break → space/none); 1 position | 8 | Correction is a policy choice, not an error fix: local text reads identically once whitespace is collapsed. Justified only if the production CSV is meant to preserve portal text byte-for-byte. | High (difference) / Medium (what to do) |
| 129 / 129 | NSQ Result | `…tronidazole in the⟦\n⟧Sample is less (i.…`<br>`…of stated Amount).⟦\n⟧2. The Sample does…`<br>(+4 more changes of the same kind) | `…tronidazole in the⟦ ⟧Sample is less (i.…`<br>`…of stated Amount).⟦ ⟧2. The Sample does…`<br>(+4 more) | whitespace-only (line break → space/none); 6 positions | 13 | Correction is a policy choice, not an error fix: local text reads identically once whitespace is collapsed. Justified only if the production CSV is meant to preserve portal text byte-for-byte. | High (difference) / Medium (what to do) |
| 131 / 131 | NSQ Result | `…of stated Amount).⟦\n⟧2.The Sample does …`<br>`… Dissolution Test.⟦\n⟧The Sample is decl…`<br>(+1 more changes of the same kind) | `…of stated Amount).⟦ ⟧2.The Sample does …`<br>`… Dissolution Test.⟦ ⟧The Sample is decl…`<br>(+1 more) | whitespace-only (line break → space/none); 3 positions | 14 | Correction is a policy choice, not an error fix: local text reads identically once whitespace is collapsed. Justified only if the production CSV is meant to preserve portal text byte-for-byte. | High (difference) / Medium (what to do) |
| 132 / 132 | NSQ Result | `…the Sample is less⟦\n⟧(i.e.62.36% of sta…`<br>`…an the I.P. Limit.⟦\n⟧(I.P. Limit- Not l…`<br>(+1 more changes of the same kind) | `…the Sample is less⟦ ⟧(i.e.62.36% of sta…`<br>`…an the I.P. Limit.⟦ ⟧(I.P. Limit- Not l…`<br>(+1 more) | whitespace-only (line break → space/none); 3 positions | 14 | Correction is a policy choice, not an error fix: local text reads identically once whitespace is collapsed. Justified only if the production CSV is meant to preserve portal text byte-for-byte. | High (difference) / Medium (what to do) |
| 135 / 135 | NSQ Result | `…zole Sodium in the⟦\n⟧Sample is less (i.…` | `…zole Sodium in the⟦ ⟧Sample is less (i.…` | whitespace-only (line break → space/none); 1 position | 14 | Correction is a policy choice, not an error fix: local text reads identically once whitespace is collapsed. Justified only if the production CSV is meant to preserve portal text byte-for-byte. | High (difference) / Medium (what to do) |
| 155 / 155 | Manufactured By | `…adun (U.K.)-248197⟦\n⟧Marketed by : CLAN…` | `…adun (U.K.)-248197⟦. ⟧Marketed by : CLAN…` | line break replaced by punctuation not present on portal; 1 position | 16 | Correction appears justified if the goal is verbatim fidelity: local contains characters that do not exist in the official value. If the goal is a clean single-line display value, keep flattened text but without invented punctuation. | High |

## Grouping
**Line break replaced by punctuation not on the portal (5 cells):** serials 72, 73, 74, 75, 155 (all *Manufactured By*). In 72, 73, 74, 75 the local value has `, ` where the portal has `\n`; serial 155 has `. ` (so the local text reads "…Dehradun (U.K.)-248197. Marketed by : …" where the portal has a break with no full stop). These are the only cases where the local file contains text the official source does not.

**Whitespace-only (7 cells):** 53 (Manufactured By), 75 (NSQ Result), 80 (Name of Product), 129 (NSQ Result), 131 (NSQ Result), 132 (NSQ Result), 135 (NSQ Result).

## Fully-compared coverage
All 220 serials × 10 fields (2,200 cells) were compared by exact string equality (after decoding the CSV; BOM ignored). Matching was by serial number; every serial exists on both sides and product, batch, dates, source and lab agree on all 220 rows. Of 2,200 cells, 12 differ.

## Direct observations vs assumptions
- *Observed:* official strings (including newlines), page numbers, counts, hash match, the character codes quoted above, the local file's content.
- *Assumption:* that the local file's flattening was applied by an earlier extraction/cleanup step rather than the portal having served different text earlier. The portal could have changed since your first extraction; I cannot tell from here.
- *Not decided here:* whether production data should keep embedded newlines. That is your call and affects CSV consumers.

## Recommendation (no changes made)
1. Pick a newline policy for the dataset (preserve `\n`, or replace with a single space). Either is defensible; the current local file mixes several treatments (single space, nothing, `, `, `. `) and is not consistent.
2. If you choose to match the portal, the 12 cells above are the complete list.
3. Do **not** correct serials 72, 121, 136, 150, 152, 153 — the official source carries those values.

*No corrected production CSV, project doc or code was created or changed. Awaiting your approval.*
