# Beginner and Agent Workflows

## Workflow A — first inspection (no code edits)
```powershell
cd D:\MedCheck
git status --short
Get-ChildItem -Force
Get-ChildItem .\data
python --version
git --version
tesseract --version
```
Confirm `data\cdsco_august_2026_nsq.csv` exists. Do not paste the entire dataset into a chat; inspect schema and quality summaries.

## Workflow B — virtual environment
```powershell
cd D:\MedCheck
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
```
If PowerShell blocks activation, use the documented local policy/workaround approved by the user; do not change machine-wide execution policy silently.

## Workflow C — run tests
Once tests exist:
```powershell
python -m pytest -q
```
Report actual pass/fail counts. Never report tests as passed if not executed.

## Workflow D — run app
Once `app.py` exists:
```powershell
streamlit run app.py
```

## Workflow E — agent request template
Ask the coding agent to:
1. inspect current files and Git status;
2. read root `AGENTS.md` and relevant feature spec;
3. state a narrow plan and acceptance tests;
4. wait for approval before scope-changing actions;
5. implement only the approved step;
6. run tests and show output;
7. summarize diff and next decision.

## Approval etiquette
The agent may proceed with low-risk implementation after the user approves the stated step. It must pause before modifying source data, installing unexpected dependencies, changing safety policy, deploying, pushing or deleting files.
