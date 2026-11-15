"""Five-scene cinematic story (medcheck_ui): configuration, the illustrative text, scroll handling and visual-claim rules.

The WebGL rendering itself is verified in a real browser (docs/UI_UX_GUIDELINES.md, manual checklist); these tests pin
everything that can be checked without a GPU so the story cannot silently drift from the safety rules."""
from __future__ import annotations

import re
from pathlib import Path

from rapidfuzz.distance import Levenshtein

from medcheck.dataset import load_dataset
from medcheck.normalization import batch_key
from medcheck_ui import scene as scene_mod
from medcheck_ui import theme

ROOT = Path(__file__).resolve().parent.parent
JS = scene_mod.script()
STAGES = (ROOT / "medcheck_ui" / "assets" / "stages.js").read_text(encoding="utf-8")
CORE = (ROOT / "medcheck_ui" / "assets" / "scene.js").read_text(encoding="utf-8")


# ---------------- five scenes, one clock ----------------
def test_five_scenes_are_configured_consistently_everywhere():
    js_scenes = re.search(r"const SCENES = \[([^\]]+)\]", CORE).group(1)
    ids = tuple(re.findall(r"'(\w+)'", js_scenes))
    assert ids == scene_mod.SCENES == tuple(s[0] for s in theme.SCENES) and len(ids) == 5
    html = theme.story_html(220, "AUG-2026")
    assert re.findall(r'<section class="mc-scene" id="mc-scene-(\d)" data-scene="\d" data-id="(\w+)"', html) == [(str(i), s) for i, s in enumerate(ids, 1)]
    assert html.count('<nav class="mc-dots"') == 1 and len(re.findall(r'href="#mc-scene-\d"', html)) == 5
    assert len(theme.HEIGHTS_VH) == 5 and all(h >= 100 for h in theme.HEIGHTS_VH)


def test_camera_path_covers_the_whole_clock_in_order():
    ts = [float(x) for x in re.findall(r"\{ t: ([\d.]+), p:", CORE)]
    assert ts[0] == 0.0 and ts[-1] == 5.5 and ts == sorted(ts) and len(set(ts)) == len(ts)
    # a keyframe inside every scene (t in [k, k+1)) so no scene is flown through unguided
    assert all(any(k <= t < k + 1 for t in ts) for k in range(5))
    assert "crom(" in CORE and "KEYS[" in CORE                       # Catmull-Rom spline: no abrupt camera jumps


def test_scroll_drives_the_clock_with_inertia_and_survives_nan():
    assert ".mc-scene" in CORE and "getAnchors" in CORE and "scrollTop" in CORE and "data-testid=\"stMain\"" in CORE
    assert "Math.exp(-Math.min(dt, 0.25)" in CORE                   # damping toward the scroll target: fast or reverse scrolling stays continuous
    assert "Number.isFinite(tgt)" in CORE and "Number.isFinite(dt)" in CORE
    assert "const clamp = (v, a = 0, b = 1)" in STAGES              # a one-argument clamp once produced NaN: keep the default bounds
    assert "forceT" in CORE                                          # the diagnostic hook used for the browser screenshots
    # every object is a function of the clock t only (reversible): stages read ctx.t, never accumulate state per frame
    assert "ctx.t = cur.t" in CORE and "win(c.t" in STAGES


def test_clear_navigation_to_the_tool_exists_and_nothing_forces_the_story():
    html = theme.story_html(220, "AUG-2026")
    assert 'class="mc-skip" href="#mc-tool"' in html and html.count('href="#mc-tool"') >= 3 and 'id="mc-tool"' in html
    assert "aria-label" in html                                      # dots are labelled for assistive technology
    assert 'html:not([data-mc-stage="3d"]) .mc-scene' in theme.css()


# ---------------- the illustrative text is not a real batch ----------------
def test_illustrative_batch_is_not_in_or_near_the_cdsco_dataset():
    lines = re.search(r"lines: \[([^\]]+)\]", STAGES).group(1)
    lot = [x for x in re.findall(r"'([^']+)'", lines) if x.startswith("Lot.")][0]
    shown = batch_key(lot[len("Lot."):].strip()).key
    assert shown == "XQ240001"
    index = load_dataset()
    keys = [batch_key(r.batch_number).key for r in index.records]
    assert shown not in keys
    assert min(Levenshtein.distance(shown, k) for k in keys) > 2, "must not even be a near-neighbour of a listed batch"
    # and no listed batch string appears anywhere in the browser module
    assert not [k for k in keys if len(k) >= 6 and k in JS.upper().replace(" ", "")]


def test_water_scene_is_labelled_as_an_illustration():
    _id, _n, _e, title, body = theme.scene_texts("AUG-2026")[1]
    assert "illustration" in body.lower() and "does not test" in body.lower()
    assert "dissolv" in body.lower()                                 # says plainly that MedCheck does not dissolve or analyse anything


# ---------------- no data leaves, nothing is stored, no fake results ----------------
def test_browser_module_makes_no_requests_and_stores_nothing():
    for forbidden in ("fetch(", "XMLHttpRequest", "WebSocket", "sendBeacon", "localStorage", "sessionStorage", "indexedDB", "FileReader",
                      "mediaDevices", "document.cookie", "navigator.geolocation"):
        assert forbidden not in JS, forbidden
    assert "import(" in JS and JS.count("import(") == 1             # the single dynamic import is the local Three.js file
    for secret in ("TG261185", "Linezolid", "batch_raw", "ocr", "OCR text"):
        assert secret.lower() not in STAGES.lower().replace("ocr engine", "") or secret.lower() == "ocr"


def test_no_check_marks_shields_or_success_claims_in_the_visuals():
    raw = JS + theme.css() + theme.story_html(220, "AUG-2026")
    text = re.sub(r"not an authenticity or safety test", "", raw, flags=re.I)          # the one permitted (negated) disclaimer
    assert not re.search(r"[✓✔✅\U0001F6E1]", text)
    assert not re.search(r"\b(verified|genuine|authentic\w*|counterfeit|fake|guarantee\w*)\b", text, re.I)
    assert not re.search(r"\bsafe(ty)?\b", text, re.I)
    assert not re.search(r"match(ed)? found|success|passed|accurate", text, re.I)
    # the comparison scene is neutral: its panels carry titles and ghost rows only, never a matched record
    panels = re.search(r"function buildPanels(.+?)\n}\n", STAGES, re.S).group(1)
    assert "NSQ LIST" in panels and "INSPECTED BATCH" in panels and "matched" not in panels.lower()


def test_scanning_is_tied_to_the_real_phase_not_a_timer():
    assert "scanning ? SCAN_T" in CORE and "phase === 'scanning'" in CORE
    # the reading panel is an INDETERMINATE bar (a looping shimmer): no percentage, no counter, no step text
    hud = re.search(r"hud\.innerHTML = '(.*?)';", CORE).group(1)
    assert "Reading the photo on this computer" in hud and not re.search(r"\d|%", hud)
    assert "@keyframes mc-indet" in theme.css() and "animation: mc-indet" in theme.css()
