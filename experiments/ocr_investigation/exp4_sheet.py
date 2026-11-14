import cv2, numpy as np
from PIL import Image
from lib import *
from crop import strip_bbox
from ink import *
tiles=[]
for i in DEV:
    im = load(i); b = strip_bbox(im); a = np.asarray(im)
    if b: x,y,w,h=b; a = a[y:y+h, x:x+w]
    bands = find_bands(a, topn=1)
    if not bands: print(i, "no ink band"); tiles.append(Image.new("RGB",(600,200),"gray")); continue
    c = crop_rect(a, bands[0]["rect"], bands[0]["scale"])
    print(i, "ink px", bands[0]["ink"], "band", c.shape)
    t = Image.fromarray(c); t.thumbnail((900, 260)); tiles.append(t)
H = sum(t.height+6 for t in tiles[:10]); 
for part, name in ((tiles[:10], "a"), (tiles[10:], "b")):
    sh = Image.new("RGB",(920, sum(t.height+14 for t in part)),"white"); y=0
    for t in part: sh.paste(t,(0,y)); y+=t.height+14
    sh.save(OUT/f"exp4_bands_{name}.png")
