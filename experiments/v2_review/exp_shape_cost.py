"""Is the 2 s RapidOCR pass (vs 0.5 s in a repeated-image benchmark) a per-NEW-SHAPE cost?
Same engine settings as production. For several crops/sizes: time call 1 (new shape) vs calls 2-3 (same shape)."""
import time

import cv2
import numpy as np
from PIL import Image

from lib import *  # noqa: F401,F403
from medcheck.ocr_rapid import RapidEngine
from medcheck.regions import crop_to, detect_pack_region

eng = RapidEngine()
eng.warm_up()
engine = eng._engine()
views = []
for i in (3, 13, 6, 10, 14):
    im = Image.open(photo_path(i)).convert("RGB")
    reg = detect_pack_region(im)
    views.append((f"T{i:03d}_full", np.asarray(im)[..., ::-1].copy()))
    if reg:
        views.append((f"T{i:03d}_crop", np.asarray(crop_to(im, reg))[..., ::-1].copy()))

print(f"{'view':<12} {'shape':>11} | call1(new shape)  call2  call3")
c1s, c2s = [], []
for name, img in views:
    ts = []
    for _ in range(3):
        t = time.perf_counter(); engine(img); ts.append(time.perf_counter() - t)
    c1s.append(ts[0]); c2s.append(ts[1])
    print(f"{name:<12} {str(img.shape[1]) + 'x' + str(img.shape[0]):>11} | {ts[0]:6.2f}s          {ts[1]:5.2f}s {ts[2]:5.2f}s")
print(f"\nmean first call {np.mean(c1s):.2f}s vs mean repeat call {np.mean(c2s):.2f}s")

# does the SAME shape with different content stay fast? (shape reuse is what matters, not content)
a = views[0][1]
b = np.ascontiguousarray(a[:, ::-1])  # mirrored: same shape, different pixels
t = time.perf_counter(); engine(b); print(f"same shape, different pixels, first time seen: {time.perf_counter() - t:.2f}s")
