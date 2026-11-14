"""Does the automatic pack region contain the batch/date block? Does the edge guard cost real reads?
For every dev photo: (1) region box and area; (2) RapidOCR on the FULL frame at 0/90/180/270 deg, label lines
(B.No / Batch / MFG / MFD / EXP) mapped back to original coordinates and tested against the region;
(3) lines of the crop view that touch its edge. Diagnostic only."""
import json
import re

import numpy as np
from PIL import Image

from lib import *  # noqa: F401,F403
from medcheck.ocr_rapid import RapidEngine
from medcheck.regions import crop_to, detect_pack_region

eng = RapidEngine()
eng.warm_up()
LABEL = re.compile(r"B\.?\s?N[O0]|BATCH|MF[GD]|EXP", re.I)


def to_original(pt, rot, W, H):
    """Map a point from a view rotated by `rot` degrees counter-clockwise (PIL expand=True) back to the original."""
    x, y = pt
    if rot == 0:
        return x, y
    if rot == 90:   # view W' = H, H' = W; point (x,y) in view <- original (W-1-y, x)?  derive: PIL rotate(90) CCW
        return W - 1 - y, x
    if rot == 180:
        return W - 1 - x, H - 1 - y
    return y, H - 1 - x  # 270


rows = []
for i in DEV:
    im = Image.open(photo_path(i)).convert("RGB")
    W, H = im.size
    reg = detect_pack_region(im)
    row = {"img": i, "region": reg, "area_pct": round(100 * reg[2] * reg[3] / (W * H)) if reg else None, "labels": []}
    for rot in (0, 90, 180, 270):
        view = im.rotate(rot, expand=True) if rot else im
        out = eng.run(np.asarray(view), f"full_rot{rot}")
        for k, (line, w) in enumerate(zip(out.lines, out.words)):
            if LABEL.search(line):
                cx, cy = to_original((w.left + w.width / 2, w.top + w.height / 2), rot, W, H)
                inside = bool(reg and reg[0] <= cx <= reg[0] + reg[2] and reg[1] <= cy <= reg[1] + reg[3])
                row["labels"].append({"rot": rot, "text": line[:40], "inside": inside, "edge": k in out.edge_lines})
    # edge guard on the crop view (rot0..270)
    base = crop_to(im, reg) if reg else im
    row["crop_edge_label_lines"] = 0
    for rot in (0, 90, 180, 270):
        view = base.rotate(rot, expand=True) if rot else base
        out = eng.run(np.asarray(view), f"crop_rot{rot}")
        row["crop_edge_label_lines"] += sum(1 for k in out.edge_lines if LABEL.search(out.lines[k]))
    rows.append(row)
    n = len(row["labels"])
    ins = sum(1 for l in row["labels"] if l["inside"])
    print(f"T{i:03d} region {reg} ({row['area_pct']}% of frame) | label lines found in full frame: {n}, inside region: {ins} | "
          f"label lines touching the CROP edge: {row['crop_edge_label_lines']}")
json.dump(rows, open(OUT / "crop_assessment.json", "w"), indent=1)
tot = sum(len(r["labels"]) for r in rows); ins = sum(l["inside"] for r in rows for l in r["labels"])
print(f"\nlabel lines found anywhere in the full frame: {tot}; inside the automatic region: {ins} ({100 * ins / max(tot, 1):.0f}%)")
print("outside:", [(f"T{r['img']:03d}", l["text"]) for r in rows for l in r["labels"] if not l["inside"]][:12])
print("photos with a region:", sum(1 for r in rows if r["region"]), "of", len(rows), "| median area %:", int(np.median([r["area_pct"] for r in rows if r["area_pct"]])))
