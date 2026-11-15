# Deployment (Streamlit Community Cloud, D-034)

Status: PREPARED, NOT DEPLOYED. Nothing below has run on Linux or on Community Cloud yet; see "Verification status".

## Targets
- One shared GitHub repository, owner `shashankedu02`, name `MedCheck`, **private** (owner's choice, 2026-11-15). Collaborator: `amrutnanda2007-hub` (write access; Amrut must accept the invitation).
- One Community Cloud app: repository `shashankedu02/MedCheck`, branch `ui-redesign`, main file `app.py`. `master` is not touched. A future `main` branch is optional and needs the owner's decision.
- Private repository: Community Cloud must be authorised to read it (sign in at https://share.streamlit.io with the GitHub account that owns it and allow access to private repositories when asked).

## Files that make the build work
- `requirements.txt`: every runtime pin (one file only; Cloud ignores `requirements-ocr.txt`). OpenCV is `opencv-python==5.0.0.93`, the name `rapidocr-onnxruntime` requires, instead of the headless wheel used locally (a single file cannot say `--no-deps` for one line).
- `packages.txt`: `tesseract-ocr` (found on PATH; English data ships with the Debian package), `libgl1` and `libglib2.0-0` (needed by the non-headless OpenCV wheel).
- `.streamlit/config.toml`: unchanged (telemetry off, 10 MB upload cap, XSRF on, static serving of `static/` for the vendored Three.js, theme). `server.address = "localhost"` is kept; the Community Cloud documentation does not list it among the options it overrides, and whether the app is reachable with it is **unverified until the first cloud build**. If the app does not come up, that line is the first suspect; changing it is a safety-relevant change (a test pins it) and needs the owner.
- RapidOCR models ship inside the wheel; there is no model download at run time. Their SHA-256 are pinned in `medcheck/config.py`; a mismatch makes RapidOCR unavailable and the app falls back to Tesseract with a visible note.

## Python version
Choose **3.13** in "Advanced settings" when deploying (the default there is 3.12, which is not what the pins were verified on). The version cannot be changed after deployment without deleting and redeploying the app. All pins have CPython 3.13 Linux wheels (resolver dry-run with manylinux tags succeeded for the full transitive set).

## Deployment steps (manual; they need the owners' accounts)
1. Owner creates the private repository `MedCheck` under `shashankedu02` (no README/licence/gitignore, so the push is a clean first push).
2. `git remote add origin https://github.com/shashankedu02/MedCheck.git` then `git push -u origin ui-redesign`. Never force-push. `master` need not be pushed.
3. GitHub, Settings, Collaborators: add `amrutnanda2007-hub` with write access; Amrut accepts the email/notification invitation.
4. https://share.streamlit.io, Create app: repository `shashankedu02/MedCheck`, branch `ui-redesign`, main file `app.py`, Advanced settings, Python 3.13, no secrets needed.
5. After the first build, run the live checks below with synthetic fixtures only.

## Privacy: local and hosted are different
Local: the photo never leaves the computer. Hosted: the photo is uploaded to the server that runs the app and is processed in memory there; MedCheck does not save or log it and sends it to no other service (no external OCR); the hosting platform carries the upload under its own terms. The interface says so in hosted mode (`medcheck_ui/hosting.py`, detected from the `/mount/src/` path or `MEDCHECK_HOSTED=1`; `MEDCHECK_HOSTED=0` forces local wording). If detection ever failed, the local wording would be shown on the hosted app, which would be false: check the sidebar and the story text in the live app (checklist below).

## Known deployment limitations
- Cloud Tesseract is the Debian package (about 5.3), not the 5.5.3 used for local verification; its output may differ slightly. Accuracy was never evaluated on real photographs (D-014 open) and is not re-evaluated here.
- Resource limits (memory/CPU) of the free tier are not measured. OCR runs several passes and the first request loads RapidOCR; expect a slow first check and cold starts after inactivity. Not measured.
- The demonstration fixtures (`demo_images/`) are not in the repository (git-ignored); upload them from the local machine for live checks.

## Verification status
| Item | State |
|---|---|
| Full test suite, local Windows, Python 3.13.5 | verified (see BUILD_PROGRESS) |
| Dependency resolution for Linux CPython 3.13 | resolver dry-run only (not an install) |
| Linux install, Tesseract on Linux, libGL import | NOT verified (no Linux/WSL/Docker here) |
| GitHub repository, collaborator access | NOT done |
| Community Cloud build | NOT done |
| Live app | NOT verified |

## Live checklist (after the first build; synthetic fixtures only)
Startup without an error box; sidebar shows the dataset period and record count and the HOSTED privacy sentence; story text shows no "this computer"/"Offline" claim; static Three.js loads (canvas appears, or the still fallback); upload FIXTURE_1 (Alert found), FIXTURE_6 (Unable to verify), FIXTURE_3 (Unable to verify, then No alert found after ticking the box); manual correction; engines listed under Technical details (RapidOCR and Tesseract, or a visible fallback note); app logs contain no photo content; `MEDCHECK_PLAIN_UI=1` as a Cloud secret/environment value for the plain interface if needed.

## Release checklist
Tests pass; dataset hash recorded; no secrets; safe errors; safety language visible; hosted privacy wording shown; deployment target verified; rollback: delete the Cloud app (the local build is unaffected).
