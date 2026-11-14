import cv2, numpy as np
from PIL import Image, ImageDraw
from lib import *
from crop import strip_bbox
tiles = []
for i in DEV:
    im = load(i); b = strip_bbox(im)
    t = im.copy(); d = ImageDraw.Draw(t)
    if b: d.rectangle([b[0], b[1], b[0]+b[2], b[1]+b[3]], outline=(255,0,0), width=14)
    t.thumbnail((380, 380)); c = Image.new("RGB", (380, 380), "white"); c.paste(t); ImageDraw.Draw(c).text((4,4), f"{i} {b and (b[2],b[3])}", fill=(255,0,0))
    tiles.append(c)
cols = 5; rows = (len(tiles)+cols-1)//cols
sheet = Image.new("RGB", (cols*380, rows*380), "white")
for k, t in enumerate(tiles): sheet.paste(t, ((k%cols)*380, (k//cols)*380))
sheet.save(OUT / "exp2_bbox_sheet.png"); print(sheet.size)
