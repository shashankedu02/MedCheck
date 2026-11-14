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
OCR_TOTAL_BUDGET_SECONDS = 60
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


# --- OCR engines, V2 (UNCALIBRATED) ---------------------------------------------
# RapidOCR is the primary engine; Tesseract contributes extra passes on the same views.
USE_RAPIDOCR = True
RAPIDOCR_RETRY_ROTATIONS_DEG = (90, 180, 270)  # crop only; tried ONLY when no batch label was found
TESSERACT_EVIDENCE_VARIANTS = 2  # preprocessing variants Tesseract runs when RapidOCR is primary
CROP_UPSCALE_WHEN_NO_REGION = 1.3  # second RapidOCR view when no pack region was found

# SHA-256 of the model files shipped inside rapidocr-onnxruntime==1.2.3 (verified before every load; a
# mismatch makes RapidOCR unavailable and the pipeline falls back to Tesseract with a note).
RAPIDOCR_MODEL_SHA256 = {
    "ch_PP-OCRv3_det_infer.onnx": "3439588c030faea393a54515f51e983d8e155b19a2e8aba7891934c1cf0de526",
    "ch_PP-OCRv3_rec_infer.onnx": "897a3ededb38fee0dae2c1ccee38241f37df202c9509e3abca02e9217c5ee615",
    "ch_ppocr_mobile_v2.0_cls_infer.onnx": "e47acedf663230f8863ff1ab0e64dd2d82b838fceb5957146dab185a89d6215c",
}

# --- Manual batch entry ----------------------------------------------------------
MANUAL_BATCH_MAX_CHARS = 30

# --- Extraction / matching (UNCALIBRATED) --------------------------------------
MIN_AGREEING_OCR_PASSES = 2
MIN_BATCH_KEY_LENGTH = 3
MAX_BATCH_LETTER_RUN = 5  # longest run of letters in any of the 220 listed batches; longer runs are words, not batches
BATCH_ALLOWED_CHARS = r"A-Za-z0-9 \-/.,"  # the character set observed in every listed batch; others mean OCR garbage
EDGE_MARGIN_FRACTION = 0.012  # a text line this close to the image/crop edge may be cut off
EDGE_MARGIN_MIN_PX = 6
SHORT_BATCH_KEY_LENGTH = 6  # shorter keys need stronger corroboration
BRAND_MATCH_MIN_SCORE = 90
INGREDIENT_MATCH_MIN_SCORE = 88
FUZZY_BATCH_MAX_DISTANCE = 2  # candidate retrieval only, never confirms an alert

# --- Expiry -------------------------------------------------------------------
# UNRESOLVED OWNER DECISION: how to interpret month-only expiry dates.
# Until approved, MedCheck never emits "Expired". See docs/EXPIRY_POLICY.md.
EXPIRY_POLICY_APPROVED = False
