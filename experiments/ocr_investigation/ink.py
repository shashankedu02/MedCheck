"""Locate stamped batch/date ink (blue/violet) on a pack crop; return oriented band crops (diagnostic)."""
import cv2, numpy as np
from crop import strip_bbox

def ink_mask(rgb, smin=70, vmin=40, hlo=105, hhi=150):
    hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)
    h, s, v = hsv[..., 0], hsv[..., 1], hsv[..., 2]
    return ((h >= hlo) & (h <= hhi) & (s >= smin) & (v >= vmin)).astype(np.uint8) * 255

def find_bands(rgb, topn=3, work=1600):
    """Return list of dicts {rect, crop(rgb, upright-ish), score} for the densest ink clusters."""
    sc = work / max(rgb.shape[:2]); small = cv2.resize(rgb, None, fx=sc, fy=sc, interpolation=cv2.INTER_AREA)
    m = ink_mask(small)
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((2, 2), np.uint8))
    k = max(9, int(small.shape[1] * 0.014))
    d = cv2.dilate(m, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k)))
    n, lab, st, _ = cv2.connectedComponentsWithStats(d)
    out = []
    for c in range(1, n):
        x, y, w, h, area = st[c]
        ink = int((m[lab == c] > 0).sum())
        if ink < 150 or max(w, h) < 40: continue
        out.append((ink, c))
    out.sort(reverse=True)
    res = []
    for ink, c in out[:topn]:
        pts = cv2.findNonZero(((lab == c) & (m > 0)).astype(np.uint8))
        rect = cv2.minAreaRect(pts)  # (cx,cy),(w,h),angle in small coords
        res.append(dict(ink=ink, rect=rect, scale=sc))
    return res

def crop_rect(rgb, rect, scale, margin=0.5, axial=0.4):
    """Warp the rotated rect (from find_bands) out of the full-res image, long axis horizontal."""
    (cx, cy), (w, h), ang = rect
    cx, cy, w, h = cx/scale, cy/scale, w/scale, h/scale
    if w < h: ang += 90; w, h = h, w
    w2, h2 = w*(1+axial*2), h*(1+margin*2)  # a little slack so label words at the line start are kept
    M = cv2.getRotationMatrix2D((cx, cy), ang, 1.0)
    rot = cv2.warpAffine(rgb, M, (rgb.shape[1], rgb.shape[0]), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
    x0, y0 = int(max(0, cx - w2/2)), int(max(0, cy - h2/2)); x1, y1 = int(min(rgb.shape[1], cx + w2/2)), int(min(rgb.shape[0], cy + h2/2))
    return rot[y0:y1, x0:x1]
