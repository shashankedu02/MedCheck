"""Where do the seconds go? Per-stage timing of MedCheckPipeline.check on the development photos.

Part 1 (cold): a fresh pipeline; the FIRST check includes lazy RapidOCR model verification + ONNX session creation.
Part 2 (warm): every dev photo, stage by stage.
Nothing is changed in the pipeline: stages are wrapped from the outside.
"""
import json
import statistics
import time
from collections import defaultdict

from lib import *  # noqa: F401,F403
from medcheck import pipeline as pl
from medcheck import ocr_rapid

# ---------------- Part 1: cold start ----------------
cold_pipe = pl.MedCheckPipeline.load()
t = time.perf_counter(); first = cold_pipe.check(photo_bytes(6)); first_s = time.perf_counter() - t
t = time.perf_counter(); second = cold_pipe.check(photo_bytes(6)); second_s = time.perf_counter() - t
t = time.perf_counter(); ocr_rapid.verify_models(); verify_s = time.perf_counter() - t
print(f"COLD: first check {first_s:.1f}s, second check {second_s:.1f}s -> one-off start-up cost ~{first_s - second_s:.1f}s "
      f"(model hash check alone {verify_s:.2f}s)")

# ---------------- Part 2: warm, stage by stage ----------------
acc = defaultdict(list)


def wrap(obj, attr, name):
    fn = getattr(obj, attr)

    def w(*a, **k):
        t0 = time.perf_counter()
        try:
            return fn(*a, **k)
        finally:
            acc[name].append(time.perf_counter() - t0)
    setattr(obj, attr, w)


pipe = pl.MedCheckPipeline.load()
pipe._rapid.check_available()
rapid_passes = []
orig = pipe._rapid.run


def rapid_run(rgb, source):
    t0 = time.perf_counter()
    out = orig(rgb, source)
    dt = time.perf_counter() - t0
    acc["rapid"].append(dt)
    rapid_passes.append((source, round(dt, 2), rgb.shape[1], rgb.shape[0]))
    return out


pipe._rapid.run = rapid_run
for attr, name in (("load_image", "load_image"), ("detect_pack_region", "region"), ("make_variants", "tess_prep"),
                   ("run_ocr", "tesseract"), ("extract", "extract"), ("match_batch", "match")):
    wrap(pl, attr, name)

rows = []
for i in DEV:
    acc.clear(); rapid_passes.clear()
    t0 = time.perf_counter(); r = pipe.check(photo_bytes(i)); total = time.perf_counter() - t0
    row = {"img": i, "total": round(total, 2), "outcome": r.decision.headline, "passes": len(r.variants_used),
           **{k: round(sum(v), 2) for k, v in acc.items()}, "rapid_n": len(acc["rapid"]),
           "rapid_detail": list(rapid_passes)}
    rows.append(row)
    print(f"T{i:03d} total {total:5.1f}s | rapid {row.get('rapid', 0):5.1f}s ({row['rapid_n']} passes) tesseract {row.get('tesseract', 0):4.1f}s "
          f"region {row.get('region', 0):4.2f}s prep {row.get('tess_prep', 0):4.2f}s load {row.get('load_image', 0):4.2f}s | {r.decision.headline}")
json.dump(rows, open(OUT / "time_breakdown.json", "w"), indent=1)
tot = [r["total"] for r in rows]
print(f"\nWARM mean {statistics.mean(tot):.1f}s median {statistics.median(tot):.1f}s max {max(tot):.1f}s")
for k in ("rapid", "tesseract", "region", "tess_prep", "load_image", "extract", "match"):
    s = sum(r.get(k, 0) for r in rows)
    print(f"  {k:<11} {s:6.1f}s total = {100 * s / sum(tot):4.1f}% of all time")
sizes = [(d[2] * d[3]) / 1e6 for r in rows for d in r["rapid_detail"]]
rt = [d[1] for r in rows for d in r["rapid_detail"]]
print(f"  RapidOCR pass: mean {statistics.mean(rt):.2f}s over {len(rt)} passes (image {statistics.mean(sizes):.2f} Mpx on average)")
