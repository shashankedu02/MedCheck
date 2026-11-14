# UI/UX Guidelines

Status: implemented in `app.py` and covered by `tests/test_app.py`. Below is the design intent it follows.

## Main screen
Explain in one short paragraph that the tool checks an image against the August 2026 CDSCO NSQ Drugs list only. Offer two input methods: upload and camera capture. State supported image formats and size limits after they are implemented.

## Results
Show the primary status prominently, followed by:
- extracted product name, batch number and expiry date;
- whether each field was clear, uncertain or unavailable;
- relevant OCR evidence without overwhelming the user;
- matched dataset record and its source serial number, only when a candidate is established;
- reason for abstention or mismatch;
- dataset period and scope limitation;
- safety guidance.

## 3D interface (D-029, branch `ui-redesign`)
Presentation only (`medcheck_ui/`, `app.py` layout); no OCR, matching, decision, dataset or evaluation code is involved.
- **Stage:** one fixed WebGL canvas behind the app (Three.js 0.170.0, local). The blister strip has a brushed, crinkled aluminium lid (procedural texture with bump and roughness maps, perforation lines), lathe-profiled blisters with an embossed flange in refractive glass (`transmission`), glossy two-tone capsules with a seam ring, soft shadows from the capsules, image-based lighting built in code (long softbox reflections), a cyan backdrop glow and drifting light motes for depth, and a printed placeholder batch band (decorative dots, never a real batch). No image or model files are used. Idle motion is capped near 30 fps (20 fps and 1x pixel ratio while the OCR runs), paused in a hidden tab; a quality governor lowers resolution, then swaps to cheaper glass without shadows or motes, then falls back to the still artwork.
- **Scanning is the real OCR run:** `app.py` sets the stage to `scanning` immediately before `pipeline.check()` and to the result tint after it. The strip moves to the centre and enlarges, the page content fades back, the beam sweeps and each blister lights as the beam crosses it, corner brackets lock onto the batch band, and a "Reading the photo on this computer" panel with an **indeterminate** bar is shown. Nothing is simulated: no percentage, no step counter, no fabricated progress. When the result arrives the brackets and glow take the status tint and the page eases to the verdict.
- **Result tints are tints, not verdicts:** alert amber/red (pulses), unable amber, no alert calm cyan (never green, no tick or shield), system error grey. The verdict text stays in the native result boxes.
- **Scroll story:** the strip follows a scripted path (hero, macro on the blisters, close-up of the batch band, pull-back, tool). Poses are keyed to where each step actually sits on the page, move with inertia, and add a subtle pointer parallax (off under reduced motion). The steps are an editorial layout (large outlined numerals, hairline rule, gradient text backing), not boxes; they reveal with CSS only (`animation-timeline`). "Start a check" is a plain anchor to the tool. The sidebar is collapsed by default and glass when opened.
- **Hero:** a three-line statement ("Read the batch. Check the list. Say so when unsure.") with fact chips whose figures come from the loaded dataset (record count and period), "Offline" and "Abstains when the evidence is unclear". No performance figure appears anywhere on the front page (tested).
- **Fallbacks:** no WebGL, a failed library load or a lost context removes the canvas and shows a still strip illustration (CSS data URI); reduced motion renders single frames only; `MEDCHECK_PLAIN_UI=1` restores the plain interface; if `medcheck_ui` cannot import the app runs plain.
- **Readability:** palette tokens and WCAG AA contrast (including over the brightest canvas pixel) are tested; font stack starts with Segoe UI Variable, nothing is downloaded.

Manual browser checklist (before a demonstration): Edge or Chrome on the demo laptop; Wi-Fi off; open the app and confirm the strip renders and idles; scroll through the three steps and watch the camera move; press "Start a check"; upload a fixture, check that the strip enlarges and scans while the reading panel shows, then settles on the result and the page eases to the verdict; resize the window narrow and wide; enable "reduce motion" in Windows and reload (still frame); run with `MEDCHECK_PLAIN_UI=1`; confirm the red TEST FIXTURE banner stays visible in every fixture photo.

## Status wording
- **Alert found:** say that the extracted batch and corroborating fields matched an entry in the August 2026 NSQ snapshot. Show source row and NSQ result. Directly under the alert show "Check before acting" (`Decision.action_check`, D-027): compare the printed batch character by character, and the product, strength and manufacturer, with the listed record; show the batch read next to the listed batch. This prompt never delays or hides the alert.
- **No alert found:** shown only after the user has compared the batch (OCR-read, corrected or typed) with the pack and ticked the confirmation (D-026). Say no qualifying match was found in this one-month snapshot; this does not establish safety or authenticity, and the confirmation checks the printed number only. Before the tick, show `Unable to verify` with the batch as read and the instruction to compare it character by character (S/5, O/0, I/1). Never label an agreed OCR reading as "read consistently"; say it is agreed by the OCR passes and not yet checked against the pack. `Alert found` is never delayed for confirmation.
- **Expired:** show the parsed expiry basis and policy; if month-only ambiguity remains unresolved, do not make a definitive claim.
- **Unable to verify:** explain what is missing/conflicting and suggest a clearer photo or pharmacist consultation.

## Accessibility and trust
Use readable contrast, clear labels, keyboard-operable controls, plain language and visible uncertainty. Do not use green “safe” indicators for No alert found. Avoid fear-inducing language. Never hide the August-only limitation in a footer.
