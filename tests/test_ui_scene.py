"""3D interface (medcheck_ui): frontend-only guarantees.

Covers the audit items (static serving configured, component lifecycle cleanup, canvas resize/aspect, theme contrast,
commit-independent provenance of the vendored library), the privacy boundary of the browser component, the plain-UI
safety net and the wording rules. WebGL itself is verified in a real browser (docs/UI_UX_GUIDELINES.md, manual checklist)."""
from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from medcheck.models import Decision, Status, SystemFailure
from medcheck_ui import plain_ui
from medcheck_ui import scene as scene_mod
from medcheck_ui import theme

ROOT = Path(__file__).resolve().parent.parent
APP = str(ROOT / "app.py")
JS = (ROOT / "medcheck_ui" / "assets" / "scene.js").read_text(encoding="utf-8")
BANNED = re.compile(r"\b(safe|genuine|authentic\w*|counterfeit|fake|guarantee\w*)\b", re.I)
ALLOWED_NEGATIONS = ("not an authenticity or safety test",)


# ---------------- configuration: static serving, localhost, theme ----------------
def test_config_serves_local_static_files_and_stays_local():
    cfg = (ROOT / ".streamlit" / "config.toml").read_text(encoding="utf-8")
    assert "enableStaticServing = true" in cfg  # the audit finding: previously only a command-line flag in the trial
    assert 'address = "localhost"' in cfg and "gatherUsageStats = false" in cfg and "maxUploadSize = 10" in cfg
    assert (ROOT / "static").is_dir()


def test_javascript_content_type_is_explicit():
    import mimetypes
    assert mimetypes.guess_type("x.js")[0] == "text/javascript"  # a registry mapping .js to text/plain would break the module


# ---------------- vendored Three.js ----------------
def test_vendored_three_matches_its_pinned_hash_and_ships_the_licence():
    d = ROOT / "static" / "vendor" / "three"
    meta = json.loads((d / "VENDOR.json").read_bytes())
    assert meta["version"] == "0.170.0" and meta["npm_integrity"].startswith("sha512-")
    for name, info in meta["files"].items():
        assert hashlib.sha256((d / name).read_bytes()).hexdigest() == info["sha256"], name
    assert b"MIT License" in (d / "LICENSE").read_bytes()
    assert b"-text" in (ROOT / ".gitattributes").read_bytes() and b"static/vendor/** -text" in (ROOT / ".gitattributes").read_bytes()


def test_no_remote_urls_in_the_ui_assets_or_theme():
    css_and_html = theme._CSS + theme.hero_html() + theme.steps_html()
    for text in (JS, css_and_html):
        urls = [u for u in re.findall(r"https?://[^\s'\"<>)]+", text) if "www.w3.org/2000/svg" not in u]
        assert urls == [], urls
    assert "import(" in JS and "app/static/vendor/three/three.module.min.js" in JS  # local, relative to the page origin
    assert "cdn" not in (JS + css_and_html).lower() and "@import" not in css_and_html and "fonts.googleapis" not in css_and_html


# ---------------- lifecycle, resize, fallbacks (static contract of the browser code) ----------------
def test_component_releases_its_resources_and_resizes_with_the_viewport():
    assert "st.dispose" in JS and "forceContextLoss" in JS and "renderer.dispose()" in JS and "canvas.remove()" in JS
    assert "cancelAnimationFrame" in JS and "removeEventListener" in JS
    # every texture and render target is registered with track() and released by st.free; overlays are removed too
    assert "track(envTarget)" in JS and "disposables.forEach((d) =>" in JS and JS.count("track(") >= 6
    assert "hud.remove()" in JS and "brackets.remove()" in JS
    assert "return st.makeCleanup()" in JS and "st.calls === id" in JS  # an older instance never disposes a newer mount
    assert "addEventListener(ev, fn, o)" in JS and "'resize'" in JS and "camera.aspect = w / h" in JS and "updateProjectionMatrix()" in JS


def test_fallbacks_and_frame_cap_exist():
    assert "prefers-reduced-motion" in JS and "webglcontextlost" in JS and "WebGL is not available" in JS
    assert "data-mc-stage" in JS and "'fallback'" in JS
    assert re.search(r"cap = st\.state\.phase === 'scanning' \? 50 : 33", JS)  # 20 fps while scanning, ~30 fps otherwise
    assert "document.hidden" in JS  # paused in a background tab
    # still artwork shown unless 3D runs (a CSS data-URI background: st.html strips inline <svg>)
    assert 'html[data-mc-stage="3d"] .mc-art-fallback' in theme._CSS and "data:image/svg+xml" in theme.css()
    assert 'class="mc-art-fallback"' in theme.hero_html()
    assert "prefers-reduced-motion: reduce" in theme._CSS


# ---------------- privacy boundary: the component only ever gets a phase and a status name ----------------
def test_payload_is_a_closed_set():
    assert scene_mod.ALLOWED_FIELDS == ("phase", "status")
    assert scene_mod.scene_payload("idle") == {"phase": "idle", "status": None}
    assert scene_mod.scene_payload("scanning", "alert") == {"phase": "scanning", "status": None}  # no verdict while scanning
    assert scene_mod.scene_payload("result", "no_alert") == {"phase": "result", "status": "no_alert"}
    with pytest.raises(ValueError):
        scene_mod.scene_payload("result", "TG261185")
    with pytest.raises(ValueError):
        scene_mod.scene_payload("done")


def _decision(status, system_failure=None):
    return Decision(status=status, reason_code="x", headline="h", explanation="e", system_failure=system_failure)


def test_status_tint_mapping_never_invents_a_verdict():
    assert scene_mod.status_key(None) is None
    assert scene_mod.status_key(_decision(Status.ALERT_FOUND)) == "alert"
    assert scene_mod.status_key(_decision(Status.NO_ALERT_FOUND)) == "no_alert"
    assert scene_mod.status_key(_decision(Status.UNABLE_TO_VERIFY)) == "unable"
    assert scene_mod.status_key(_decision(Status.EXPIRED)) == "unable"
    assert scene_mod.status_key(_decision(None, SystemFailure.INTERNAL)) == "error"
    assert set(scene_mod.STATUSES) == {"alert", "unable", "no_alert", "error"}
    # no_alert is a calm cyan: the green channel must not dominate the colour (no "all clear" green)
    m = re.search(r"no_alert: \[([\d.]+), ([\d.]+), ([\d.]+)\]", JS)
    r, g, b = map(float, m.groups())
    assert b >= g > r


def _components(at):
    return [n for n in at.main if type(n).__name__ == "UnknownElement" and getattr(n, "type", "") == "bidi_component"]


def test_browser_component_never_receives_photo_text_or_batch(monkeypatch):
    from tests.test_app import extraction, result_for  # reuse the rendering fixtures (batch TG261185, product text)
    from medcheck.dataset import load_dataset
    from medcheck.models import MatchOutcome

    record = next(r for r in load_dataset().records if r.serial == 4)
    at = AppTest.from_file(APP, default_timeout=30)
    at.session_state["result"] = result_for(MatchOutcome.CONFIRMED, serial=4, record=record)
    at.session_state["result_digest"] = None
    at.run()
    assert not at.exception, [e.value for e in at.exception]
    comps = _components(at)
    assert len(comps) == 1
    payload = json.loads(comps[0].proto.json)
    assert set(payload) <= set(scene_mod.ALLOWED_FIELDS) and payload == {"phase": "result", "status": "alert"}
    blob = comps[0].proto.json + comps[0].proto.component_name
    for secret in ("TG261185", "Linzotal", "Linezolid", "04/2028", "Serial"):
        assert secret not in blob


def test_several_mounts_in_one_script_run_do_not_raise():
    """The app mounts the stage for idle, scanning and result within one run; Streamlit rejects duplicate keys."""
    def script():
        import streamlit as st
        from medcheck_ui.scene import render_scene
        slot = st.empty()
        render_scene(slot, "idle")
        render_scene(slot, "scanning")
        render_scene(slot, "result", "unable")
    at = AppTest.from_function(script, default_timeout=30).run()
    assert not at.exception, [e.value for e in at.exception]


# ---------------- plain-UI safety net ----------------
def test_plain_ui_switch(monkeypatch):
    monkeypatch.setenv("MEDCHECK_PLAIN_UI", "1")
    assert plain_ui() is True
    at = AppTest.from_file(APP, default_timeout=30).run()
    assert not at.exception
    assert _components(at) == [] and at.get("html") == []
    assert len(at.tabs) == 2 and len(at.file_uploader) == 1 and any(t.value == "MedCheck" for t in at.title)  # tool intact
    monkeypatch.setenv("MEDCHECK_PLAIN_UI", "0")
    assert plain_ui() is False


def test_default_ui_has_stage_story_and_the_whole_tool():
    at = AppTest.from_file(APP, default_timeout=30).run()
    assert not at.exception
    assert len(_components(at)) == 1 and len(at.get("html")) == 3  # style, hero, steps (recursive: the style block sits in its own container)
    assert len(at.tabs) == 2 and len(at.file_uploader) == 1 and len(at.camera_input) == 1 and not at.success


def test_app_still_works_when_the_presentation_layer_cannot_load(monkeypatch):
    monkeypatch.setitem(sys.modules, "medcheck_ui", None)  # import raises ImportError
    at = AppTest.from_file(APP, default_timeout=30).run()
    assert not at.exception, [e.value for e in at.exception]
    assert len(at.tabs) == 2 and len(at.file_uploader) == 1 and _components(at) == []


# ---------------- wording ----------------
def test_story_text_follows_the_wording_rules():
    chips = [a + " " + b for a, b in theme.chips(220, "AUG-2026")]
    text = " ".join([theme.HERO_LEAD, theme.HERO_NOTE, *theme.TAGLINE, *chips, *(t + " " + d for _n, t, d in theme.STEPS)])
    scrubbed = text
    for ok in ALLOWED_NEGATIONS:
        scrubbed = scrubbed.replace(ok, "").replace(ok.capitalize(), "")
    assert not BANNED.search(scrubbed), BANNED.search(scrubbed)
    assert "August 2026" in text and "Unable to verify" in text and "not an authenticity or safety test" in text.lower()
    assert "%" not in text and not re.search(r"\baccura", text, re.I)  # no performance claims on the front page


# ---------------- contrast (WCAG 2.x) ----------------
def _lum(rgb):
    def ch(v):
        v /= 255
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    r, g, b = (ch(x) for x in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _ratio(a, b):
    la, lb = sorted((_lum(a), _lum(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def _hex(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def test_text_contrast_meets_wcag_aa_even_over_the_brightest_canvas():
    r, g, b, a = theme.CARD_RGBA
    worst = tuple(a * c + (1 - a) * 255 for c in (r, g, b))  # glass card over a pure-white highlight (worst case)
    step_worst = tuple(theme.STEP_ALPHA * c + (1 - theme.STEP_ALPHA) * 255 for c in theme.NAVY)  # step text backing, same worst case
    assert _ratio(_hex(theme.TEXT), step_worst) >= 4.5 and _ratio((255, 255, 255), step_worst) >= 4.5
    assert _ratio(_hex(theme.TEXT), worst) >= 4.5
    assert _ratio(_hex(theme.MUTED), worst) >= 4.5
    assert _ratio((255, 255, 255), worst) >= 4.5  # card headings
    navy = theme.NAVY
    assert _ratio(_hex(theme.TEXT), navy) >= 7 and _ratio(_hex(theme.MUTED), navy) >= 4.5 and _ratio(_hex(theme.ACCENT), navy) >= 3
    cfg = (ROOT / ".streamlit" / "config.toml").read_text(encoding="utf-8")
    colors = dict(re.findall(r'(\w+Color) = "(#[0-9a-fA-F]{6})"', cfg))
    assert _ratio(_hex(colors["textColor"]), _hex(colors["backgroundColor"])) >= 7
    assert _ratio(_hex(colors["textColor"]), _hex(colors["secondaryBackgroundColor"])) >= 7
    assert colors["textColor"].lower() == theme.TEXT and colors["primaryColor"].lower() == theme.ACCENT


def test_font_stack_starts_with_segoe_ui_variable_and_loads_nothing_remote():
    assert '"Segoe UI Variable Text", "Segoe UI Variable", "Segoe UI"' in theme._CSS and "@font-face" not in theme._CSS
