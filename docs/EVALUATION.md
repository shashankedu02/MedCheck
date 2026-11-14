# Evaluation Protocol (D-014 OPEN: not yet performed)

**No accuracy, sensitivity, specificity or time-saving claim may be made about MedCheck until this protocol has been run and the raw per-image results are kept.** The automated test suite proves behaviour on synthetic labels and logic cases; it is not an evaluation of real-world OCR.

## Planned study
Target: 60 photographs of real medicine packs, 30 whose batch is in the August 2026 NSQ list and 30 that are not. With n = 30 per group, confidence intervals are wide (for example 27/30 correct has a 95% Wilson interval of roughly 74-97%); report them, do not round them away.

## Collection (owner decisions still needed)
- Source of packs/photos, permission to photograph, and removal of personal information.
- Realistic conditions: curved foil, glare, blur, low light, rotation, small print, multiple dates, carton plus strip.
- Ground truth from the physical pack and the official list, labelled **before** running the software: `expected_alert`, `expected_serial`, `true_batch` (exactly as printed).
- Split into `dev` (used to tune thresholds in `medcheck/config.py`) and `heldout` (run once, report as is). Never tune on heldout images. Freeze the code version and the dataset hash before the heldout run.
- Store images outside version control (`eval_private/` and `eval_images/` are git-ignored) and delete them when no longer needed.

## Running
```powershell
.\.venv\Scripts\python.exe scripts\evaluate.py --manifest eval_private\manifest.csv --split heldout --out eval_private\results.csv
```
The manifest format is documented in the script header. The script refuses missing or duplicate images and prints, with confidence intervals: alert sensitivity (abstentions count as misses), false negatives (wrong clean negatives) separately from abstentions, false positives, alert precision, specificity, abstention rate, decisive coverage, system errors, batch exact accuracy, median and p95 latency.

## Reporting rules
Keep every abstained or failed image in the denominators. Report false negatives and false positives separately and discuss each. Record hardware, OS, Tesseract version (`tesseract --version`), dataset SHA-256 (from `data/dataset_manifest.json`) and git commit. If the protocol is compromised (labels uncertain, tuning on heldout, leakage), say so and do not claim validated performance.

## What is already verified (not an evaluation)
Unit and integration tests, including synthetic-label runs through real Tesseract and the Streamlit widgets, are described in `docs/TESTING_GUIDELINES.md`.
