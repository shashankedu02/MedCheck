"""Broader sweep to find a crop of T003 where BOTH views consistently read HLA50019 (S misread as 5), using the production
pipeline only. Variables: crop margin x downscale factor x JPEG re-encode (a phone-screenshot-like crop). Dev photo only."""
import io

from PIL import Image

from lib import *  # noqa: F401,F403
from medcheck import pipeline as pl
from medcheck.normalization import batch_key

pipe = pl.MedCheckPipeline.load()
pipe.warm_up()
src = Image.open(photo_path(3)).convert("RGB")
W, H = src.size
x0, y0, x1, y1 = 270, 1029, 1200, 1396
found = []
print(f"{'crop':<18}{'scale':>6}  result")
for mx, my in ((100, 100), (200, 150), (250, 250), (400, 300)):
    base = src.crop((max(0, x0 - mx), max(0, y0 - my), min(W, x1 + mx), min(H, y1 + my)))
    for scale in (1.0, 0.8, 0.6):
        im = base.resize((int(base.width * scale), int(base.height * scale)), Image.LANCZOS) if scale != 1 else base
        buf = io.BytesIO(); im.save(buf, "JPEG", quality=80)
        r = pipe.check(buf.getvalue())
        if r.rejection is not None:
            print(f"+{mx}/{my:<12}{scale:>6}  rejected ({r.rejection.code})"); continue
        b = r.extraction.batch
        reads = [raw for raw, _s in b.reading_sources]
        tag = ""
        if b.raw and batch_key(b.raw).key == "HLA50019":
            tag = "   <== CONSISTENT HLA50019"; found.append((mx, my, scale))
        print(f"+{mx}/{my:<12}{scale:>6}  {b.state.value:<9} {r.decision.headline:<16} reads={reads}{tag}")
print("\nreproductions:", found or "none in this sweep")
