# OCR Failure Investigation and V2 Design (diagnostic; no production change)

Status: investigation complete. (Implemented afterwards as V2, see `docs/OCR_ENGINES.md`, D-022..D-024 and `BUILD_PROGRESS.md`; this report is kept as the evidence record and still describes the state at commit `ea045e7`.) Production code, thresholds, matching rules, the dataset and the baseline run `run_20261114_200938` are untouched. Experiment scripts: `experiments/ocr_investigation/` (outputs git-ignored). Date: 2026-11-14.

## 1. Method and its limits
- **Split.** Dev = 20 photographs (T001-T008, T010, T011, T013, T014, T016, T017, T019, T020, T022, T023, T025, T026). **Held-out = 7 photographs (T009, T012, T015, T018, T021, T024, T027): excluded from every experiment in this investigation** (`experiments/.../lib.py` refuses to load them) and reserved for the first evaluation of an implemented V2. *Correction (2026-11-15): the original wording here said "never opened, viewed or OCR'd". That was inaccurate: these seven were part of the first baseline run `run_20261114_200938` (all 27 photos, Tesseract only, run before the split), and they were later processed by V2 and visually read by an AI model (`docs/HELDOUT_EVALUATION.md`). None of the 27 photos has physical-pack ground truth. The seven are not eligible as untouched independent held-out samples.*
- **Reference ("ground truth") for batch numbers** was read by eye from zoomed, upright crops (the OCR engine was used only to *locate* the region, never to supply text). Only batches read with certainty are scored: **7 certain** (T003 `HLAS0019`, T006 `5BA1617`, T010 `BEC1106`, T011 `5BA1447`, T013 `25S3GCA146`, T014 `CP50097`, T026 `18261604A`). 3 probable (T004 `INA26003`, T016 `SIL536`, T022 `SIN552`) are reported but not scored. T002, T005, T007, T008, T017, T020, T023 are not reliably readable even by eye (S/5, A/B, I/1 ambiguity, glare). T001 and T025 show no batch on the visible face; T019 was thought to be cut off by the frame edge (see erratum).
- **Small sample.** 7 scored images means every number below is an observation, not an accuracy estimate. This reference was produced by a model reading images, not by checking physical packs or the official list; it is a diagnostic reference, not formal ground truth. No NSQ status of any photo is known.
- One variable was changed at a time where practical (Exps 1-3, 5, 7); engine comparisons (Exps 9-10) change the engine and extractor together.

## 2. What the photographs look like
- All 20 dev photos are 1600x1200 or 1200x1600 JPEGs with **no EXIF orientation tag** (re-encoded), so EXIF handling is irrelevant. The pack is physically rotated in the frame.
- The strip is usually 25-45% of the frame width, on a plain table (16 of 20) or a busy shelf of chocolates (T001, T025, T026).
- The batch/date block is **stamped ink (mostly blue/violet, sometimes black) on embossed foil**. It runs **vertically in about half the photos and upside-down or sideways in several**, while the printed text on the same strip runs in other directions.
- Layouts vary: `B.No.` and the value on one line (T003, T010, T013, T014, T026), the value on the next line (T016, T022), or the block cut by the pack edge/frame (T019).

## 3. Experiment results (dev set)

| # | Change tested | Result |
|---|---|---|
| 0 | Baseline production pipeline (Tesseract, 8 passes) | 0/20 labelled batch found (25/27 not found, 2 ambiguous, over all 27) |
| 1 | Rotate the **whole frame** 0/90/180/270, Tesseract | Still 0/20. Rotation alone does not help. |
| 2 | Auto strip detection (foil texture energy) | Boxes the pack correctly on all plain-background photos; marginal on shelf backgrounds. Cheap (ms). |
| 3 | Strip crop x 4 rotations x upscale to 2400px, Tesseract | 2/20 found a label; one value was wrong (`pry 7`). Crop plus rotation is **not sufficient** with Tesseract. |
| 4 | Locate the ink band by colour, OCR the band | Band locating works when ink is blue/violet and fails on black ink on gold foil (T006, T011, T016, T019: no band). Band crops were clipped and sometimes merged with blue brand print. |
| 5 | OCR the colour-difference ("ink") channel | 1/20. **JPEG stores colour at half resolution, so the ink channel is blocky.** Colour is good for *locating* print, useless for *reading* glyphs. |
| 6-7 | Band luminance, scale 0.6-3x, Gaussian/median/Otsu/adaptive/black-hat | On a clean band (T014) Tesseract reads `B.No.CP50097 MFD` at 94% confidence at every scale and with every denoiser, so scale and denoising barely matter. On blue ink over embossed foil (T003, T010, T004, T013) nothing helped. Orientation picked by Tesseract confidence is unreliable (garbage scored 40-50). |
| 8 | Gate luminance by the chroma ink mask | Marginal gains (partial `EXP.JUN` in T003, `2025 MAY 2027` in T022); not decisive. |
| 9 | **Different local engine** (RapidOCR 1.2.3, Apache-2.0, ONNX, models bundled in the wheel, 14 MB + onnxruntime 54 MB, no network at run time) on the unmodified, unrotated, uncropped frame | **16/20 have a labelled batch line** (vs 0/20), 18/20 with strip crop plus 4 rotations. |
| 10 | Exact-match scoring on the 7 certain batches (below) | see table |

Exp 10 (7 certain batches; "unique exact" = the reference was the only batch reading; "ambiguous" = reference present among several readings):

| Configuration | Extractor | Unique exact | Ambiguous | Wrong only | Not found | s/photo |
|---|---|---|---|---|---|---|
| Production (Tesseract), baseline | production | 0 | 0 | 0 | 7 | ~5-9 |
| RapidOCR, full frame, no rotation | production | 2 | 0 | 4 | 1 | 2.3 |
| RapidOCR, full frame, no rotation | glue-aware prototype | 3 | 0 | 4 | 0 | 2.3 |
| RapidOCR, strip crop, no rotation | glue-aware | 4 | 0 | 2 | 1 | 2.4 |
| RapidOCR, strip crop, 4 rotations | glue-aware | **5** | 1 | 1 | 0 | 8.0 |
| RapidOCR, full frame, 4 rotations | glue-aware | 2 | 3 | 2 | 0 | 24.8 |

Wrong readings observed (reference in brackets): `HLAS50019` [HLAS0019], `5BA13A7` [5BA1447], `INA26083` [INA26003, probable], `18261604K8`/`18261604A8PERBLISTER` [18261604A], `25S3GCA146MR` [25S3GCA146]. The last two are extractor defects (OCR drops spaces so the next label is glued on); the rest are genuine character misreads.

## 4. Root causes, ranked
1. **Engine/input mismatch (dominant).** Tesseract's page-layout analysis plus LSTM fails on small stamped ink over embossed foil with mixed text directions. A text-detector-plus-recogniser engine finds those lines on the raw frame. Changing the engine moved labelled-batch detection from 0/20 to 16/20; no preprocessing change did anything comparable.
2. **Text orientation.** Real but secondary with a detector-based engine: unrotated full frame 16/20 labelled lines, strip crop with 4 rotations 18/20; unrotated, vertical and upside-down blocks (T002, T004, T007 and similar) were recovered only by rotating. Costs 3.5x time per photo.
3. **Cropping.** Small effect (+0 to +1 batch). It improves speed slightly and reduced misreads in this sample (wrong-only 4 -> 2) but is not the main factor. Cropping before rotation was used; the opposite order was not tested separately.
4. **Extraction layer built for Tesseract output.** The production label parser expects spaces ("B.No. ABC MFG"). Glued output (`B.NO.5BA1617MFD`) yields a wrong batch key. Needs a glue-aware parser, and multi-line "label / value on next line" support (T016, T022).
5. **Photo quality.** Glare, partial occlusion by the embossed pattern (T020), batch cut by the frame (T019), the batch on a face not photographed (T001, T025), and 1600 px re-encoded images limit what any engine can do. Not fixable in software.
6. **Validator.** The 300 px minimum side rejected a tight manual crop, as the owner observed. An in-app crop must be allowed to be small (internally upscaled), or the minimum applied to the original upload instead.
7. **Not significant here:** EXIF (absent), scale 0.6-3x, denoising choice, binarisation choice, number of Tesseract passes (8 passes of the wrong approach are still wrong).

## 5. Image-by-image observations (dev set; held-out intentionally absent)
| Test | Observation | Best configuration outcome |
|---|---|---|
| T001 | Front face on a chocolate shelf, glare, no batch visible | Nothing found (appropriate) |
| T002 | Small strip, batch block vertical, purple; last characters ambiguous even by eye | Two competing readings (`51P07486`, `5707486`) |
| T003 | Strip small and low in frame, horizontal blue ink, clear | Full frame: `HLAS50019` (wrong); strip crop: correct |
| T004 | Two strips with a rubber band, block upside-down | `INA26083` (probable reference `INA26003`) |
| T005 | Upside-down purple, tiny | Nothing |
| T006 | Gold foil, black vertical ink | Correct |
| T007 | Block sideways/upside-down | Partial `1886001` (reference unreliable) |
| T008 | Upside-down, small | `25S3GTA4` plus 3 variants (reference unreliable) |
| T010 | Vertical blue, clear | Correct in every configuration |
| T011 | Gold foil, black embossed line near the frame edge | Full frame wrong (`5BA13A7`); crop+4 rotations: correct but among 3 competing readings |
| T013 | Vertical blue | Correct on crop; `MR` glued on full frame |
| T014 | Vertical dark print, clear | Correct (also with Tesseract on a tight band) |
| T016 | Gold, vertical, value on the line after `B.No.` | Nothing (layout) |
| T017 | Very small strip, blue, vertical | Dates read, batch not |
| T019 | QR code beside the block; (see erratum below: the block is complete, not cut off) | Nothing under the investigation setup |
| T020 | Blue ink partly hidden by foil glare | `B.NO.U` fragment only |
| T022 | Label and value on separate lines | Nothing (layout) |
| T023 | Block vertical, partly occluded | Wrong fragment `25020` |
| T025 | Chocolate shelf, no batch face | Nothing (appropriate) |
| T026 | Horizontal, clear, shelf background | `18261604A8PERBLISTER` (extractor glue defect) |

Dates: RapidOCR also returned correct-looking expiry/mfg text where batches worked (for example `EXP.JUN.2028`, `EXP.03-2028`, `MFD.MAY25.EXP.APR.28`); date extraction was not scored because no exact reference was recorded for dates. Expiry stays disabled.

## 6. Recommended OCR architecture (V2)
1. **Engine.** Add RapidOCR (ONNX, local, bundled models) as the primary engine; keep Tesseract as a fallback/secondary pass. Pin versions, verify that models load with the network disabled, and review the licence and supply chain before adoption (new dependency: decision D-022, to be recorded; owner approval is required for a new third-party runtime dependency because it changes the security surface and installation size by about 70 MB).
2. **Pipeline.** (a) Validate and downscale. (b) Detect the pack region (foil-texture detector, fall back to the full frame). (c) OCR the crop unrotated. (d) **Only if no batch label is found**, retry the crop at the other 3 rotations (cascade, to avoid the 3.5x cost on easy photos; the cost saving was not measured). (e) Parse. Do not add more passes by default.
3. **Extraction.** Glue-aware batch parser (value ends at an embedded `MFG/MFD/M.R.P/EXP/PER/INCL`), plus support for the value on the next line. Keep raw strings and the existing normalisation. A batch containing a glued label word is rejected rather than trimmed silently.
4. **Reconciliation.** Keep strict agreement but define "agreement" over independent readings (different rotation/engine), and keep AMBIGUOUS when several distinct readings appear (as for T011). Never pick the "best" of competing readings.
5. **Safety.** The measured misreads (`HLAS50019`, `INA26083`, `5BA13A7`) are the dangerous failure: a confident wrong batch that is not on the list would read as "No alert found" for a batch that may be listed. Mitigations that must stay: abstention when a near-neighbour (edit distance) listed batch exists, the O/0 collision rule, and wording that says the result is for the batch as read. Add a requirement that "No alert found" shows the batch as read, so the user can compare it to the pack.

## 7. Manual batch entry (design)
- Show the extracted batch, with the crop it came from, in an editable field labelled **"Batch read from photo (check against the pack)"**; if nothing was read, show an empty field **"Type the batch number"**.
- Track provenance in the data model: `batch_source = ocr | user_corrected | user_entered`. User text is never stored as OCR evidence and never enters `extraction`; it is passed to the matcher as a separate input.
- **Matching is unchanged.** The same exact-unique batch rule, confusable/collision handling (38/157), fuzzy-as-abstention and corroboration rule apply. Corroboration still needs product evidence from the *photo's OCR text*; the user's typing never corroborates. If no photo text corroborates, the result is `Unable to verify` and the page shows the listed record for the user to compare by eye (still not an alert).
- A manually entered batch can lead to `No alert found` only with the same abstention checks, worded "for the batch you entered", and requires the user to confirm the entry (re-type or tick "I checked this against the pack"), because a typing error is a false-reassurance path.
- Log nothing about the entered text (privacy rules unchanged). Evaluation records must mark the source.
- OCR value edited by the user becomes `user_corrected` and is treated exactly like user entry.

## 8. Proposed V2 workflow (evaluation of the 11 steps)
Keep: upload/capture; auto-detect pack region; show the detected crop; extract; display fields for review; manual correction; run the unchanged decision engine; abstain when evidence is thin.
Change: (a) **Do not require users to set crop boundaries**; auto-crop with a "use full photo" option and a simple rotate button (4-way) as the manual fallback. Adjustable crop boxes cost more UI than they return given the engine finding. (b) **Automatic orientation by cascade** (section 6), not EXIF (absent) or OSD. (c) Run OCR on the crop first and on the full frame only as a fallback. (d) Add a guidance line for capture ("photograph the stamped batch line close up, flat, without glare"), since T019/T020/T001/T025 are limited by the photo. Drop: explicit manual region selection as a first release item.

## 9. Prioritised implementation plan
1. **Decide D-022** (RapidOCR dependency) and record it. *Owner decision.*
2. Parser: glue-aware and next-line batch parser with unit tests (including the glued cases above, collision 38/157, short batches). No engine change needed to start.
3. Engine adapter behind the existing OCR interface; Tesseract kept; engine selectable by config; offline-load test.
4. Pack detection and rotation cascade; allow small internal crops past the 300 px rule.
5. Manual entry UI and `batch_source` provenance, with tests that it never alters matching outcomes or corroboration.
6. Re-run the dev photos, freeze, then run the 7 held-out photos once and report as is.
7. Only after labels exist: consider date extraction scoring and the owner's expiry decision (D-007).

## 10. Required tests
- Parser: glued labels (`B.NO.5BA1617MFD`, `...146MR`, `...A8PERBLISTER`), next-line value, multi-reading ambiguity, short batches.
- Safety regression: 38/157 collision both ways; fuzzy-only abstains; uncorroborated abstains; misread near a listed batch abstains; system failures never become a status; wording tests; privacy tests (no files, no OCR text in logs, localhost).
- Manual entry: user text never reaches `extraction`; same outcomes as an equivalent OCR read for every decision-table row; confirmation required for "No alert found".
- Engine: runs with the network disabled; per-photo time budget; engine-missing is a system error, not "No alert found".
- Evaluation: per-photo exact/incorrect/not-found counts against labelled batches; the held-out set run once.

## 11. Risks, limitations, open questions
- 7 scored photos; no confidence intervals would be meaningful. The 3 wrong-reading categories show the real risk is wrong confident reads, not only failure to read.
- The reference was read by eye by an AI model from re-encoded 1600 px photos; the owner should confirm the 7 certain batches (and the probable ones) against the physical packs before any figure is called ground truth.
- Whether any of the 27 packs is on the NSQ list is unknown, so the alert path is untested on real data; no real-photo "Alert found" has been observed.
- RapidOCR adds about 70 MB, a new maintainer and model supply chain; the recognition model is a general (Chinese/English) model; accuracy on other print styles is unmeasured. Dependency, licence and offline behaviour must be reviewed (D-022).
- Speed: 2.3 s (single pass) to 8 s (4 rotations) per photo on this machine; a cascade is expected to land between, unmeasured.
- Dark-ink-on-gold, glare and cut-off cases remain unreadable by any approach tried; guidance and manual entry are the only remedies.
- Not tested: perspective/deskew correction, super-resolution, more engines (for example PaddleOCR proper, EasyOCR), crop-after-rotation ordering, and date extraction accuracy.
- The held-out set remains unused; any further tuning on it would void it.

## Erratum (added during V2 implementation)
The statement that T019's batch block is cut off by the frame edge was **wrong**. Inspecting the rotated pack crop showed `B.No.: SIH1166A / Mfg. Dt.: JUN.2026 / Exp. Dt.: MAY.2028` complete (upside-down in that rotation). The earlier impression came from my own zoomed reference crop, not from the photo. T019 is therefore not a frame-edge failure; the investigation setup simply did not read it. T019 is recorded in `evaluation/reference_batches.csv` as `probable` (read after the V2 run produced it, so not scored).
