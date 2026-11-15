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

## 3D interface (D-029, D-030; branch `ui-redesign`)
Presentation only (`medcheck_ui/`, the layout in `app.py`); no OCR, matching, decision, dataset or evaluation code is involved.

**One persistent scene, five connected stages, one clock.** A single Three.js scene (0.170.0, local) is driven by a master clock `t` (0 to 5.5) derived from the measured scroll position of five story sections. Camera, particles and objects are pure functions of `t`, so scrolling backwards or quickly is always coherent. `t` follows the scroll with inertia and a speed limit (a fast jump is a flight, never a cut). The camera follows a Catmull-Rom path through keyframes. Captions fade with the same clock; five scene dots and a "Skip to the check" link jump straight to the tool, and nothing forces the story.

| Scene | What happens |
|---|---|
| 1 The medicine | A glass capsule with a seam, a translucent gel and glitter, floating in a bokeh studio; slow rotation, depth, subtle camera drift. Hero statement and fact chips (figures from the loaded dataset). |
| 2 The transformation | A glass of water (refractive water body, so the backdrop bends through it) and an effervescent tablet that descends, fizzes and dissolves. No fluid simulation: bubbles and swirl particles are stateless functions of `t`. Labelled in the caption as an illustration: MedCheck does not test, dissolve or analyse a medicine. |
| 3 Evidence emerges | The dissolved particles leave the glass, organise into rows, resolve into glyph shapes behind a scanning line, and split into two reader outputs (READER 1 and READER 2) read by two beams. The text is illustrative placeholder text (a test checks it is not, and is not near, any listed batch). |
| 4 The inspection | The particles land on a procedural medicine carton as printed information (Mfd., Exp., Lot., a barcode, silver foil panel). A magnifying glass travels along the printed lines and dwells on the batch line. The lens is a real optical effect: a second, narrower camera renders the scene behind the lens into a render target which a shader maps to the lens with barrel distortion and a chromatic edge, so the text is genuinely enlarged and crisp. A subtle cyan light follows the lens. |
| 5 The comparison | The batch characters detach from the carton and fly into the tiles of an "INSPECTED BATCH" panel; beside it a "CDSCO NSQ LIST" panel shows neutral ghost rows. A single connector and a restrained sweep link them. **No match, tick, shield or result is shown.** The camera pulls back, the canvas dims and the real tool rises in from below. |

- **Scanning is the real OCR run:** `app.py` sets the stage to `scanning` immediately before `pipeline.check()` and to the result tint after it. The camera eases back to the magnifier composition, the page content fades out, the lens sweeps the batch line, brackets lock onto it and a "Reading the photo on this computer" panel with an **indeterminate** bar is shown (no percentage, no counter, no simulated progress). Afterwards the camera eases forward again, the brackets and lens ring take the status tint and the page eases to the verdict.
- **Result tints are tints, not verdicts:** alert amber/red, unable amber, no alert calm cyan (never green, no tick or shield), system error grey. The verdict text stays in the native result boxes.
- **Performance and cleanup:** capped near 30 fps (20 fps and 1x pixel ratio while the OCR runs), paused in a hidden tab; one extra scene render only while the lens is visible. A quality governor lowers the resolution, then switches to the lite tier (no refraction, no shadows, smaller lens target), then falls back. Every texture, geometry, render target, event listener and overlay is released on teardown.
- **Fallbacks:** no WebGL, a failed load or a lost context removes the canvas and shows a still capsule illustration (the story collapses to short sections); reduced motion renders single frames only on events; `MEDCHECK_PLAIN_UI=1` restores the plain interface; if `medcheck_ui` cannot import the app runs plain. Portrait screens move the camera back so the subject always fits.
- **Typography and layout:** Segoe UI Variable (nothing downloaded), WCAG AA contrast tested including over the brightest canvas pixel; the sidebar is collapsed by default and glass when opened; the tool is one glass panel.

Manual browser checklist (before a demonstration): Edge or Chrome on the demo laptop; Wi-Fi off; open the app and confirm the capsule renders and idles; scroll slowly and quickly forwards and backwards through all five scenes (the camera must always move continuously); use the scene dots and "Skip to the check"; upload a fixture, check that the camera returns to the magnifier, the lens sweeps the batch line while the reading panel shows, then settles on the result and the page eases to the verdict; resize the window narrow and wide; enable "reduce motion" in Windows and reload (still frames); run with `MEDCHECK_PLAIN_UI=1`; confirm the red TEST FIXTURE banner stays visible in every fixture photo.
## Status wording
- **Alert found:** say that the extracted batch and corroborating fields matched an entry in the August 2026 NSQ snapshot. Show source row and NSQ result. Directly under the alert show "Check before acting" (`Decision.action_check`, D-027): compare the printed batch character by character, and the product, strength and manufacturer, with the listed record; show the batch read next to the listed batch. This prompt never delays or hides the alert.
- **No alert found:** shown only after the user has compared the batch (OCR-read, corrected or typed) with the pack and ticked the confirmation (D-026). Say no qualifying match was found in this one-month snapshot; this does not establish safety or authenticity, and the confirmation checks the printed number only. Before the tick, show `Unable to verify` with the batch as read and the instruction to compare it character by character (S/5, O/0, I/1). Never label an agreed OCR reading as "read consistently"; say it is agreed by the OCR passes and not yet checked against the pack. `Alert found` is never delayed for confirmation.
- **Expired:** show the parsed expiry basis and policy; if month-only ambiguity remains unresolved, do not make a definitive claim.
- **Unable to verify:** explain what is missing/conflicting and suggest a clearer photo or pharmacist consultation.

## Accessibility and trust
Use readable contrast, clear labels, keyboard-operable controls, plain language and visible uncertainty. Do not use green “safe” indicators for No alert found. Avoid fear-inducing language. Never hide the August-only limitation in a footer.
