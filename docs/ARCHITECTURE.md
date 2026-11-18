# Architecture (authoritative baseline)

**Baseline:** committed code at `f24770f` (M16) on branch `ui-redesign`. This is the best current implementation. `master` is still at `ad8c68f` (M13) and does not contain the 3D interface, the redesigned result screen or the clickable batch readings (M14-M16); `ui-redesign` is not merged because the physical rehearsal on the demo laptop is pending.

**Evidence for this document:** the committed code and Git history, a read of every module under `medcheck/`, `medcheck_ui/`, `app.py` and `scripts/`, a run of `scripts/build_dataset.py --check` (OK) and a full `pytest -q` run (443 passed). Nothing here is claimed from the earlier plan alone. Where a statement rests only on reading code, or only on a manual browser run, the status column says so.

**Status key**
| Status | Meaning |
|---|---|
| **Implemented + tested** | Code exists and automated tests (named in section 9) exercise it. |
| **Implemented, manually verified** | Code exists; the evidence is a manual or scripted browser run recorded in `BUILD_PROGRESS.md`, not a repeatable test. |
| **Implemented, unverified** | Code exists; no test or recorded run demonstrates the behaviour. |
| **Not implemented** | Planned or discussed only. |

Nothing in this file is an accuracy, speed or reliability claim. Real-photograph accuracy has not been evaluated (D-014 is OPEN); see section 11.

---

## 1. What the system is
A local-first Streamlit application. A user supplies one photo of a medicine strip or box. Local OCR reads the batch number (and, as secondary fields, expiry and manufacturing dates). The batch is matched against the immutable CDSCO August 2026 NSQ list (220 records) and a deterministic engine returns one of four statuses (`Alert found`, `No alert found`, `Expired`, `Unable to verify`) or, separately, a system error. It is a lookup aid, not an authenticity, safety or quality test.

```
                          PRESENTATION  (app.py, medcheck_ui/)                 no matching rules live here
  photo (upload / camera)  ->  status banner, reading cards, record, batch form + clickable readings, notes
        |                          ^                                  ^
        | bytes                    | ScanResult                       | phase + status name only
        v                          |                                  v
  ORCHESTRATION  medcheck/pipeline.py  MedCheckPipeline          3D stage (Three.js, decorative)
   check(bytes)      verify_manual(prior, text, confirmed)
        |
        |-- image_input   validate + decode in memory (size, format by content, pixels, EXIF, downscale)
        |-- regions       pack-region crop (extra view only)
        |-- OCR cascade   RapidOCR full frame + crop  ||  Tesseract on the crop (2 variants x 2 page modes, concurrent)
        |                 [no batch label found -> RapidOCR on the crop rotated 90/180/270]
        |                 [exactly one reading with single-pass support -> ONE confirmation pass at another scale]
        |-- extraction    label-anchored batch / expiry / mfg; strict cross-pass agreement; provenance
        |-- matching      batch-led match against the indexed dataset  (retrieval + corroboration)
        |-- dates         expiry assessment (verdict disabled: D-007 OPEN)
        '-- decision      four statuses + confirmation gate (D-026) + alert action check (D-027)
        ^
  DATASET  dataset.py  fail-closed loader, SHA-256 pinned, manifest        EVALUATION  evaluation.py, real_eval.py, scripts/
```
A typed or corrected batch re-enters at `verify_manual` and goes through the **same** matching and decision code (marked by `BatchSource`).

## 2. Modules and their state
| Module | Role | Status |
|---|---|---|
| `medcheck/config.py` | Every path, limit and threshold (UNCALIBRATED ones labelled), expiry-policy flag (`EXPIRY_POLICY_APPROVED = False`), pinned source and model hashes | Implemented + tested |
| `medcheck/dataset.py`, `scripts/build_dataset.py` | Canonical dataset build (drop `Portal Page`, line breaks to one space, nothing else); fail-closed loader (missing / schema / integrity -> `DatasetError`); manifest | Implemented + tested (`test_dataset.py`) |
| `medcheck/models.py` | Typed contracts: `Status`, `BatchSource`, `FieldState`, `MatchOutcome`, `SystemFailure`, `Decision`, `ManualEntry` | Implemented + tested |
| `medcheck/normalization.py` | Comparison keys (NFKC, upper-case, letters and digits only); `confusable_key` folds O/0, I/1, L/1, S/5, B/8 **for ambiguity detection only** | Implemented + tested |
| `medcheck/dates.py` | Month/year parsing; expiry assessment (`UNDETERMINED` while the policy flag is off); manufacture-after-expiry anomaly | Implemented + tested |
| `medcheck/product.py`, `matching.py` | Product-name parsing and identity scoring (brand, active ingredient, strength, form, manufacturer); `DatasetIndex`; `match_batch`; listed-neighbour warning | Implemented + tested |
| `medcheck/decision.py` | Pure four-status engine, confirmation gate, provenance wording, alert action check | Implemented + tested |
| `medcheck/image_input.py` | In-memory validation and decode; EXIF orientation; downscale to 3000 px long side | Implemented + tested |
| `medcheck/preprocessing.py` | Up to 4 deterministic variants (grayscale, CLAHE, Otsu, adaptive); used for Tesseract | Implemented + tested |
| `medcheck/ocr.py` | Tesseract adapter: executable called directly, image on stdin, TSV parsed, per-call timeout and total budget; `OCRPass` provenance | Implemented + tested |
| `medcheck/ocr_rapid.py` | RapidOCR adapter: models verified by SHA-256 before load, offline, ONNX threads bounded (4), warm-up, generic errors, edge-touching lines flagged | Implemented + tested |
| `medcheck/regions.py` | Pack-region detection by local gradient energy (geometry only, no ML); crop is an extra view, never a replacement | Implemented + tested (`test_v2_manual_entry.py`) |
| `medcheck/extraction.py` | Glue-aware, label-anchored batch/Exp/Mfg parser with garbage guards; `reconcile_batch` (strict agreement, minimum 2 supporting passes, any conflicting reading makes the field AMBIGUOUS) | Implemented + tested |
| `medcheck/pipeline.py` | Orchestration, cascade, manual verification, failure taxonomy | Implemented + tested |
| `medcheck/evaluation.py`, `medcheck/real_eval.py`, `scripts/evaluate.py`, `run_evaluation.py`, `run_fixture_check.py`, `run_heldout_evaluation.py`, `set_ground_truth.py`, `make_demo_images.py` | Metric arithmetic (abstentions stay in denominators), real-photo run records (photos and results git-ignored), synthetic fixtures with a separate fixture check, one-time held-out run (spent) | Implemented + tested: the library code, and the scripts `evaluate.py` (subprocess), `run_evaluation.py`, `run_fixture_check.py`, `make_demo_images.py` and `build_dataset.py` are run by tests. `set_ground_truth.py` and `run_heldout_evaluation.py` (a one-time script, spent) have no direct test |
| `app.py` | Entry point: cached pipeline (dataset + index + warmed OCR), upload/camera, check button, result, batch form, clickable readings, plain-text technical expander; fallbacks | Implemented + tested (`test_app.py`, `test_alert_check.py`, `test_batch_suggestions.py`) |
| `medcheck_ui/result.py` | Pure functions: `ScanResult` -> escaped HTML (banner, cards, record, notes, steps, suggestions intro) and the result CSS. Presentation only | Implemented + tested (`test_ui_result.py`); layout seen in a browser by the owner |
| `medcheck_ui/theme.py`, `scene.py`, `__init__.py` | Story copy, theme CSS, Components V2 mount, closed payload (`phase`, `status`), `plain_ui()` switch (`MEDCHECK_PLAIN_UI=1`) | Implemented + tested for payload privacy, contrast, no remote URLs (`test_ui_scene.py`, `test_ui_scene_story.py`) |
| `medcheck_ui/assets/stages.js`, `scene.js` | One persistent Three.js scene, master clock from scroll, five scenes, scan phase bound to the real OCR call, WebGL / reduced-motion / lite fallbacks | **Implemented, manually verified** (headless Edge runs recorded in `BUILD_PROGRESS.md` M15; the owner's browser checks). No automated test executes this JavaScript. |
| `static/vendor/three/` | Three.js 0.170.0 (MIT), SHA-256 pinned in `VENDOR.json`, stored byte-for-byte, served by Streamlit static serving | Implemented + tested (hash and "no remote URL" scans) |

## 3. Runtime flow
### 3.1 Check a photo (`MedCheckPipeline.check`)
1. If the dataset failed to load at start: `ScanResult` with a **system error** (never a status).
2. `load_image`: rejects empty, over 10 MB, unsupported format (by content), animated, over 40 M pixels, under 300 px, corrupt. Rejection is a `ScanResult.rejection`, not a verification result.
3. Pack-region detection (optional). **Views:** RapidOCR on the full frame and on the crop (if no region was found, the second view is the full frame upscaled 1.3x). **Tesseract** runs concurrently in a worker thread on the crop (or full frame), 2 preprocessing variants x page modes 6 and 11 = 4 passes; if RapidOCR is unavailable Tesseract runs all variants.
4. `extract(passes)`: per pass, label-anchored fields; lines touching the image/crop edge are blanked for extraction; then `reconcile_batch`: all candidate keys across passes must be the same key and at least 2 passes must have found it, else AMBIGUOUS (or NOT_FOUND when none).
5. If the batch is NOT_FOUND and RapidOCR is available: RapidOCR on the crop (or full frame) rotated 90, 180, 270 degrees (stops at the time budget). AMBIGUOUS readings are never retried until they agree.
6. If exactly one distinct reading exists with single-pass support: one extra RapidOCR pass of the same view at 1.3x; strict agreement still applies afterwards.
7. If the batch is READ: `match_batch`. Then `assess_expiry` (verdict never `EXPIRED` while the policy flag is off) and `decide`.
8. Any unexpected exception in `check` becomes the internal system error (no content logged).

### 3.2 Matching (`match_batch`, `docs/MATCHING.md`)
Exact comparison key is the only route to `CONFIRMED`; it additionally needs product identity evidence (brand, or all active-ingredient words; short keys under 6 characters need two independent signals) and no strength/form conflict. A confusable-equivalent rival row or several exact rows is `COLLISION`; near keys (confusable-equivalent, or edit distance up to 2 for keys of 6+ characters) are `FUZZY_ONLY`; both force `Unable to verify`. Serials 38 and 157 are the required collision pair. Product text is the OCR text of the whole photo. A user-typed value is never corroboration.

**Look-alike folding** (`normalization.confusable_key`: O->0, I->1, L->1, S->5, B->8) is read in exactly two places in `matching.py` and once for explanation text. (1) When the exact key matches one row, a *different* row with the same folded key turns the would-be alert into `COLLISION`. (2) When no exact row exists, rows with the same folded key are retrieved as `FUZZY_ONLY`. Both only add abstention. An alert needs the exact `key`, in which L and 1 stay different, and raw strings are never altered, so the fold never produces a match, an alert or a clean negative (checked against the real index in this baseline; serial 121 is pinned by `test_matching.py`). The letter L extends the four owner-confirmed pairs of D-005; it is motivated by serial 121, published as `0l25038` with an undeterminable intended character. Details: `docs/MATCHING.md`, D-005.

### 3.3 Decision and confirmation (`decision.decide`, D-026, D-027)
Precedence: system failure -> batch not read cleanly -> match outcome -> (no match) expiry verdict. A clean negative (`No alert found` or `Expired`) for **any** batch string (OCR-read, corrected or typed) is withheld as `Unable to verify` (`ocr_batch_unconfirmed` / `manual_entry_unconfirmed`) until the user has ticked that they compared it with the pack. `Alert found` is never delayed and always carries `action_check` (compare batch character by character, product, strength, manufacturer). Every decision records `batch_source`, `batch_as_read` and `batch_confirmed`. After a corrected or typed batch the explanation says "the batch you entered" (M16).

### 3.4 Manual correction (`verify_manual`, D-024, D-032)
The user can pick one of the OCR's readings (button, exact string, tick cleared, never submitted or confirmed by the click), edit it, or type one. `verify_manual` validates it (3-30 printable characters, a digit), computes the source (`ocr` if it equals the OCR-read key, `user_corrected` if OCR had readings, else `user_entered`), runs the same `match_batch` against the prior photo's text, and returns the prior result with the new decision. `prior.extraction` is never altered. The returned result also carries `photo_result`, the ORIGINAL photo result (also after repeated manual entries); when that was `Alert found` and the user's batch differs from the OCR reading, `ScanResult.preserved_photo_alert` exposes it and both renderers keep showing it (banner, action check, matched record) above the user's own result, with one wording (`preserved_photo_alert_text`) saying that the user's result does not cancel or disprove the photo's alert (audit AU-1).

### 3.5 Presentation
`main()` loads the cached pipeline, then (unless `MEDCHECK_PLAIN_UI` is set) mounts the story and the 3D stage, then the tool. The stage receives only `{phase: idle|scanning|result, status: alert|unable|no_alert|error|null}`; the scan phase is set around the real `pipeline.check` call. The result is rendered by `medcheck_ui.result` (`st.html`, every dynamic value escaped); the recognised text appears only as plain text in an expander. The basic native rendering remains as the fallback if `medcheck_ui.result` cannot import.

## 4. Safety invariants and where they are enforced
| Invariant | Enforced in | Tests |
|---|---|---|
| Only four statuses; system failures are a separate result type | `models.py`, `decision.py`, `pipeline.py` | `test_decision.py` (exhaustive grid), `test_pipeline.py`, `test_app.py` |
| Batch is primary evidence; product similarity alone never alerts; fuzzy only abstains | `matching.py` | `test_matching.py` (dataset-wide properties) |
| No silent substitution of look-alike characters (owner-confirmed pairs O/0, I/1, S/5, B/8; the ambiguity fold also treats L as 1, see 3.2 and OA-11); 38/157 abstain both ways | `normalization.py`, `matching.py` | `test_normalization_dates.py`, `test_matching.py`, `test_look_alike_consistent_misread.py` |
| Disagreeing or single-pass readings abstain | `extraction.reconcile_batch` | `test_extraction.py`, `test_v2_parser_and_misreads.py`, `test_v2_pipeline.py` |
| Raw strings preserved; engine scores never read by decision code | `extraction.py`, `ocr*.py`, `decision.py` | `test_v2_parser_and_misreads.py` |
| Dataset failure is a system error, never "No alert found" | `dataset.py`, `pipeline.py` | `test_dataset.py`, `test_pipeline.py` |
| `Expired` never emitted while D-007 is OPEN | `config.EXPIRY_POLICY_APPROVED`, `dates.py` | `test_normalization_dates.py`, `test_decision.py`, `test_v2_manual_entry.py` |
| No clean negative before the user's confirmation; alerts never delayed | `decision.py` | `test_decision.py`, `test_app.py`, `test_pipeline.py`, `test_v2_pipeline.py` |
| A user's batch is never OCR evidence or corroboration | `pipeline.verify_manual`, `decision.py` | `test_v2_manual_entry.py` |
| Never claim safe / genuine / authentic / defect-free | `decision.py` wording, `theme.py`, `result.py` | `test_decision.py`, `test_app.py` (page scan), `test_ui_result.py`, `test_ui_scene_story.py` |
| No image persistence, no logging of image bytes, OCR text or typed batches, no network, localhost only, telemetry off | `image_input.py`, `ocr*.py`, `config.toml`, adapters | `test_image_input.py`, `test_pipeline.py`, `test_v2_pipeline.py` (network blocked), `test_v2_manual_entry.py`, `test_app.py` (config), `test_ui_scene.py` |
| The browser stage never receives a photo, text, batch or record | `scene.py` (`ALLOWED_FIELDS`) | `test_ui_scene.py` |

## 5. Configuration (`medcheck/config.py`; thresholds are UNCALIBRATED engineering defaults)
Image: 10 MB, 40 M pixels, min side 300, working long side 3000. OCR: Tesseract per-call timeout 25 s, total budget 60 s, page modes (6, 11), up to 4 variants (2 used as extra evidence), RapidOCR rotations (90, 180, 270), crop upscale 1.3, ONNX intra-op threads 4, Tesseract concurrent. Extraction/matching: minimum agreeing passes 2, minimum batch key length 3, maximum letter run 5, allowed batch characters `A-Za-z0-9 -/.,`, edge margin 1.2 percent (min 6 px), short-batch threshold 6, brand score 90, ingredient score 88, fuzzy distance 2. Manual batch: max 30 characters. Streamlit (`.streamlit/config.toml`): localhost, headless, 10 MB upload, XSRF on, telemetry off, static serving on, dark theme.

## 6. Failure taxonomy and fallbacks
| Condition | Behaviour |
|---|---|
| Dataset missing / schema / integrity failure | System error; checks disabled; never a status |
| Upload unusable | Friendly rejection (`ImageRejected`), no result |
| RapidOCR missing / model hash mismatch / fails | Note shown; Tesseract only (all variants); engine stays disabled for the rest of the process (see OA-1) |
| Tesseract missing / timeout | Note; RapidOCR evidence only; if no pass at all: system error (engine unavailable or timeout) |
| Both engines unavailable | System error `ocr_engine_unavailable` |
| Unexpected exception in `check` | System error `internal_error`, no content logged |
| `medcheck_ui.result` fails to import | Basic native rendering (the same decision wording). Known limitation: the clickable readings and the basic caption then both list the readings (shown twice) |
| `medcheck_ui` theme/stage fails or `MEDCHECK_PLAIN_UI=1` | Plain interface, no 3D stage |
| WebGL unavailable / context lost / reduced motion | Still artwork or still frames (JavaScript, manually verified) |
| Code updated while the server runs (stale modules) | Restart instruction instead of a traceback |

## 7. Privacy and offline boundary
Images are decoded in memory; Tesseract receives them on stdin, RapidOCR as arrays; nothing is written, logged or sent. No log line carries image bytes, filenames, OCR text or typed batches. RapidOCR models ship in the wheel and are hash-checked; Three.js is vendored; no CDN, remote font or API. The server binds to localhost. The cached pipeline holds only the public dataset and engines; user images and results live in the Streamlit session state of the one browser session. Public hosting would change this boundary and needs a separate review (`docs/DEPLOYMENT.md`).

## 8. Dependencies (pinned)
`requirements.txt`: streamlit 1.67.0, opencv-python-headless 5.0.0.93, pillow 13.0.0, numpy 2.5.4, RapidFuzz 3.14.6, pytest 9.2.0 (test tool listed with the runtime packages). `requirements-ocr.txt` (installed with `--no-deps`, see `docs/OCR_ENGINES.md`): rapidocr-onnxruntime 1.2.3, onnxruntime 1.32.0, flatbuffers, pyclipper, PyYAML, shapely, six. Native: Tesseract 5.5.3 (`eng`, `osd`). Frontend: Three.js 0.170.0 vendored. No coverage tool, browser-automation tool or lint tool is installed.

## 9. Tests (443 passed on 2026-11-15; `pytest -q`, about 100 s)
Counts are the collected test items per file (parametrised cases count separately).
| Layer | Files (items) |
|---|---|
| Dataset | `test_dataset.py` (18) |
| Normalisation, dates, decision | `test_normalization_dates.py` (36), `test_decision.py` (34) |
| Matching and look-alike safeguards | `test_matching.py` (22), `test_look_alike_consistent_misread.py` (3), `test_alert_check.py` (12, also UI) |
| Image input, preprocessing, OCR adapters | `test_image_input.py` (15), `test_ocr_preprocessing.py` (12) |
| Extraction and parser | `test_extraction.py` (28), `test_v2_parser_and_misreads.py` (60) |
| Pipeline, cascade, manual entry | `test_pipeline.py` (15), `test_v2_pipeline.py` (25), `test_v2_manual_entry.py` (22) |
| Streamlit UI (headless `AppTest`) | `test_app.py` (30), `test_ui_result.py` (41), `test_batch_suggestions.py` (15) |
| 3D interface (static) | `test_ui_scene.py` (16), `test_ui_scene_story.py` (9) |
| Evaluation and fixtures | `test_evaluation.py` (10), `test_real_eval.py` (15), `test_demo.py` (3) |
| Documentation | `test_docs.py` (2: relative links, removed-file references) |

**What the suite does not show (be explicit):**
- **Line or branch coverage was not measured** (no coverage tool is installed and dependencies were not changed for this baseline). The per-file table above is the only coverage evidence.
- OCR tests use synthetic rendered labels; they prove plumbing and safety logic, not accuracy on photographs. No real photograph is part of the suite (they are private and git-ignored).
- The JavaScript (scroll clock, scenes, fallbacks) is executed by no automated test; the 3D interface and the result screen's CSS/layout were checked by headless-Edge runs and the owner's eyes only. Playwright and Selenium are not installed.
- No concurrency, long-running-process or multi-session test exists.
- `Alert found` has only been produced by synthetic fixtures and programmatic tests, never by a photograph of a real listed pack.

## 10. How the architecture evolved, and why
| Stage (commit) | Change | Why | Decision |
|---|---|---|---|
| M0-M6 (`9e43170`..`d41b4ab`) | Tesseract-only pipeline, label-anchored extraction, strict agreement, four-status engine, Streamlit UI, evaluation tooling | Original design | D-001..D-021 |
| M7-M8 (`6ab898f`, `ea045e7`) | Real-photo run workflow; OCR investigation | First real run: 27 of 27 photos `Unable to verify`, OCR text mostly noise | - |
| M9 (`a735acb`) | RapidOCR primary, Tesseract as extra evidence and fallback; glue-aware parser; crop/rotation cascade; manual batch entry | Investigation: the engine dominated; Tesseract could not read stamped foil print | D-022, D-023, D-024 (D-021 superseded) |
| M10 (`a840a31`) | ONNX thread bounding, Tesseract concurrency, date and glue fixes, look-alike explanations, stale-server message | Erratic times (up to 20x), manual-test findings | D-025 |
| M11 (`c83ecf3`) | Clean negatives need the user's confirmation | Both engines agreed on a wrong look-alike (`HLA50019` for `HLAS0019`); agreement is not independence | D-026 |
| M12-M13 (`e7eda99`, `ad8c68f`) | One-time held-out run (spent); alert action check; confirmation-aware metrics; labelled fixtures | Honest evaluation; a false alert from a misread neighbouring batch is possible | D-027, D-028 |
| M14-M15 (`c729b23`..`a1a1813`) | Three.js interface; blister-strip hero replaced by a five-scene story; vendored, hash-pinned, offline | Demonstration quality; frontend only | D-029, D-030 (the strip hero is superseded) |
| M16 (`f24770f`) | Redesigned result screen; "Confirmed by you"; clickable OCR readings; one wording fix in `decision.py` | Readability and manual-test usability; no logic change | D-031, D-032 |

Superseded and replaced: Tesseract-only OCR (by D-022/D-023); the unanimity-over-Tesseract-variants description (now strict agreement over RapidOCR and Tesseract passes, minimum 2); D-021 "no manual correction" (by D-024); the blister-strip hero (by D-030). **Not superseded:** D-014 (evaluation protocol) is OPEN, pending further evaluation planning; the original 60-image proposal and the evidence-category revision are both unapproved and unexecuted (`docs/DECISIONS.md`, `docs/EVALUATION.md`). Retained unchanged: D-001..D-006, D-008..D-020 (D-007 and D-014 remain OPEN) and all safety rules.

## 11. Known limitations
- Real-photograph accuracy is unmeasured; diagnostic runs on 20 development photos and one run on 7 reserved photos exist and are not accuracy figures (`docs/EVALUATION.md`, `docs/HELDOUT_EVALUATION.md`).
- Extraction is label-anchored and heuristic; packs without a recognisable `B.No.`/`Batch`/`Lot` label end as `Unable to verify`. Batches shorter than 3 characters (serials 24, 26) are never read.
- Two engines or views over the same pixels can make the same mistake. Mitigations: strict agreement, near-neighbour abstention (distance 2 for keys of 6+), and the user's confirmation of the printed batch (D-026). A larger misread or a truncated reading can still end as `No alert found` after the user ticks the confirmation.
- Alert corroboration uses all text in the photo and has no manufacturer-conflict rule (a manufacturer found in the text is an extra signal, and for short batches can supply the second one; a conflicting manufacturer is not checked); an unlisted neighbouring batch of a listed product misread by one character could alert (documented, mitigated by the action check, `docs/MATCHING.md`).
- English only; no deskew or perspective correction; one image per check; no barcode/QR; August 2026 list only.
- The dataset hash is verified when the pipeline loads (process start), not on every check.

## 12. Open architectural issues recorded for the independent audit
Identified by reading the code; **none was reproduced, measured or fixed** by this baseline. They are inputs to the audit, not decisions.
| ID | Area | Observation | Evidence |
|---|---|---|---|
| OA-1 | Shared state and concurrency | `get_pipeline()` is `st.cache_resource`, so one `MedCheckPipeline` (with one `RapidEngine` and one cached Tesseract handle) serves every browser session. `_collect_passes` sets `self._rapid = None` after an engine failure, which disables RapidOCR for the whole process until restart. `RapidEngine._engine()` lazily builds the model while temporarily replacing a library function (`rutils.SessionOptions`) with no lock; the code contains no locking. Behaviour with two simultaneous checks is untested. | `pipeline.py`, `ocr_rapid.py`; `grep` finds no `Lock`/`threading` use beyond `ThreadPoolExecutor` |
| OA-2 | Time budget | `OCR_TOTAL_BUDGET_SECONDS` is enforced between passes only; a single RapidOCR pass cannot be interrupted, and `run_ocr` keeps its own 60 s budget. The worst-case wall time of one check is therefore not bounded by the documented budget and is unmeasured. | `pipeline.py`, `ocr.py` |
| OA-3 | UI copy versus mechanism | Story scene 3 says two engines "read the photo independently" and that a batch counts only "when both passes agree". The mechanism is: at least 2 supporting passes among up to six (more with rotation or confirmation), passes that found nothing do not veto, any conflicting reading abstains, and the passes share the same pixels. **Copy corrected 2026-11-15 (audit AU-5):** scene 3 now says the photo is read several times, in different views, by up to two offline engines, that a batch counts only when at least two readings agree and none contradicts them, and that agreeing readings can still be wrong; the scanning overlay no longer says two engines always run. The decorative READER 1 / READER 2 animation is unchanged and illustrative. | `medcheck_ui/theme.py` scene 3 versus `extraction.reconcile_batch` |
| OA-4 | Alert basis | See section 11 (neighbour misread, no manufacturer-conflict rule). Flagged post-demonstration work (`BUILD_PROGRESS.md` 4a). | `matching.py`, `docs/MATCHING.md` |
| OA-5 | Confirmation is attestation | The tick cannot verify that the user actually compared the number (no software can); it is the control against consistent look-alike misreads. Its effectiveness with real users is unstudied (human-confirmation study not done). | D-026, `docs/EVALUATION_STRATEGY.md` |
| OA-6 | Untested JavaScript and CSS | The scene logic and the CSS-selector-based styling (including `.st-key-*` and `[class*="st-key-mc_sugg_"]` rules that depend on Streamlit's DOM class naming, and `st.components.v2`) have no automated browser test; a Streamlit upgrade could break them silently. Streamlit is pinned at 1.67.0. | `medcheck_ui/assets/*.js`, `result.py` CSS; no browser tool installed |
| OA-7 | Coverage unmeasured | Line/branch coverage is unknown; real-photograph behaviour is outside the suite; scripts are only partly exercised. | section 9 |
| OA-8 | Branch state | The current implementation lives only on `ui-redesign`; `master` is behind by M14-M16. The merge is gated on the demo-laptop rehearsal. Risk: documentation and code baselines on two branches. | `git log` |
| OA-9 | Duplicated rendering paths | The basic fallback (`render_status_basic`, `render_details_basic`, `show_field`, `FIELD_WORDS`) duplicates the redesigned view; only a partial test covers the fallback. | `app.py`, `test_ui_result.py` |
| OA-10 | Evaluation validity | Ground truth for existing runs is not independent; D-014 (neither the original 60-image proposal nor the evidence-category revision is approved or executed; pending further evaluation planning) and D-007 remain OPEN; no accuracy figure may be quoted. | `docs/EVALUATION.md`, `docs/EVALUATION_STRATEGY.md` |
| OA-11 | Look-alike fold exceeds the confirmed list | The fold also maps L to 1, but D-005 (owner-confirmed), `PROJECT_GUIDE.md` and the spec name four pairs. The extension is conservative (it only adds abstention; measured: the equivalence groups are identical with and without L, only serials 38/157; 26 of the 220 listed batches contain an L) and is motivated by serial 121 (`0l25038`). Owner confirmation is pending. The code comment in `normalization.py` says the pairs are "named in the spec", which is inaccurate for L: a documentation drift inside the code, not changed by this baseline. | `normalization.py`, `matching.py`, D-005, `docs/MATCHING.md` |
| OA-12 | Serial 121 and what a pack may print | Alerts for serial 121 need the exact spelling `0l25038`/`0L25038`; a printed `0125038` or `0I25038` (both allowed by the official note on that row) ends as `FUZZY_ONLY`, so `Unable to verify` (pinned by `test_matching.py`). The direction is conservative (a possible missed alert, never a false one) but means that row can alert only if the pack really prints an L. Whether that is acceptable is an owner and audit question; D-016 forbids correcting source anomalies. | `docs/DATASET.md`, `data/cdsco_august_2026_nsq_unresolved_items.md` |
| OA-13 | Look-alike coverage | Folding covers five characters. Other look-alikes (5/6, 3/5, 6/8, 2/Z, ...) rely on edit-distance retrieval, which applies only to keys of 6 or more characters; the 27 listed keys under 6 characters get exact-only retrieval, so a one-character misread of such a batch ends as no match and only the user's confirmation (D-026) protects against a miss. Already documented in `docs/MATCHING.md`; recorded so the audit measures it. | `matching.py`, `docs/MATCHING.md`, `docs/EVALUATION_STRATEGY.md` R11 |
