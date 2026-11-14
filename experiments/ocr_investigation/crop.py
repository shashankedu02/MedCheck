"""Candidate automatic pack-region detectors (diagnostic)."""
import cv2, numpy as np

def strip_bbox(img_rgb, pad=0.03):
    """Foil/print has dense local gradients; the table/background is smooth. Return (x,y,w,h) or None."""
    g = cv2.cvtColor(np.asarray(img_rgb), cv2.COLOR_RGB2GRAY)
    s = 800 / max(g.shape)
    sm = cv2.resize(g, None, fx=s, fy=s, interpolation=cv2.INTER_AREA)
    sm = cv2.GaussianBlur(sm, (3, 3), 0)
    gx = cv2.Sobel(sm, cv2.CV_32F, 1, 0); gy = cv2.Sobel(sm, cv2.CV_32F, 0, 1)
    mag = cv2.magnitude(gx, gy)
    energy = cv2.boxFilter(mag, -1, (15, 15))
    thr = max(np.percentile(energy, 50) * 2.0, 12)
    m = (energy > thr).astype(np.uint8) * 255
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (31, 31)))
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (15, 15)))
    n, lab, st, _ = cv2.connectedComponentsWithStats(m)
    if n <= 1: return None
    k = 1 + int(np.argmax(st[1:, cv2.CC_STAT_AREA]))
    x, y, w, h, area = st[k]
    if area < 0.02 * m.size: return None
    H, W = g.shape
    x, y, w, h = [v / s for v in (x, y, w, h)]
    px, py = pad * w, pad * h
    x0, y0 = max(0, int(x - px)), max(0, int(y - py)); x1, y1 = min(W, int(x + w + px)), min(H, int(y + h + py))
    return x0, y0, x1 - x0, y1 - y0
