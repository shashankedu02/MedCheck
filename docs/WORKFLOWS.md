# Workflows (PowerShell, from `D:\MedCheck`)

## One-time setup
```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
tesseract --version        # native engine must be installed separately (v5.x, English data)
```
If PowerShell blocks `Activate.ps1`, skip activation and call `.\.venv\Scripts\python.exe` directly, as below.

## Run the app
```powershell
.\.venv\Scripts\python.exe -m streamlit run app.py
```
Opens at http://localhost:8501 (localhost only).

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
.\.venv\Scripts\python.exe scripts\make_demo_images.py        # writes demo_images\ (synthetic labels)
.\.venv\Scripts\python.exe scripts\evaluate.py --manifest eval_private\manifest.csv --split heldout
```

## Resuming development
Read `BUILD_PROGRESS.md`, run `git status` and the tests, then continue with its "Next action". Update `BUILD_PROGRESS.md` and commit at the end of each milestone.
