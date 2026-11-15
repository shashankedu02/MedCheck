"""Where the app runs decides which privacy wording is true (D-034). Wording only: no check, rule or threshold reads this.

Run on the user's own computer, a photo never leaves that computer. Hosted (Streamlit Community Cloud), the photo is
uploaded to the hosting server and processed in memory there. The on-screen text must say which, never the wrong one.

Hosted mode is detected, not assumed: the app's files live under /mount/src/ on Community Cloud, or the operator sets
MEDCHECK_HOSTED=1. MEDCHECK_HOSTED=0 forces the local wording. The default on any other machine is local.
"""
from __future__ import annotations

import os
from pathlib import Path

HOSTED_ENV = "MEDCHECK_HOSTED"
_CLOUD_PREFIX = "/mount/src/"


def is_hosted() -> bool:
    flag = os.environ.get(HOSTED_ENV, "").strip().lower()
    if flag in ("1", "true", "yes"):
        return True
    if flag in ("0", "false", "no"):
        return False
    return Path(__file__).resolve().as_posix().startswith(_CLOUD_PREFIX)


# Static, trusted text. Hosted wording states what is true: the upload goes to the server; MedCheck does not keep it or
# pass it on; the platform carries it under its own terms. No claim about the platform's internals is made.
SIDEBAR_LOCAL = "Photos are processed in memory on the computer running this app. They are not saved, logged or sent elsewhere."
SIDEBAR_HOSTED = ("Hosted demo: a photo you upload is sent to the server that runs this app and is processed in memory there. "
                  "MedCheck does not save or log it and sends it to no other service; the hosting platform carries it under its own terms. "
                  "Use test or synthetic photos only if you are unsure.")

HERO_NOTE_LOCAL = "A lookup aid on this computer. Not an authenticity or safety test, and not medical advice."
HERO_NOTE_HOSTED = "A lookup aid. Photos are processed on the hosting server. Not an authenticity or safety test, and not medical advice."

CHIP_LOCAL = ("Offline", "everything runs on this computer")
CHIP_HOSTED = ("No outside OCR", "read by engines inside the app")

INSPECTION_LOCAL = ("Photograph the line marked B.No., Batch or Lot so it fills the frame. "
                    "The photo stays in memory on this computer and is never saved.")
INSPECTION_HOSTED = ("Photograph the line marked B.No., Batch or Lot so it fills the frame. "
                     "The photo is uploaded to the hosting server, kept in memory only and not saved by MedCheck.")

EVIDENCE_ENGINES_LOCAL = "up to two offline engines"
EVIDENCE_ENGINES_HOSTED = "up to two text-recognition engines running inside the app"


def sidebar_note() -> str:
    return SIDEBAR_HOSTED if is_hosted() else SIDEBAR_LOCAL
