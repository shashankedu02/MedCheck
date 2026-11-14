"""Exp 1: does rotating the FULL image (no crop) change what Tesseract finds? One variable: rotation."""
import json, time
from concurrent.futures import ThreadPoolExecutor
import numpy as np
from lib import *

def job(args):
    i, deg, psm = args
    g = to_gray(rotate(load(i), deg))
    t = time.monotonic(); p = ocr(g, psm); dt = time.monotonic() - t
    return dict(img=i, rot=deg, psm=psm, secs=round(dt, 1), **stats(p))

jobs = [(i, d, psm) for i in DEV for d in (0, 90, 180, 270) for psm in (11,)]
with ThreadPoolExecutor(4) as ex:
    rows = list(ex.map(job, jobs))
json.dump(rows, open(OUT / "exp1.json", "w"), indent=1)
print("img  | label_words by rot 0/90/180/270 | labelled-batch candidates found at rot")
for i in DEV:
    r = {x["rot"]: x for x in rows if x["img"] == i}
    best = max(r.values(), key=lambda x: x["label_words"])["rot"]
    print(f"{i:>3} | {[r[d]['label_words'] for d in (0,90,180,270)]} | best rot {best} | batch cands {[ (d, r[d]['batch_cands']) for d in (0,90,180,270) if r[d]['batch_cands']]}")
tot = {d: sum(x["label_words"] for x in rows if x["rot"] == d) for d in (0,90,180,270)}
print("total label words per rotation:", tot)
print("images with a labelled batch candidate at ANY rotation:", sum(1 for i in DEV if any(x["batch_cands"] for x in rows if x["img"] == i)), "/", len(DEV))
print("images with one at rot 0:", sum(1 for i in DEV if any(x["batch_cands"] for x in rows if x["img"] == i and x["rot"] == 0)))
