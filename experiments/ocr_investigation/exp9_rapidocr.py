"""Exp 9 (runs in a scratch venv with rapidocr-onnxruntime; NOT the project venv). Dev photos only."""
import re, sys, time, json, cv2, numpy as np
from pathlib import Path
from PIL import Image
sys.path.insert(0, str(Path(__file__).parent))
from crop import strip_bbox
from rapidocr_onnxruntime import RapidOCR
HELDOUT = {9,12,15,18,21,24,27}; DEV = [i for i in range(1,28) if i not in HELDOUT]
P = Path(__file__).resolve().parents[2]/"evaluation"/"incoming_photos"
eng = RapidOCR()
LBL = re.compile(r"B\.?\s?N[O0]|BATCH|MF[GD]|EXP", re.I)

def run(a):
    t = time.monotonic(); res, _ = eng(a); dt = time.monotonic()-t
    lines = [r[1] for r in (res or [])]
    return lines, dt

out = {}
for i in DEV:
    im = Image.open(P/f"{i}.jpeg").convert("RGB"); a = np.asarray(im)[..., ::-1].copy()  # BGR
    b = strip_bbox(im); crop = a[b[1]:b[1]+b[3], b[0]:b[0]+b[2]] if b else a
    rec = {}
    for name, img in (("full", a), ("crop", crop)):
        best = None
        for r in (0, 1, 2, 3):
            lines, dt = run(np.ascontiguousarray(np.rot90(img, r)))
            hits = [l for l in lines if LBL.search(l)]
            sc = len(hits)
            if best is None or sc > best[0]: best = (sc, r, hits, dt, len(lines))
        rec[name] = dict(score=best[0], rot=best[1], hits=best[2][:6], secs=round(best[3],1), n=best[4])
        r0, _ = run(img); rec[name]["rot0_hits"] = [l for l in r0 if LBL.search(l)][:6]
    out[i] = rec
    print(i, "full rot0:", rec["full"]["rot0_hits"], "| crop rot0:", rec["crop"]["rot0_hits"], "| crop best-of-4 rot", rec["crop"]["rot"], rec["crop"]["hits"])
json.dump(out, open(Path(__file__).parent/"out"/"exp9.json","w"), indent=1)
print("images with label hits: full rot0", sum(1 for i in out if out[i]['full']['rot0_hits']), "crop rot0", sum(1 for i in out if out[i]['crop']['rot0_hits']),
      "crop best-of-4", sum(1 for i in out if out[i]['crop']['score']), "/", len(out))
