"""A/B: is running Tesseract concurrently with RapidOCR actually faster? Interleaved (ABCABC) so drifting background load hits
every mode equally. Modes: sequential | concurrent | concurrent with Tesseract limited to 2 OpenMP threads.
Reports best-of-rounds per photo and totals; also asserts that the decision is identical in every mode."""
import os
import statistics
import time

from lib import *  # noqa: F401,F403
from medcheck import config
from medcheck import pipeline as pl

PHOTOS_USED = [3, 6, 13, 14, 10, 2, 16, 26]
ROUNDS = 3
pipe = pl.MedCheckPipeline.load()
pipe.warm_up()
pipe.check(photo_bytes(6))  # settle caches

MODES = [("sequential", False, None), ("concurrent", True, None), ("concurrent+OMP2", True, "2")]
times = {m[0]: {i: [] for i in PHOTOS_USED} for m in MODES}
decisions = {}
for rnd in range(ROUNDS):
    for i in PHOTOS_USED:
        data = photo_bytes(i)
        for name, conc, omp in MODES:
            config.TESSERACT_CONCURRENT = conc
            if omp: os.environ["OMP_THREAD_LIMIT"] = omp
            else: os.environ.pop("OMP_THREAD_LIMIT", None)
            t = time.perf_counter(); r = pipe.check(data); dt = time.perf_counter() - t
            times[name][i].append(dt)
            decisions.setdefault(i, set()).add((r.decision.headline, r.extraction.batch.state.value, r.extraction.batch.raw))
os.environ.pop("OMP_THREAD_LIMIT", None); config.TESSERACT_CONCURRENT = True

print(f"{'photo':>6} | " + " | ".join(f"{m[0]:>16}" for m in MODES) + "   (best of %d / median)" % ROUNDS)
for i in PHOTOS_USED:
    print(f"T{i:03d}   | " + " | ".join(f"{min(times[m[0]][i]):5.1f}s /{statistics.median(times[m[0]][i]):5.1f}s" for m in MODES))
print("TOTAL  | " + " | ".join(f"{sum(min(v) for v in times[m[0]].values()):7.1f}s best  " for m in MODES))
print("TOTAL  | " + " | ".join(f"{sum(statistics.median(v) for v in times[m[0]].values()):7.1f}s median" for m in MODES))
print("decision identical in every mode and round for every photo:", all(len(s) == 1 for s in decisions.values()))
