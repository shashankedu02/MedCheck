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
| `tests/test_evaluation.py` | Metric arithmetic on made-up rows, abstentions in denominators, results awaiting confirmation as their own category (potential misses on listed packs), CLI behaviour |
| `tests/test_demo.py` | Every synthetic fixture gives its documented result through the real OCR, carries a legible in-frame "TEST FIXTURE" banner and is listed as synthetic; the fixture check writes only its own labelled folder |
| `tests/test_alert_check.py` | Every alert carries the pack check (batch, product, strength, manufacturer) without delay; listed neighbours named; known exposures pinned (sibling misread, conflicting manufacturer) |
| `tests/test_docs.py` | Relative links in live documentation resolve |
| `tests/test_v2_parser_and_misreads.py` | Glue-aware parser (`5BA1617MFD`, `...146M.R`), label words never a batch, value on next line, raw strings preserved, sentence-fragment/garbage guards (`30 deg C. Protect`), every listed batch passes the guards, the investigation's known wrong readings (`HLAS50019`, `5BA13A7`, `INA26083`, `18261604K8`...) abstain against a dataset listing the true batch, strict agreement and provenance, edge-cut lines ignored, engine scores never read by decision code |
| `tests/test_v2_pipeline.py` | Scripted-engine cascade rules (rotations only when no label found, one bounded confirmation pass, no retries on conflict), provenance, consistent misreads and conflicts never give `No alert found`, engine failure/fallback/system-error semantics, real RapidOCR with the network blocked, model hash pinning and fail-closed tampering, edge-touching line flagged |
| `tests/test_v2_manual_entry.py` | Typed/corrected/confirmed batch provenance, typed text never OCR evidence or corroboration, confirmation required for typed clean negatives, near-neighbour and 38/157 collision still abstain, `Expired` never, input validation, no logging, pack-region detection |
| (V2 review additions) | Look-alike conflict explanations, dropped-F date label and strength-is-not-a-date guards, glued-month cut, `JUN25`/`MfgDt:` layouts (`test_v2_parser_and_misreads.py`); bounded ONNX threads applied and restored, identical text, warm-up never raises, Tesseract concurrent with identical evidence and full-variant fallback (`test_v2_pipeline.py`); stale-module restart message, confirmation cleared on edit (`test_app.py`) |
| `tests/test_look_alike_consistent_misread.py`, D-026 additions in `test_decision.py`, `test_app.py`, `test_pipeline.py`, `test_v2_pipeline.py`, `test_demo.py`, `test_real_eval.py` | The reported case (both engines read `HLA50019`): matching abstains when the true batch is listed, and an OCR-read clean negative needs confirmation otherwise; correction goes through the same rules; every batch source (OCR, corrected, typed) needs confirmation for `No alert found` and `Expired`; `Alert found` is never delayed; confirmation changes nothing else; exhaustive grid never yields a clean negative unconfirmed; UI wording ("agreed by the OCR passes", what confirmation does not mean); headline asserted strictly (not the page disclaimer); evaluation scores a withheld negative as Inconclusive |
| `tests/test_real_eval.py` | Evaluation records, held-out photographs never opened by default, batch scoring against the independent reference, run history, ground-truth handling |

## Honest scope
- OCR tests use **synthetic rendered text**. They prove the plumbing and the safety logic, not accuracy on photographs of curved foil, glare or blur. Real-world accuracy is unknown until `docs/EVALUATION.md` is executed.
- Real-photo categories still untested: blur, glare, rotation beyond EXIF, perspective, curved blister, tiny print, multi-pack scenes.
- Tests that need Tesseract or a TrueType font skip (not pass) when those are missing.

## Rules for new tests
No hard-coded results to satisfy a test; add a negative or boundary case with every positive case; a bug found by a test gets a regression test; never weaken an assertion to make a test pass without recording why in `docs/DECISIONS.md`.
