# Dataset Specification

## Supplied CSV
Filename: `cdsco_august_2026_nsq.csv`  
Coverage: reporting month August 2026  
Inspected dimensions: 220 records × 10 columns  
All cells were populated in the inspected copy.

### Exact column headers
1. `Serial Number`
2. `Name of Product`
3. `Batch Number`
4. `Manufacturing Date`
5. `Expiry Date`
6. `Manufactured By`
7. `NSQ Result`
8. `Reporting Source`
9. `Reporting by Lab/State`
10. `Reporting Month and Year`

Treat batch identifiers as strings, not numbers. Preserve leading zeroes, punctuation, spacing, and raw source value. Do not modify the source CSV as a side effect of loading.

## Reported audit observations
- Serial numbers 1–220; no duplicate serial numbers observed.
- No exact duplicate raw batch values observed in the inspected copy.
- Serial 136 has manufacturing date Jul-2025 and expiry Jun-2025 (chronologically suspicious).
- Serials 150 and 153 have trailing commas in batch values.
- Two product-name transcription anomalies (serials 72 and 152) were reportedly corrected in the audited dataset.
- The accompanying audit report states 22 pages inspected, 220/220 records, 2,200/2,200 fields compared, and zero unresolved items. These are claims made by that report, not independently re-performed regulatory verification.

## Required runtime validation (proposed)
At startup, validate file existence, UTF-8/encoding handling, exact required headers, row count expectations for this frozen snapshot, non-empty critical fields, and a pinned SHA-256 digest. A mismatch must fail closed and show a system verification error, never `No alert found`.

Do not hardcode a hash until the final approved CSV file is frozen and its digest is computed. Record filename, SHA-256, acquisition/source details, audit version, and validation date in a dataset manifest.

## Data-quality handling
- Preserve anomalous source values and surface them as source-data caveats.
- Do not silently “repair” the manufacturing/expiry inversion or trailing punctuation.
- If a source anomaly affects identity resolution, abstain and explain.
- Do not assume unique batch numbers will remain unique in future datasets.
