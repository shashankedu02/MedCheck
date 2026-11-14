"""Does OMP_THREAD_LIMIT change Tesseract pass time or output? One variable: the OpenMP thread limit (unset = default)."""
import os
import statistics
import subprocess
import time

import cv2
import numpy as np
from PIL import Image

from lib import *  # noqa: F401,F403
from medcheck import config
from medcheck.ocr import find_engine, _png_bytes, parse_tsv
from medcheck.preprocessing import make_variants
from medcheck.regions import crop_to, detect_pack_region

eng = find_engine()
im = Image.open(photo_path(13)).convert("RGB")
reg = detect_pack_region(im)
view = crop_to(im, reg) if reg else im
pixels = make_variants(view)[1].pixels  # clahe, as the pipeline uses
png = _png_bytes(pixels)
cmd = [eng.command, "stdin", "stdout", "-l", config.OCR_LANGUAGE, "--psm", "6", "--oem", "3", "-c", "preserve_interword_spaces=1", "tsv"]
ref = None
print(f"image {pixels.shape[1]}x{pixels.shape[0]}")
print(f"{'OMP_THREAD_LIMIT':>17} | min/median wall of 5 | same text as default")
for limit in (None, "1", "2", "4"):
    env = dict(os.environ)
    env.pop("OMP_THREAD_LIMIT", None)
    if limit:
        env["OMP_THREAD_LIMIT"] = limit
    walls, text = [], ""
    for _ in range(5):
        t = time.perf_counter()
        r = subprocess.run(cmd, input=png, capture_output=True, env=env)
        walls.append(time.perf_counter() - t)
        text = "\n".join(parse_tsv(r.stdout.decode("utf-8", "replace"))[0])
    ref = text if ref is None else ref
    print(f"{limit or 'unset':>17} | {min(walls):4.2f}s / {statistics.median(walls):4.2f}s | {text == ref}")
