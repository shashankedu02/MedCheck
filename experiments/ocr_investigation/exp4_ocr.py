"""Exp 4: ink-colour band -> oriented crop -> OCR at 0 and 180 deg. Records candidates (NOT scored as correct)."""
import json, time, cv2, numpy as np
from PIL import Image
from lib import *
from crop import strip_bbox
from ink import *

def bands_for(i):
    im = load(i); b = strip_bbox(im); a = np.asarray(im)
    if b: x,y,w,h=b; a = a[y:y+h, x:x+w]
    out = []
    for bd in find_bands(a, topn=2):
        out.append(crop_rect(a, bd["rect"], bd["scale"]))
    return out

def scale_to(c, target_h=320):
    s = max(1.0, target_h / c.shape[0]); s = min(s, 8)
    return cv2.resize(c, None, fx=s, fy=s, interpolation=cv2.INTER_CUBIC)

if __name__ == "__main__":
    res = {}
    for i in DEV:
        cands = []
        for k, c in enumerate(bands_for(i)):
            if c.size == 0: continue
            g = to_gray(scale_to(c))
            for deg in (0, 180):
                gg = cv2.rotate(g, cv2.ROTATE_180) if deg else g
                for psm in (6, 11):
                    p = ocr(gg, psm); st = stats(p)
                    cands.append(dict(band=k, deg=deg, psm=psm, lines=list(p.lines)[:8], **st))
        res[i] = cands
        found = sorted({(c["deg"], tuple(c["batch_cands"]), tuple(c["exp"]), tuple(c["mfg"])) for c in cands if c["batch_cands"] or c["exp"]})
        print(i, "bands:", len(bands_for(i)), "->", found)
    json.dump(res, open(OUT/"exp4.json","w"), indent=1)
    print("with batch cand:", sum(1 for i in DEV if any(c['batch_cands'] for c in res[i])), "/", len(DEV))
