"""Exp 6: chroma LOCATES the ink band; OCR runs on sharp luminance of that band. 4 rotations, psm 6; variants gray/clahe/otsu."""
import json, cv2, numpy as np
from concurrent.futures import ThreadPoolExecutor
from lib import *
from exp4_ocr import bands_for

def variants(c):
    g = to_gray(c); s = min(8, max(1.0, 300 / g.shape[0])); g = cv2.resize(g, None, fx=s, fy=s, interpolation=cv2.INTER_CUBIC)
    cl = cv2.createCLAHE(2.0, (8, 8)).apply(g)
    ot = cv2.threshold(cv2.GaussianBlur(g, (0,0), 1.2), 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
    return {"gray": g, "clahe": cl, "otsu": ot}

def job(i):
    out = []
    for k, c in enumerate(bands_for(i)):
        if c.size == 0 or min(c.shape[:2]) < 8: continue
        for vn, v in variants(c).items():
            for r in range(4):
                p = ocr(np.ascontiguousarray(np.rot90(v, r)), 6)
                st = stats(p); out.append(dict(img=i, band=k, var=vn, rot90=r, **st, lines=list(p.lines)[:6]))
    return out

if __name__ == "__main__":
    with ThreadPoolExecutor(4) as ex: allr = list(ex.map(job, DEV))
    flat = [x for r in allr for x in r]
    json.dump(flat, open(OUT/"exp6.json","w"), indent=1)
    for i, r in zip(DEV, allr):
        hits = sorted({(x["var"], x["rot90"], tuple(x["batch_cands"]), tuple(x["exp"]), tuple(x["mfg"])) for x in r if x["batch_cands"]})
        print(i, "bands", len({x['band'] for x in r}), hits[:6])
    print("images with a labelled batch candidate:", sum(1 for r in allr if any(x['batch_cands'] for x in r)), "/", len(DEV))
    for v in ("gray","clahe","otsu"):
        print(v, "images:", sum(1 for r in allr if any(x['batch_cands'] for x in r if x['var']==v)))
