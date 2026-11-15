# Workflows (PowerShell, from `D:\MedCheck`)

## One-time setup
```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pip install --no-deps -r requirements-ocr.txt   # primary OCR engine (RapidOCR); see docs/OCR_ENGINES.md for why --no-deps
tesseract --version        # native engine must be installed separately (v5.x, English data)
```
Without `requirements-ocr.txt` the app still runs, on Tesseract alone, and says so.
If PowerShell blocks `Activate.ps1`, skip activation and call `.\.venv\Scripts\python.exe` directly, as below.

## Run the app
```powershell
.\.venv\Scripts\python.exe -m streamlit run app.py
```
Opens at http://localhost:8501 (localhost only). After changing code, stop and restart the server (the app shows a restart message if it detects stale modules).

`MEDCHECK_PLAIN_UI=1` starts the plain interface (no story, no 3D stage): the demonstration safety net. Set it in the shell before `streamlit run`.

## Run tests
```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

## Dataset
```powershell
.\.venv\Scripts\python.exe scripts\build_dataset.py --check   # verify committed dataset is exactly reproducible
.\.venv\Scripts\python.exe scripts\build_dataset.py           # rebuild (only if the pinned official source changed policy-wise)
```

## Demonstration images and evaluation
```powershell
.\.venv\Scripts\python.exe scripts\make_demo_images.py        # writes demo_images\ (synthetic, labelled TEST FIXTURE) + fixtures_manifest.csv
.\.venv\Scripts\python.exe scripts\run_fixture_check.py       # records a fixture run separately from real photos
.\.venv\Scripts\python.exe scripts\run_evaluation.py          # runs evaluation\incoming_photos (private, git-ignored) through the real pipeline; reserved photos excluded
.\.venv\Scripts\python.exe scripts\set_ground_truth.py T005 "Alert found" --serial 4 --batch ABC123 --verified-by "checked pack + CDSCO list"   # an independently verified label (see --help)
.\.venv\Scripts\python.exe scripts\evaluate.py --manifest <manifest.csv> [--split dev|heldout|all] [--out <file>]   # metrics for a labelled set that follows docs/EVALUATION.md
```
`scripts\run_heldout_evaluation.py` was a one-time run on the reserved photographs; they are spent (`docs/HELDOUT_EVALUATION.md`). Do not use them to tune or compare designs.

## Resuming development
Read `BUILD_PROGRESS.md`, run `git status` and the tests, then continue with its "Next action". Update `BUILD_PROGRESS.md` and commit at the end of each milestone.
