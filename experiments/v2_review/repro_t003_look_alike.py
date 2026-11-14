"""Reproduce: T003 (loosely cropped) -> batch read as HLA50019 -> 'No alert found'.
Uses ONLY the production pipeline (MedCheckPipeline.check) on loose crops of the original T003 photo (a dev photo; the
reserved photographs are never touched). The reporter's own crop file is not in the repository, so crops with several
margins are tried. Prints, for each crop, what each engine pass read and what the decision was."""
import io

from PIL import Image

from lib import *  # noqa: F401,F403
from medcheck import pipeline as pl
from medcheck.matching import DatasetIndex, match_batch
from medcheck.normalization import batch_key
from rapidfuzz.distance import Levenshtein

pipe = pl.MedCheckPipeline.load()
pipe.warm_up()
src = Image.open(photo_path(3)).convert("RGB")
W, H = src.size
STRIP = (270, 1029, 1200, 1396)  # the strip in the original frame (x0, y0, x1, y1)


def loose(margin_x, margin_y, bottom_extra=0):
    x0, y0, x1, y1 = STRIP
    return src.crop((max(0, x0 - margin_x), max(0, y0 - margin_y), min(W, x1 + margin_x), min(H, y1 + margin_y + bottom_extra)))


CROPS = {
    "tight (strip only)": loose(0, 0),
    "loose +60px": loose(60, 60),
    "loose +150px": loose(150, 150),
    "loose +300px": loose(300, 300),
    "loose +300 wide, +200 up": loose(300, 200),
    "upper-left half of frame + strip": src.crop((0, 700, W, H)),
    "bottom 40% of frame": src.crop((0, int(H * 0.6), W, H)),
}

print("=== 1. production pipeline on loose crops of T003 ===")
hits = []
for name, im in CROPS.items():
    buf = io.BytesIO(); im.save(buf, "PNG")
    r = pipe.check(buf.getvalue())
    if r.rejection is not None:
        print(f"{name:<34} {im.size}: REJECTED ({r.rejection.code})"); continue
    b = r.extraction.batch
    print(f"{name:<34} {im.size}: batch {b.state.value:<9} raw={b.raw!r:<12} -> {r.decision.headline}")
    print(f"     readings: {[(raw, src_) for raw, src_ in b.reading_sources]}  note: {b.reason}")
    if b.raw and batch_key(b.raw).key == "HLA50019":
        hits.append(name)
print("\ncrops that reproduce a CONSISTENT read of HLA50019:", hits or "none among these crops")

print("\n=== 2. why is no listed batch involved? distance from both strings to every listed batch ===")
idx = pipe.index
for s in ("HLAS0019", "HLA50019"):
    k = batch_key(s)
    best = min((Levenshtein.distance(k.key, bk.key), serial) for serial, bk in idx.keys.items())
    print(f"{s}: confusable key {k.confusable_key}; nearest listed batch is serial {best[1]} ({idx.keys[best[1]].key}) at edit distance {best[0]}; "
          f"match outcome vs the real dataset: {match_batch(idx, k, '').outcome.value}")

print("\n=== 3. the look-alike safeguard against LISTED batches: add the true batch to a copy of the dataset (synthetic) ===")
from dataclasses import replace
from medcheck.dataset import Dataset, DatasetRecord
real = pipe.dataset
fake = DatasetRecord(999, "Hicet-L Levocetirizine Tablets IP 5 mg", "HLAS0019", "07/2025", "06/2028", "Micro Labs Ltd", "NSQ", "test", "test", "AUG-2026")
syn = DatasetIndex.build(replace(real, records=(*real.records, fake)))
for s in ("HLA50019", "HLAS0019", "HLAS50019", "HLA5O019"):
    m = match_batch(syn, batch_key(s), "Hicet-L Levocetirizine Tablets IP")
    print(f"if HLAS0019 WERE listed, a consistent read of {s!r}: {m.outcome.value:<14} | {m.evidence[0][:100] if m.evidence else m.reason}")
