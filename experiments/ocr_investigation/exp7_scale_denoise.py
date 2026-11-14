"""Exp 7: on known-legible bands (T003,T010,T004,T013,T014), vary ONE thing at a time: scale, then denoise/binarise."""
import cv2, numpy as np
from lib import *
from exp4_ocr import bands_for

def best_orient(v, psm=6):
    res = []
    for r in range(4):
        p = ocr(np.ascontiguousarray(np.rot90(v, r)), psm); res.append((p.lines, stats(p), r))
    # orientation chosen by Tesseract's own confidence over alphabetic words, never by us knowing the answer
    return max(res, key=lambda t: (t[1]["mean_conf"] * min(t[1]["alpha_words"], 6)))

def show(tag, v):
    lines, st, r = best_orient(v)
    print(f"  {tag:<28} rot{r} conf {st['mean_conf']:>5} batch {st['batch_cands']} exp {st['exp']} | {[l[:34] for l in lines[:3]]}")

for i in (3, 10, 4, 13, 14):
    cs = bands_for(i)
    if not cs: continue
    c = max(cs, key=lambda x: x.shape[0]*x.shape[1]); g = to_gray(c)
    print(f"T{i} band {g.shape}")
    for s in (0.6, 1.0, 1.5, 2.0, 3.0):
        v = cv2.resize(g, None, fx=s, fy=s, interpolation=cv2.INTER_CUBIC if s>1 else cv2.INTER_AREA)
        show(f"scale {s} gray", v)
    v = cv2.resize(g, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
    show("2x + gauss2 + otsu", cv2.threshold(cv2.GaussianBlur(v,(0,0),2),0,255,cv2.THRESH_BINARY+cv2.THRESH_OTSU)[1])
    show("2x + median5", cv2.medianBlur(v, 5))
    bh = cv2.morphologyEx(v, cv2.MORPH_BLACKHAT, cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(15,15)))
    show("2x blackhat inv", 255 - cv2.normalize(bh, None, 0, 255, cv2.NORM_MINMAX))
    show("2x adaptive 31", cv2.adaptiveThreshold(cv2.GaussianBlur(v,(0,0),1.5),255,cv2.ADAPTIVE_THRESH_GAUSSIAN_C,cv2.THRESH_BINARY,31,12))
