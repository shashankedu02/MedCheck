# CDSCO August 2026 NSQ — Extraction Log

Run date: 2026-11-14 (IST)  
Source: https://cdscoonline.gov.in/CDSCO/viewPublicNSQDrug (official CDSCO portal)  
Method: Claude desktop built-in browser, normal page interaction only (no authentication, no CAPTCHA, no protection bypassed).

## Filters applied (direct observation)
| Control | Value selected |
|---|---|
| Tab | NSQ Drugs (not Spurious Drugs) |
| Year | 2026 |
| Month | Aug (option value `Aug-2026`) |
| Reporting source | All |
| Apply Filter | clicked |

Portal then displayed: **"Showing 1 to 10 of 220 entries"**, 10 rows per page, pagination ending at page 22. Every extracted row carries Reporting Month & Year = `AUG-2026` (220/220).

## Completeness checks
| Check | Result |
|---|---|
| Pages visited | **22 of 22** (page 1 → 22 by clicking the portal's own *Next* control, one page at a time) |
| Records extracted | **220** (portal reported 220) |
| Rows per page | 10 on every page; per-page counter strings recorded below |
| Serial numbers | Continuous 1–220, none missing, none repeated, in order |
| Duplicate records | None (no two rows share product + batch + dates + maker + result) |
| Skipped/repeated rows between pages | None — each page's counter ("Showing N to N+9 of 220") advanced exactly 10 and serials matched it |
| Fields per row | 10 on all rows |
| Reporting source split | State Lab 191, CDSCO Labs 29 |

Per-page record (page → portal counter → serial range): p1: 1–10; p2: 11–20; p3: 21–30; p4: 31–40; p5: 41–50; p6: 51–60; p7: 61–70; p8: 71–80; p9: 81–90; p10: 91–100; p11: 101–110; p12: 111–120; p13: 121–130; p14: 131–140; p15: 141–150; p16: 151–160; p17: 161–170; p18: 171–180; p19: 181–190; p20: 191–200; p21: 201–210; p22: 211–220.

## What was captured
All 10 columns the portal displays: S.No, Name of Product, Batch No, Manufacturing Date, Expiry Date, Manufactured By, NSQ Result, Reporting Source, Reporting by Lab/State, Reporting Month & Year. The official CSV adds one column, **Portal Page**, for traceability.

Values were read from each cell's DOM `textContent` and **not trimmed, corrected, standardised or re-typed by any rule**. This preserves double spaces, trailing commas, leading zeros (batch numbers are text), case, punctuation, and **embedded line breaks** (`\n`) inside cells. 12 cells across the dataset contain embedded line breaks. Blank vs unavailable: no cell on the portal was empty; the literal text `NA` appears only inside the product-name string `(Brand Name : NA)`.

## Integrity check on the saved file
The whole 220-row result was fingerprinted inside the browser (DJB2 hash of the JSON of all cell values, 73,995 characters, hash `3572790012`). The values were then transferred into the workspace and re-fingerprinted: **length and hash matched exactly**, so the saved extraction is character-identical to what the portal rendered. The check covers every cell of every row. All characters are 7-bit ASCII.

## Limitations (stated plainly)
1. **No page-level screenshots were saved.** The browser tooling used here does not write screenshot files to disk. Page-level evidence is the recorded per-page counter text, serial ranges, row counts and the content hash above. If you need image evidence, it should be captured separately.
2. Pagination was driven by clicking the portal's *Next* button programmatically (the same button a person would click), with a short wait after each click, rather than by hand-clicking 21 times.
3. The portal's DOM is the authority for "exact value". If the site transforms characters before rendering (e.g. an encoding fallback to `?`), that transformation is not visible from here. See the unresolved-items report (serials 72 and 152).
4. Local CSV was read in read-only mode from a staged copy; the original was not modified. Nothing under `D:\MedCheck` other than the four new files (below) was written.
5. Third-party sites were not used for any value.
