"""Does the ONNX thread count matter for RapidOCR pass time (and is it robust to CPU contention)?
One variable: intra_op_num_threads (0 = ONNX default = all physical cores). Fixed images, 5 trials each."""
import statistics
import time

import numpy as np
from PIL import Image

from lib import *  # noqa: F401,F403
from medcheck.regions import crop_to, detect_pack_region
import rapidocr_onnxruntime.utils as u
from rapidocr_onnxruntime import RapidOCR

orig = u.SessionOptions


def with_threads(n):
    def S():
        o = orig()
        if n:
            o.intra_op_num_threads = n
            o.inter_op_num_threads = 1
        return o
    return S


images = {}
for i in (3, 13):
    im = Image.open(photo_path(i)).convert("RGB")
    reg = detect_pack_region(im)
    images[f"T{i:03d}_full"] = np.asarray(im)[..., ::-1].copy()
    if reg:
        images[f"T{i:03d}_crop"] = np.asarray(crop_to(im, reg))[..., ::-1].copy()

print(f"{'threads':>8} | " + " | ".join(f"{k:>12}" for k in images) + " | text identical to default?")
ref_text = {}
for n in (0, 1, 2, 4, 6, 8, 12):
    u.SessionOptions = with_threads(n)
    eng = RapidOCR()
    cells, same = [], True
    for k, img in images.items():
        eng(img)  # warm-up
        walls, cpus = [], []
        for _ in range(5):
            w, c = time.perf_counter(), time.process_time()
            res, _ = eng(img)
            walls.append(time.perf_counter() - w)
            cpus.append(time.process_time() - c)
        text = "|".join(r[1] for r in (res or []))
        if n == 0:
            ref_text[k] = text
        same &= text == ref_text.get(k, text)
        cells.append(f"{min(walls):4.1f}/{statistics.median(walls):4.1f}s")
    print(f"{n or 'default':>8} | " + " | ".join(f"{c:>12}" for c in cells) + f" | {same}   (min/median wall)")
u.SessionOptions = orig
