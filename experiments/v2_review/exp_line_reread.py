"""Field-specific re-read: crop ONLY the batch line (located by RapidOCR) and read it again with several methods.
Question: does a tight line crop give readings that are more often exact, or that disagree less with the references?
Reference tier 'certain' (7 photos) is scored; 'probable' photos are shown. Dev photos only. Diagnostic: nothing here is
used by the app."""
import json
import re
import sys

import cv2
import numpy as np
from PIL import Image

from lib import *  # noqa: F401,F403
from medcheck.extraction import _BATCH_LABEL, extract_from_lines
from medcheck.normalization import batch_key
from medcheck.ocr import find_engine, run_pass
from medcheck.ocr_rapid import RapidEngine
from medcheck.preprocessing import make_variants
from medcheck.regions import crop_to, detect_pack_region

rapid = RapidEngine()
rapid.warm_up()
engine = rapid._engine()
tess = find_engine()
IDS = [3, 6, 10, 11, 13, 14, 26, 4, 16, 19]  # 7 certain + 3 probable


def views_for(i):
    im = Image.open(photo_path(i)).convert("RGB")
    reg = detect_pack_region(im)
    base = crop_to(im, reg) if reg else im
    out = {"full_rot0": im, "crop_rot0": base}
    for d in (90, 180, 270):
        out[f"crop_rot{d}"] = base.rotate(d, expand=True)
    return out


def find_batch_boxes(view):
    """RapidOCR on a view -> boxes (x0,y0,x1,y1) of lines that carry a batch label (+ the next line if the label stands alone)."""
    res = engine(np.asarray(view)[..., ::-1].copy())[0] or []
    boxes = []
    for k, (box, text, _s) in enumerate(res):
        if _BATCH_LABEL.search(text):
            xs, ys = [p[0] for p in box], [p[1] for p in box]
            b = [min(xs), min(ys), max(xs), max(ys)]
            rest = text[_BATCH_LABEL.search(text).end():].strip()
            if not rest and k + 1 < len(res):  # label alone: include the neighbouring line
                nb = res[k + 1][0]
                b = [min(b[0], min(p[0] for p in nb)), min(b[1], min(p[1] for p in nb)), max(b[2], max(p[0] for p in nb)), max(b[3], max(p[1] for p in nb))]
            boxes.append(b)
    return boxes


def crop_line(view, b, margin=0.5):
    x0, y0, x1, y1 = b
    h = y1 - y0
    return view.crop((max(0, int(x0 - h * margin)), max(0, int(y0 - h * margin)), min(view.width, int(x1 + h * margin * 2)), min(view.height, int(y1 + h * margin))))


def methods(line_img):
    """Each method returns the recognised text of the line crop."""
    out = {}
    arr = np.asarray(line_img)
    for s in (1.0, 1.5, 2.0):
        big = cv2.resize(arr, None, fx=s, fy=s, interpolation=cv2.INTER_CUBIC) if s != 1 else arr
        res = engine(big[..., ::-1].copy())[0] or []
        out[f"rapid_full_x{s}"] = " ".join(r[1] for r in res)
    g = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)
    g2 = cv2.resize(g, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
    cl = cv2.createCLAHE(2.0, (8, 8)).apply(g2)
    for name, px in (("tess_gray", g2), ("tess_clahe", cl)):
        for psm in (7, 6):
            out[f"{name}_psm{psm}"] = " ".join(run_pass(tess, px, name, psm, 20).lines)
    return out


results = {}
for i in IDS:
    ref = CERTAIN.get(f"T{i:03d}") or (REFERENCE.get(f"T{i:03d}") or ("",))[0]
    tier = (REFERENCE.get(f"T{i:03d}") or ("", ""))[1]
    per = {}
    for vname, view in views_for(i).items():
        for b in find_batch_boxes(view)[:2]:
            for mname, text in methods(crop_line(view, b)).items():
                for raw in extract_from_lines([text]).batch_candidates:
                    per.setdefault(mname, []).append((vname, raw))
    results[i] = dict(ref=ref, tier=tier, readings=per)
    print(f"\nT{i:03d} reference {ref} ({tier})")
    for m, lst in sorted(per.items()):
        keys = {batch_key(r).key for _v, r in lst}
        verdict = "".join("=" if k == batch_key(ref).key else "x" for k in sorted(keys)) if ref else "?"
        print(f"   {m:<16} {sorted({r for _v, r in lst})}  [{verdict}]")
json.dump(results, open(OUT / "line_reread.json", "w"), indent=1)
