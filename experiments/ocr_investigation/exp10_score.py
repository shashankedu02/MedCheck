"""Exp 10 (scratch venv w/ rapidocr). Score OCR configs against the independent human reference (dev photos only)."""
import re, sys, time, json, cv2, numpy as np
from pathlib import Path
from PIL import Image
HERE = Path(__file__).parent; ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(ROOT))
from crop import strip_bbox
from medcheck.extraction import extract_from_lines
from medcheck.normalization import batch_key
from rapidocr_onnxruntime import RapidOCR
HELDOUT = {9,12,15,18,21,24,27}; DEV = [i for i in range(1,28) if i not in HELDOUT]
CERTAIN = {3:"HLAS0019", 6:"5BA1617", 10:"BEC1106", 11:"5BA1447", 13:"25S3GCA146", 14:"CP50097", 26:"18261604A"}
PROBABLE = {4:"INA26003", 16:"SIL536", 22:"SIN552"}
eng = RapidOCR(); P = ROOT/"evaluation"/"incoming_photos"
GLUE = re.compile(r"B\.?\s?N[O0]\.?[:;\-\s]*([A-Z0-9][A-Z0-9\s\-/]{1,20}?)(?=MF[GD]|M\.?R\.?P|EXP|RS\.?|PER|$|\s{2,})", re.I)

def proto_batch(lines):
    """Prototype glue-aware extractor: label then chars up to an embedded next-label (OCR drops spaces)."""
    out = []
    for l in lines:
        m = re.search(r"B\.?\s?N[O0]\.?[:;\-\s]*", l, re.I)
        if not m: continue
        rest = l[m.end():]
        mm = re.search(r"(MF[GD]|M\.?R\.?P|EXP|\bRS\b|PER\b|INCL)", rest, re.I)
        tok = (rest[:mm.start()] if mm else rest).strip(" :;.-").split(" ")[0]
        k = batch_key(tok).key
        if len(k) >= 4 and any(c.isdigit() for c in k): out.append(k)
    return out

def ocr_lines(img_bgr):
    t = time.monotonic(); res, _ = eng(img_bgr); return [r[1] for r in (res or [])], time.monotonic() - t

def configs(im):
    a = np.asarray(im)[..., ::-1].copy(); b = strip_bbox(im)
    crop = a[b[1]:b[1]+b[3], b[0]:b[0]+b[2]] if b else a
    return {"full_r0": [a], "crop_r0": [crop], "crop_4rot": [np.ascontiguousarray(np.rot90(crop, r)) for r in range(4)],
            "full_4rot": [np.ascontiguousarray(np.rot90(a, r)) for r in range(4)]}

rows = {}
for i in DEV:
    im = Image.open(P/f"{i}.jpeg").convert("RGB"); rows[i] = {}
    for name, imgs in configs(im).items():
        allk, prod, tt = [], [], 0
        for g in imgs:
            lines, dt = ocr_lines(g); tt += dt
            allk += proto_batch(lines)
            prod += [batch_key(x).key for x in extract_from_lines(lines).batch_candidates]
        rows[i][name] = dict(proto=sorted(set(allk)), prod=sorted(set(prod)), secs=round(tt, 1))
json.dump(rows, open(HERE/"out"/"exp10.json", "w"), indent=1)

def score(name, which):
    ok = wrong = miss = 0
    for i, ref in CERTAIN.items():
        c = rows[i][name][which]
        if ref in c and len(c) == 1: ok += 1          # exactly the reference, no competing readings
        elif ref in c: wrong += 0; ok += 0; miss += 0
        elif c: wrong += 1
        else: miss += 1
    ambiguous = sum(1 for i, ref in CERTAIN.items() if ref in rows[i][name][which] and len(rows[i][name][which]) > 1)
    return ok, ambiguous, wrong, miss
print("config      extractor | exact-unique ambiguous(ref among >1) wrong-only missed  (of 7 certain)  | mean secs/img")
for name in ("full_r0", "crop_r0", "crop_4rot", "full_4rot"):
    for which in ("prod", "proto"):
        print(f"{name:<10} {which:<5} |", score(name, which), "|", round(np.mean([rows[i][name]['secs'] for i in DEV]), 1))
print("\nper-image (proto, crop_4rot) vs reference:")
for i in DEV:
    print(i, CERTAIN.get(i) or PROBABLE.get(i) and "~"+PROBABLE[i], "|", rows[i]["full_r0"]["proto"], "|", rows[i]["crop_4rot"]["proto"], "| prod full_r0:", rows[i]["full_r0"]["prod"])
