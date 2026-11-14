"""Central, explicit configuration for MedCheck.

Values marked UNCALIBRATED are engineering defaults chosen conservatively. They
have NOT been calibrated on labelled photographs and must not be presented as
validated. Change them only together with an evaluation run (see docs/EVALUATION.md).
"""
from __future__ import annotations

import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"

# --- Dataset ---------------------------------------------------------------
CANONICAL_DATASET_PATH = DATA_DIR / "cdsco_august_2026_nsq.csv"
OFFICIAL_SOURCE_PATH = DATA_DIR / "cdsco_august_2026_nsq_official_extraction.csv"
DATASET_MANIFEST_PATH = DATA_DIR / "dataset_manifest.json"

# Columns of the canonical application dataset, in order (source columns minus
# the traceability-only "Portal Page" column).
CANONICAL_COLUMNS: tuple[str, ...] = (
    "Serial Number",
    "Name of Product",
    "Batch Number",
    "Manufacturing Date",
    "Expiry Date",
    "Manufactured By",
    "NSQ Result",
    "Reporting Source",
    "Reporting by Lab/State",
    "Reporting Month and Year",
)
SOURCE_EXTRA_COLUMN = "Portal Page"
SOURCE_COLUMNS: tuple[str, ...] = (SOURCE_EXTRA_COLUMN, *CANONICAL_COLUMNS)

# Pinned SHA-256 of the immutable official extraction (as received 2026-11-14).
OFFICIAL_SOURCE_SHA256 = "1eb25a9f6de052cc0be926c5785ad4a6b918ce8d06e030dc3552869d333edcef"

DATASET_REPORTING_PERIOD = "AUG-2026"
DATASET_LABEL = "CDSCO NSQ Alerts, reporting period August 2026"

# --- Image input (UNCALIBRATED) ---------------------------------------------
MAX_UPLOAD_BYTES = 10 * 1024 * 1024
MAX_IMAGE_PIXELS = 40_000_000  # decoded pixel ceiling (decompression-bomb guard)
MIN_IMAGE_SIDE = 300
MAX_WORKING_LONG_SIDE = 3000
ALLOWED_IMAGE_FORMATS = ("JPEG", "PNG", "WEBP")

# --- OCR (UNCALIBRATED) -------------------------------------------------------
OCR_LANGUAGE = "eng"
OCR_TIMEOUT_SECONDS = 25
OCR_PSM_MODES = (6, 11)  # block of text; sparse text
MAX_PREPROCESS_VARIANTS = 4
TESSERACT_CMD_ENV = "MEDCHECK_TESSERACT_CMD"
_WINDOWS_TESSERACT_DEFAULT = Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe")


def tesseract_cmd_candidates() -> list[str]:
    """Ordered places to look for the Tesseract executable (no developer-specific hardcoding)."""
    candidates: list[str] = []
    env = os.environ.get(TESSERACT_CMD_ENV)
    if env:
        candidates.append(env)
    candidates.append("tesseract")
    if _WINDOWS_TESSERACT_DEFAULT.exists():
        candidates.append(str(_WINDOWS_TESSERACT_DEFAULT))
    return candidates


# --- Extraction / matching (UNCALIBRATED) --------------------------------------
MIN_AGREEING_OCR_PASSES = 2
MIN_BATCH_KEY_LENGTH = 3
SHORT_BATCH_KEY_LENGTH = 6  # shorter keys need stronger corroboration
BRAND_MATCH_MIN_SCORE = 90
INGREDIENT_MATCH_MIN_SCORE = 88
FUZZY_BATCH_MAX_DISTANCE = 2  # candidate retrieval only, never confirms an alert

# --- Expiry -------------------------------------------------------------------
# UNRESOLVED OWNER DECISION: how to interpret month-only expiry dates.
# Until approved, MedCheck never emits "Expired". See docs/EXPIRY_POLICY.md.
EXPIRY_POLICY_APPROVED = False
