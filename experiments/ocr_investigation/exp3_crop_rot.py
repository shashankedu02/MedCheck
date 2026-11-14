"""Exp 3: crop to detected strip, then rotate 0/90/180/270, upscale to long side 2400. Gray only, psm 6 and 11."""
import json, time, cv2, numpy as np
from concurrent.futures import ThreadPoolExecutor
from PIL import Image
from lib import *
from crop import strip_bbox

def prep(i, deg, long_side=2400, crop=True):
    im = load(i)
    if crop:
        b = strip_bbox(im)
        if b: im = im.crop((b[0], b[1], b[0]+b[2], b[1]+b[3]))
    im = rotate(im, deg)
    s = long_side / max(im.size)
    if s != 1: im = im.resize((int(im.width*s), int(im.height*s)), Image.LANCZOS)
    return to_gray(im)

def job(a):
    i, deg, psm = a
    t = time.monotonic(); p = ocr(prep(i, deg), psm); dt = time.monotonic()-t
    return dict(img=i, rot=deg, psm=psm, secs=round(dt,1), **stats(p))

if __name__ == "__main__":
    jobs = [(i, d, psm) for i in DEV for d in (0,90,180,270) for psm in (6, 11)]
    with ThreadPoolExecutor(4) as ex: rows = list(ex.map(job, jobs))
    json.dump(rows, open(OUT/"exp3.json","w"), indent=1)
    for i in DEV:
        r = [x for x in rows if x["img"]==i]
        hits = sorted({(x["rot"], x["psm"], tuple(x["batch_cands"])) for x in r if x["batch_cands"]})
        lw = {d: max(x["label_words"] for x in r if x["rot"]==d) for d in (0,90,180,270)}
        print(f"{i:>3} label_words/rot {lw} | batch cands: {hits}")
    print("images with labelled batch candidate at some rotation:", sum(1 for i in DEV if any(x['batch_cands'] for x in rows if x['img']==i)), "/", len(DEV))
    print("mean secs/pass:", round(np.mean([x['secs'] for x in rows]),1))
