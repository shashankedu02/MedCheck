"""Read-only: the reporter's photo under the D-026 policy. python verify_user_crop_policy.py <path>"""
import sys
from lib import *  # noqa: F401,F403
from medcheck import pipeline as pl

data = open(sys.argv[1], "rb").read()  # read-only; nothing is copied or kept
pipe = pl.MedCheckPipeline.load(); pipe.warm_up()
r = pipe.check(data)
print("1. photo checked:", r.decision.headline, f"[{r.decision.reason_code}] | batch {r.extraction.batch.state.value} {r.extraction.batch.raw!r}")
print("   status line:", r.decision.explanation[:260], "...")
for label, text, ok in (("2. user cannot confirm (presses the button, no tick)", "HLA50019", False),
                        ("3. user compares with the pack, corrects S, ticks", "HLAS0019", True),
                        ("4. user ticks the OCR value WITHOUT looking (their responsibility)", "HLA50019", True)):
    x = pipe.verify_manual(r, text, ok)
    print(f"{label}:\n   -> {x.decision.headline} [{x.decision.reason_code}] source={x.manual.source.value} confirmed={x.decision.batch_confirmed}")
    if x.decision.status.value == "No alert found": print("   ", x.decision.explanation[-110:])
