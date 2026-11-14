"""Is strict agreement too restrictive or correctly conservative? Replay the READINGS recorded in the final V2 dev run
(run_20261114_224212) under alternative agreement policies and count what each policy would have accepted.
Reference: tier 'certain' (7) is scored, 'probable' is shown. No images are processed here."""
import csv
from collections import Counter

from lib import *  # noqa: F401,F403
from medcheck.normalization import batch_key

RUN = ROOT / "evaluation" / "results" / "runs" / "run_20261114_224212" / "evaluation_results.csv"
rows = {r["test_id"]: r for r in csv.DictReader(RUN.open(encoding="utf-8-sig"))}


def readings(tid):
    """[(raw, source)] for every report in that run."""
    out = []
    for item in filter(None, rows[tid]["batch_sources"].split(" | ")):
        raw, _, src = item.rpartition("@")
        out.append((raw, src))
    return out


def policy_strict(rs):  # current: >= 2 passes, all distinct keys must agree
    keys = Counter(batch_key(r).key for r, _ in rs)
    return next(iter(keys)) if len(keys) == 1 and sum(keys.values()) >= 2 else None


def policy_single(rs):  # accept a lone reading if no other reading exists
    keys = Counter(batch_key(r).key for r, _ in rs)
    return next(iter(keys)) if len(keys) == 1 else None


def policy_plurality(rs):  # the most frequently reported key wins (ties -> first reported)
    keys = Counter(batch_key(r).key for r, _ in rs)
    return keys.most_common(1)[0][0] if keys else None


def policy_prefer_crop(rs):  # trust the crop view over the full frame when they disagree
    crop = [r for r, s in rs if "crop_rot0" in s]
    return batch_key(crop[0]).key if crop else policy_plurality(rs)


def policy_confusable(rs):  # treat look-alike-equivalent readings (S/5, O/0, I/1/L, B/8) as agreeing; show the first
    keys = {batch_key(r).confusable_key for r, _ in rs}
    return batch_key(rs[0][0]).key if len(keys) == 1 and len(rs) >= 2 else None


POLICIES = [("strict (current)", policy_strict), ("accept a lone reading", policy_single), ("plurality vote", policy_plurality),
            ("prefer the crop view", policy_prefer_crop), ("look-alikes count as agreeing", policy_confusable)]
tids = sorted(t for t in rows if REFERENCE.get(t))
print(f"{'policy':<30} | certain refs (7): exact / WRONG accepted / abstained | probable refs (4): correct / WRONG")
for name, fn in POLICIES:
    ex = wr = ab = pc = pw = 0
    detail = []
    for t in tids:
        ref, tier = REFERENCE[t]
        rs = readings(t)
        got = fn(rs) if rs else None
        want = batch_key(ref).key
        if tier == "certain":
            if got is None: ab += 1
            elif got == want: ex += 1
            else: wr += 1; detail.append(f"{t}:{got}")
        else:
            if got is not None and got == want: pc += 1
            elif got is not None: pw += 1; detail.append(f"{t}:{got}")
    print(f"{name:<30} | {ex} / {wr} / {ab}{'':<28} | {pc} / {pw}   {('wrong: ' + ', '.join(detail)) if detail else ''}")
print("\nReadings per photo with a reference:")
for t in tids:
    print(f"  {t} ref {REFERENCE[t][0]} ({REFERENCE[t][1]}): {[r for r, _ in readings(t)]}")
