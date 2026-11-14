# Testing Guidelines (authoritative)

Run everything: `.\.venv\Scripts\python.exe -m pytest -q` (about a minute; the Streamlit UI tests are the slow part). Report only results of runs you actually performed.

## What each test file covers
| File | Covers |
|---|---|
| `tests/test_dataset.py` | Transformation (line breaks, column drop), byte-exact reproducibility, independent cell-by-cell check against the official extraction, pinned source hash, fail-closed loader (missing file/manifest, tampering, header drift, BOM, truncation, wrong period), build script refusing an untrusted source |
| `tests/test_normalization_dates.py` | Batch keys (leading zeros, punctuation, no confusable substitution, idempotence), supported/rejected date formats, `Expired` never emitted while policy unapproved, approved-policy boundaries (tested but disabled) |
| `tests/test_decision.py` | Truth table, system failure precedence, exhaustive grid over all input combinations, wording guard against safe/genuine/authentic claims |
| `tests/test_matching.py` | Product parsing, corroboration, strength/form conflicts, serials 38/157 collision both directions, trailing-comma and lowercase-L batches, short-batch rule, dataset-wide properties (every row confirms with full text except the known collisions; no row confirms on batch alone or with the wrong product) |
| `tests/test_image_input.py` | Valid formats, corrupt/zero-byte/oversize/too-many-pixels/too-small/animated/unsupported files, EXIF rotation, downscale, no files written |
| `tests/test_extraction.py` | Label formats, raw preservation, implausible values, Mfg/Exp not swapped or confused with "Mfd. by", cross-pass reconciliation, round trip of every dataset batch (documented exception: 2-character batches) |
| `tests/test_ocr_preprocessing.py` | Variant determinism/bounds, TSV parsing, missing-engine and timeout errors, real Tesseract on synthetic labels |
| `tests/test_pipeline.py` | End to end with real OCR: all four outcomes, each system-failure type, rejection, privacy (no files, no logged OCR text), internal-error non-leakage |
| `tests/test_app.py` | Streamlit AppTest: scope/period text, rendering of every outcome, neutral (never green) no-alert, forbidden-claim scan of the page, plain-text rendering of OCR content, real upload and camera flows, config (localhost, no telemetry) |
| `tests/test_evaluation.py` | Metric arithmetic on made-up rows, abstentions in denominators, CLI behaviour |
| `tests/test_demo.py` | Every README demo image gives its documented headline |
| `tests/test_docs.py` | Relative links in live documentation resolve |

## Honest scope
- OCR tests use **synthetic rendered text**. They prove the plumbing and the safety logic, not accuracy on photographs of curved foil, glare or blur. Real-world accuracy is unknown until `docs/EVALUATION.md` is executed.
- Real-photo categories still untested: blur, glare, rotation beyond EXIF, perspective, curved blister, tiny print, multi-pack scenes.
- Tests that need Tesseract or a TrueType font skip (not pass) when those are missing.

## Rules for new tests
No hard-coded results to satisfy a test; add a negative or boundary case with every positive case; a bug found by a test gets a regression test; never weaken an assertion to make a test pass without recording why in `docs/DECISIONS.md`.
