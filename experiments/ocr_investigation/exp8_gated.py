"""Exp 8: foil-texture suppression. gated = luminance where chroma says 'ink', white elsewhere. Orientation chosen by label tokens."""
import cv2, numpy as np
from lib import *
from exp4_ocr import bands_for
from ink import ink_mask

def inkscore(c):
    a = c.astype(np.float32); f = a[..., 2] - (a[..., 0] + a[..., 1]) / 2
    f = cv2.GaussianBlur(f, (0, 0), 2.0)
    return f

def gated(c, soft=True):
    g = to_gray(c).astype(np.float32)
    f = inkscore(c); thr = max(np.percentile(f, 75), 15)
    m = (f > thr * 0.6).astype(np.uint8); m = cv2.dilate(m, np.ones((5, 5), np.uint8)).astype(bool)
    out = np.full_like(g, 255); out[m] = g[m]
    # contrast stretch inside mask so ink -> dark
    lo = np.percentile(g[m], 5) if m.any() else 0; hi = np.percentile(g[m], 80) if m.any() else 255
    out[m] = np.clip((g[m] - lo) / max(hi - lo, 1), 0, 1) * 255
    return out.astype(np.uint8)

def read4(v, psm=6, scale=2.0):
    v = cv2.resize(v, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
    best = None
    for r in range(4):
        p = ocr(np.ascontiguousarray(np.rot90(v, r)), psm); st = stats(p)
        key_ = (len(st["batch_cands"]) > 0, st["label_words"], st["mean_conf"])
        if best is None or key_ > best[0]: best = (key_, r, st, p.lines)
    return best

if __name__ == "__main__":
    for i in (3, 10, 4, 13, 14, 20, 22, 26):
        cs = bands_for(i)
        if not cs: print(i, "no band"); continue
        c = max(cs, key=lambda x: x.shape[0]*x.shape[1])
        for name, v in (("gray", to_gray(c)), ("gated", gated(c))):
            key_, r, st, lines = read4(v)
            print(f"T{i:<2} {name:<6} rot{r} label_words {st['label_words']} batch {st['batch_cands']} exp {st['exp']} mfg {st['mfg']} | {[l[:30] for l in lines[:3]]}")
        if i == 3: Image.fromarray(gated(c)).save(OUT/"gated3.png")
