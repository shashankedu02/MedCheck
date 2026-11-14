"""Read-only reproduction on a user-supplied photo: python repro_user_crop.py <path>
The file is read into memory and passed to the production pipeline; it is not copied, written, or kept."""
import sys

from PIL import Image

from lib import *  # noqa: F401,F403
from medcheck import pipeline as pl

path = sys.argv[1]
data = open(path, "rb").read()  # read-only
with Image.open(path) as im:
    print("image:", im.size, im.mode, "| EXIF orientation:", im.getexif().get(274))
pipe = pl.MedCheckPipeline.load()
pipe.warm_up()
for run in (1, 2):  # twice, to see whether the result is stable
    r = pipe.check(data)
    if r.rejection is not None:
        print("REJECTED:", r.rejection.code, r.rejection.message); break
    b = r.extraction.batch
    print(f"\nrun {run}: batch state = {b.state.value}, raw = {b.raw!r}")
    print("  readings with source:", list(b.reading_sources))
    print("  reason:", b.reason or "-", "| edge-ignored:", list(r.extraction.edge_ignored))
    print("  match:", r.match.outcome.value if r.match else None, "|", (r.match.reason if r.match else ""))
    print("  decision:", r.decision.headline, f"[{r.decision.reason_code}]")
    print("  dates: mfg", r.extraction.manufacturing.raw, "| exp", r.extraction.expiry.raw)
    print("  engines:", r.engines, "| passes:", r.ocr_passes, "| views:", sorted(r.variants_used), f"| {r.elapsed_seconds:.1f}s")
