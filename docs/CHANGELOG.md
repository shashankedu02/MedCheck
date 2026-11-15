# Changelog

## 2026-11-15 - competition finalisation: photo alert preserved (AU-1), accurate OCR wording (AU-5), held-out history corrected (branch `ui-redesign`, D-033)
- **AU-1:** a manual batch entry can no longer erase an OCR `Alert found`. `ScanResult.photo_result` keeps the original photo result; `preserved_photo_alert` and `preserved_photo_alert_text` (`medcheck/pipeline.py`) feed both renderers (`medcheck_ui/result.py`, `app.py` `render_photo_alert_basic`). The user's result is shown separately and is stated not to cancel or disprove the photo's alert. Tests: `tests/test_photo_alert_preserved.py` (16: no-alert, unable and also-alert outcomes, repeated entries, no notice for a non-alert photo, same-reading confirmation, safeguards unchanged, both renderers, the audit reproduction TG261185 then ZX99001Q).
- **AU-5:** story scene 3 (`medcheck_ui/theme.py`) and the scanning overlay (`medcheck_ui/assets/scene.js`) no longer say two engines always run and both must agree. Two tests in `tests/test_ui_scene_story.py` tie the copy to `config.MIN_AGREEING_OCR_PASSES` and `reconcile_batch`. Animations, timing and layout unchanged.
- **Held-out history corrected (documentation and a comment header only):** the seven reserved photos (T009, T012, T015, T018, T021, T024, T027) were not untouched; they were OCR'd in the first baseline run `run_20261114_200938` and later visually read by an AI model. No photo has physical-pack ground truth. They are not independent held-out samples. Corrected in `OCR_INVESTIGATION`, `V2_REVIEW`, `HELDOUT_EVALUATION`, `POSTER_FACTS`, `BUILD_PROGRESS` and the comment lines of `evaluation/heldout_ids.txt`. No run record, result, label or ID list was changed.
- No extraction, matching, decision, dataset, threshold, expiry or dependency change. D-014 and D-007 remain OPEN.

## 2026-11-15 - documentation baseline after M16 (documentation only)
- `docs/ARCHITECTURE.md` rewritten from the committed code at `f24770f`: layers, module status (implemented + tested / manually verified / unverified), runtime flow including the confirmation gate and manual correction, safety invariants with their enforcing code and tests, failure taxonomy, privacy boundary, test map, architectural evolution and reasons, known limitations, and thirteen open issues for the independent audit (OA-1 to OA-13, not reproduced or fixed).
- `docs/DECISIONS.md`: rows in numeric order (D-024, D-026, D-028 had been out of sequence); superseded-decisions table added. No decision changed.
- Reconciled with the implementation: `PROJECT_SPEC` (flow was Tesseract-only), `TECH_STACK` (the 3D scene is the five-scene story; result screen added), `WORKFLOWS` (RapidOCR install, fixture and evaluation scripts, plain-UI switch), `DEPLOYMENT`, `DEBUGGING_GUIDELINES`, `TESTING_GUIDELINES` (UI test files, coverage not measured, no browser automation), `SECURITY_GUIDELINES`, `README` (branch note, result screen, clickable readings), `CLAUDE.md` document map, `BUILD_PROGRESS` (milestone table M7-M16, current state, next action).
- D-014 clarified: still OPEN, pending further evaluation planning. `docs/EVALUATION.md` now shows the original 60-image proposal and the evidence-category revision side by side, both unapproved and unexecuted; wording that presented either as settled or as "infeasible" was corrected in `DECISIONS` (D-014, D-028, the superseded table), `PROJECT_SPEC`, `README`, `HELDOUT_EVALUATION`, `POSTER_FACTS`, `BUILD_PROGRESS`, `ARCHITECTURE`.
- Look-alike folding clarified: the implementation folds O, I, L, S, B (L is an extension of the four owner-confirmed pairs of D-005, present since M2). Verified against the real index: the fold is read only to detect a rival listed row (`COLLISION`) or retrieve a near row (`FUZZY_ONLY`); it never produces a match, an alert or a clean negative. Documented in D-005, D-018, `MATCHING`, `ARCHITECTURE`, `CLAUDE.md`, `REVIEW_PROCESS`; audit issues OA-11 (L beyond the confirmed list, inaccurate code comment), OA-12 (serial 121 can alert only for an L spelling), OA-13 (look-alike coverage).
- No application code, test, dataset or dependency changed. Test suite re-run: 443 passed.

## 2026-11-15 - result-screen redesign and clickable batch readings (M16, branch `ui-redesign`, D-031, D-032)
- Result screen (D-031): `medcheck_ui/result.py` replaces the plain status boxes and text lines with a status banner, reading cards, a batch-against-listed-batch comparison and record grid for alerts, and a styled batch form; the engine's wording is shown unchanged. Spacing bug fixed (a blanket CSS reset outranked the component rules; now `:where()`). A neutral "Confirmed by you" chip marks a batch the user confirmed against the pack.
- One engine wording fix (`medcheck/decision.py`, one line): after a user-corrected or typed batch, the `No alert found` explanation says "the batch you entered", not "read from the photo". Regression test added.
- Clickable batch readings (D-032): each reading is a button that fills the batch box with the exact string; it clears the confirmation tick, never confirms, never submits, never preselects. They replace the former static chips. Known limitation: in the basic fallback rendering the readings are also listed as a caption (shown twice).
- Tests: 443 passed (was 421 before D1/D2 and the suggestions; +7 for D1/D2, +15 in `tests/test_batch_suggestions.py`). No OCR, extraction, matching, classification, dataset, threshold or expiry change.
- Documentation: `docs/UI_UX_GUIDELINES.md` (result presentation, clickable readings), D-031 and D-032 added to `docs/DECISIONS.md` (D-031 had been cited in the guidelines without a decision entry).

## 2026-11-15 - cinematic five-scene story (M15, branch `ui-redesign`, D-030)
- One persistent Three.js scene driven by a master clock from the measured scroll position: capsule, water glass with effervescent tablet, evidence particles and two readers, medicine carton with a real optical magnifier (render-to-texture lens with distortion), neutral comparison panels, then the real tool. Catmull-Rom camera path, inertia and a speed limit, scene dots and a skip link.
- Scanning stays tied to the real OCR phase (camera returns to the magnifier, indeterminate reading panel, brackets on the batch line). Frontend only; plain UI, no-WebGL, reduced-motion and lite tiers kept; no new dependency; no backend change.

## 2026-11-15 - 3D interface visual refinement (M14b, branch `ui-redesign`)
- Premium strip: procedural brushed/crinkled foil with bump and roughness maps and perforation lines, lathe-profiled refractive glass blisters, glossy capsules with a seam ring, capsule shadows, softbox image-based lighting, backdrop glow and light motes.
- Cinematic scroll: poses keyed to the real position of each story step (macro, batch-band close-up, pull-back, tool) with inertia and pointer parallax; editorial step layout replaces the cards; collapsed glass sidebar; composed hero with dataset-driven fact chips.
- Scanning sequence tied to the real OCR phase: enlarged strip, faded page, blister highlight sweep, bracket lock on the batch band, indeterminate reading panel, tinted result and an eased scroll to the verdict. No fabricated progress. Frontend only; fallbacks and the plain UI unchanged.

## 2026-11-15 - 3D interface (M14, branch `ui-redesign`, D-029)
- Frontend only: Components V2 WebGL stage (blister strip) with locally vendored Three.js 0.170.0, theme, story, scan phase tied to the real OCR call, scroll effects, fallbacks (no WebGL, reduced motion, `MEDCHECK_PLAIN_UI=1`, import failure). The browser component receives only a phase and a status name.
- Audit fixes: static serving configured, lifecycle cleanup, resize/aspect, contrast tests, correct commit reference. No backend, OCR, matching, dataset or evaluation change.

## 2026-11-15 - completion sprint (M13)
- D-027: every `Alert found` shows "Check before acting" (batch character by character, product, strength, manufacturer) with the batch read beside the listed batch; listed neighbouring batches are named. Alerts are not delayed; no matching rule or threshold changed.
- D-028: `medcheck/evaluation.py` counts results awaiting confirmation separately; listed packs misread into unlisted strings are reported as potential misses.
- Synthetic fixtures carry an in-frame "TEST FIXTURE" banner and a manifest; new neighbour fixture; `scripts/run_fixture_check.py` records fixture runs apart from real-photo runs.
- Documentation reconciled; assessment `docs/EVALUATION_STRATEGY.md`; poster facts `docs/POSTER_FACTS.md`.

## 2026-11-15 - reserved-photo evaluation and owner browser tests
- One-time run of the unchanged pipeline (`c83ecf3`) on the 7 reserved photos: `docs/HELDOUT_EVALUATION.md`. 0 wrong batches among 4 certain references, 1 exact, 3 abstained; a likely wrong truncated reading (T009) was withheld by D-026. Records only; no tuning.
- The owner's four manual browser tests recorded in `docs/EVALUATION.md` (user-performed; not accuracy evidence).
- The reserved photographs are now spent.

## 2026-11-15 - D-026: clean negatives need the user's confirmation
- A loosely cropped T003 was read as `HLA50019` by both OCR views (true `HLAS0019`), shown as "read consistently" and gave `No alert found`. Reproduced; root cause and corrected claims in `docs/V2_REVIEW.md` (addendum).
- No `No alert found` / `Expired` for any batch string (OCR-read, corrected or typed) until the user has compared it with the pack and confirmed; `Unable to verify` until then; `Alert found` never delayed. Label "read consistently" replaced by "agreed by the OCR passes - not yet checked against the pack". Matching, thresholds, dataset unchanged; no automatic S/5 substitution.
- Evaluation tooling records withheld negatives (`ocr_batch_unconfirmed`) and scores them Inconclusive.

## 2026-11-15 - V2 manual-testing review (D-025)
- Diagnosed the startup `ImportError` (stale server modules after a code update; reproduced); the app now shows a restart instruction.
- Speed: bounded ONNX threads (removes 10-20x outliers, same text), engine warm-up at start, Tesseract concurrent with RapidOCR (-26% in an interleaved A/B).
- Dates: dropped-F `MG.JUL.2025` handled safely, glued month cut from the batch, `JUN25` / `MfgDt:` forms read.
- Look-alike-only conflicts explained (`5 or S`); manual-entry confirmation cleared on edit.
- Evidence and rejected alternatives: `docs/V2_REVIEW.md`.

## 2026-11-14 - V2: RapidOCR integration, glue-aware parser, manual batch entry (D-022..D-024)
- RapidOCR primary engine (pinned in `requirements-ocr.txt`, offline, model hashes verified), Tesseract retained as extra evidence and fallback; pack-region crop; rotation retries only when no batch label was found; one bounded confirmation pass; strict agreement, near-neighbour abstention, O/0 collision and product corroboration unchanged.
- Batch parser cuts glued labels (`5BA1617MFD`, `...146M.R`), reads a value on the next line, rejects label words; every reading keeps engine/view provenance.
- Manual batch entry with `BatchSource` provenance and a confirmation requirement for typed clean negatives; `No alert found` shows the batch checked.
- Evaluation: held-out photographs excluded by default, independent batch reference scoring. Details: `docs/OCR_ENGINES.md`, `docs/OCR_INVESTIGATION.md`.

## 2026-11-14 - real-photograph evaluation workflow
- `scripts/run_evaluation.py`, `scripts/set_ground_truth.py`, `medcheck/real_eval.py`: per-run, non-overwriting CSV/Markdown records for photos in `evaluation/incoming_photos/`; ground truth kept separate and initially Pending. See `docs/EVALUATION.md`.

## 2026-11-14 - first implementation (milestones M0-M6)
- Baseline commit of the pre-implementation documentation and datasets; `.gitattributes` keeps data byte-exact.
- Canonical dataset generated reproducibly from the official CDSCO extraction (pinned SHA-256), manifest, fail-closed loader.
- Normalization, month-year parsing, four-status decision engine with separate system errors; `Expired` disabled pending owner policy (D-007).
- Product parsing and batch-led matching with confusable-collision handling (serials 38/157).
- Image validation, preprocessing, local Tesseract via stdin, label-anchored extraction with strict cross-pass agreement.
- Pipeline and Streamlit UI; localhost-only, no telemetry, no image persistence.
- Evaluation tooling and demo set; documentation consolidated (superseded documents moved to `docs/archive/`); review process for Antigravity.
- Test suite and results: see `BUILD_PROGRESS.md`.

## 2026-11-13 - pre-implementation documentation package
Documentation-only package (superseded; preserved in `docs/archive/`).
