import cv2, numpy as np
from PIL import Image
from lib import *
from exp4_ocr import bands_for, scale_to
for i in (10, 4):
    bs = bands_for(i)
    for k, c in enumerate(bs):
        Image.fromarray(c).save(OUT/f"dbg{i}_{k}.png"); print(i, k, c.shape)
        g = to_gray(scale_to(c))
        for deg in (0, 90, 180, 270):
            gg = np.rot90(g, deg//90)
            for psm in (6, 7, 11):
                p = ocr(np.ascontiguousarray(gg), psm); print(i, k, deg, psm, [l[:40] for l in p.lines][:4])
