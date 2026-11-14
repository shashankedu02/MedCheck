"""Zoomed, upright crops of each dev photo's batch area so a human (me) can read the printed batch independently.
The OCR engine is used ONLY to locate the region, never to supply the text."""
import re, sys, cv2, numpy as np
from pathlib import Path
from PIL import Image, ImageDraw
sys.path.insert(0, str(Path(__file__).parent))
from crop import strip_bbox
from rapidocr_onnxruntime import RapidOCR
HELDOUT = {9,12,15,18,21,24,27}; DEV = [i for i in range(1,28) if i not in HELDOUT]
P = Path(__file__).resolve().parents[2]/"evaluation"/"incoming_photos"; OUT = Path(__file__).parent/"out"
eng = RapidOCR(); LBL = re.compile(r"B\.?\s?N[O0]|BATCH", re.I)
tiles = {}
for i in DEV:
    im = Image.open(P/f"{i}.jpeg").convert("RGB"); b = strip_bbox(im)
    base = np.asarray(im)[b[1]:b[1]+b[3], b[0]:b[0]+b[2]] if b else np.asarray(im)
    pick = None
    for r in range(4):
        rot = np.ascontiguousarray(np.rot90(base, r)); res, _ = eng(rot[..., ::-1].copy())
        for box, txt, sc in (res or []):
            if LBL.search(txt): pick = (rot, np.array(box)); break
        if pick: break
    if pick:
        rot, box = pick; x0, y0 = box.min(0); x1, y1 = box.max(0); h = y1 - y0
        X0, Y0 = int(max(0, x0 - h*1.0)), int(max(0, y0 - h*1.2)); X1, Y1 = int(min(rot.shape[1], x1 + h*4)), int(min(rot.shape[0], y1 + h*2.5))
        c = rot[Y0:Y1, X0:X1]
    else:
        c = base; 
    t = Image.fromarray(c); s = min(3.0, 1000 / t.width); t = t.resize((int(t.width*s), int(t.height*s)), Image.LANCZOS)
    t.thumbnail((1000, 330)); d = ImageDraw.Draw(t); d.rectangle([0,0,60,16], fill="yellow"); d.text((3,2), f"T{i}", fill="black")
    tiles[i] = t
for n, grp in enumerate([DEV[0:7], DEV[7:14], DEV[14:]]):
    sh = Image.new("RGB", (1000, sum(tiles[i].height+8 for i in grp)), "white"); y = 0
    for i in grp: sh.paste(tiles[i], (0, y)); y += tiles[i].height + 8
    sh.save(OUT/f"ref_sheet_{n}.png"); print(n, sh.size, grp)
