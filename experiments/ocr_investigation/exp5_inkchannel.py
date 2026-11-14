"""Exp 5: same strip crop, same rotations/psm as Exp 3, but the image given to Tesseract is an 'ink-ness' channel
(blue minus mean(red,green)) instead of plain gray. One variable changed: the channel."""
import json, time, cv2, numpy as np
from concurrent.futures import ThreadPoolExecutor
from PIL import Image
from lib import *
from crop import strip_bbox

def strip(i):
    im = load(i); b = strip_bbox(im)
    return im.crop((b[0], b[1], b[0]+b[2], b[1]+b[3])) if b else im

def inkness(rgb):
    a = rgb.astype(np.float32); f = a[..., 2] - (a[..., 0] + a[..., 1]) / 2
    f = cv2.GaussianBlur(f, (3, 3), 0)
    lo, hi = np.percentile(f, 20), np.percentile(f, 99.5)
    f = np.clip((f - lo) / max(hi - lo, 1), 0, 1)
    return (255 - f * 255).astype(np.uint8)  # dark ink on white

def prep(i, deg, mode, long_side=2400):
    im = rotate(strip(i), deg); s = long_side / max(im.size)
    im = im.resize((int(im.width*s), int(im.height*s)), Image.LANCZOS)
    a = np.asarray(im)
    return inkness(a) if mode == "ink" else to_gray(im)

def job(a):
    i, deg, psm, mode = a
    p = ocr(prep(i, deg, mode), psm); return dict(img=i, rot=deg, psm=psm, mode=mode, **stats(p), lines=list(p.lines)[:12])

if __name__ == "__main__":
    Image.fromarray(prep(3, 0, "ink")).save(OUT/"ink3.png")
    jobs = [(i, d, psm, "ink") for i in DEV for d in (0,90,180,270) for psm in (6, 11)]
    with ThreadPoolExecutor(4) as ex: rows = list(ex.map(job, jobs))
    json.dump(rows, open(OUT/"exp5.json","w"), indent=1)
    for i in DEV:
        r = [x for x in rows if x["img"]==i]
        hits = sorted({(x["rot"], tuple(x["batch_cands"]), tuple(x["exp"])) for x in r if x["batch_cands"]})
        print(f"{i:>3} label_words max {max(x['label_words'] for x in r)} | {hits}")
    print("images with labelled batch candidate:", sum(1 for i in DEV if any(x['batch_cands'] for x in rows if x['img']==i)), "/", len(DEV))
