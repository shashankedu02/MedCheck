"""Theme, hero and story for the 3D interface. Static, trusted text only (nothing user-supplied is ever rendered here).

Wording rules are the project's: never "safe", "genuine" or "authentic" except in explicit negation; always say the check
covers one list; Unable to verify is presented as a normal, deliberate result. No performance figure appears here.
"""
from __future__ import annotations

from urllib.parse import quote

import streamlit as st

# Palette (checked by tests/test_ui_scene.py against WCAG 2.x AA).
TEXT = "#eaf4ff"
MUTED = "#b4c7dd"
ACCENT = "#22d3ee"
NAVY = (6, 20, 43)
CARD_RGBA = (8, 24, 50, 0.86)   # glass panel of the tool; the worst case behind it is a bright foil highlight (white)
STEP_ALPHA = 0.85               # backing of the step text blocks (navy over whatever the canvas shows)

TAGLINE = ("Read the batch.", "Check the list.", "Say so when unsure.")
HERO_LEAD = "Scan a medicine strip and check its batch number against the CDSCO August 2026 NSQ list. When the evidence is unclear, MedCheck says Unable to verify."
HERO_NOTE = "A lookup aid on this computer. Not an authenticity or safety test, and not medical advice."
STEPS = (
    ("01", "Frame the batch line", "Photograph the strip or box so the line marked B.No. fills the frame. The photo stays in memory on this computer and is never saved."),
    ("02", "Two readers, one answer", "Two offline text-recognition engines read the photo. The batch counts only when the passes agree; otherwise MedCheck reports it as uncertain."),
    ("03", "Compare, confirm, abstain", "The batch is compared with one monthly list. You check the printed number on the pack before a \"No alert found\" is ever shown, and anything unclear is Unable to verify."),
)
CHIP_OFFLINE = ("Offline", "everything runs on this computer")
CHIP_ABSTAIN = ("Abstains", "when the evidence is unclear")

_CSS = f"""
html, body, [data-testid="stApp"], button, input, textarea, select {{
  font-family: "Segoe UI Variable Text", "Segoe UI Variable", "Segoe UI", system-ui, -apple-system, sans-serif;
}}
html, body {{ background: rgb({NAVY[0]},{NAVY[1]},{NAVY[2]}); }}
/* the WebGL canvas sits behind the app; Streamlit's own layers are made transparent so it shows through */
#mc-stage {{ position: fixed; inset: 0; width: 100vw; height: 100vh; z-index: -1; pointer-events: none; }}
[data-testid="stApp"], [data-testid="stAppViewContainer"], [data-testid="stMain"], [data-testid="stHeader"] {{ background: transparent !important; }}
[data-testid="stMainBlockContainer"] {{ max-width: 1240px; padding: 1.5rem 3rem 5rem; }}
h1, h2, h3, p, label, li, [data-testid="stCaptionContainer"] {{ color: {TEXT}; }}
[data-testid="stCaptionContainer"] {{ color: {MUTED}; }}

/* the sidebar stays out of the way: collapsed by default, glass when opened */
[data-testid="stSidebar"] {{ background: rgba(8,24,50,.86) !important; backdrop-filter: blur(16px); border-right: 1px solid rgba(120,220,255,.14); }}
[data-testid="stSidebar"] [data-testid="stSidebarHeader"] {{ padding-bottom: 0; }}
[data-testid="stExpandSidebarButton"], [data-testid="stSidebarCollapseButton"] {{ opacity: .75; }}

/* ---------------- hero ---------------- */
.mc-hero {{ min-height: 94vh; display: flex; flex-direction: column; justify-content: center; max-width: 46%; padding: 2rem 0 3rem; position: relative; }}
.mc-eyebrow {{ font-size: .8rem; letter-spacing: .22em; text-transform: uppercase; color: {ACCENT}; margin-bottom: 1.3rem; display: flex; align-items: center; gap: .8rem; }}
.mc-eyebrow::before {{ content: ""; width: 2.6rem; height: 1px; background: {ACCENT}; display: inline-block; }}
.mc-brand {{ font-family: "Segoe UI Variable Display", "Segoe UI Variable Text", "Segoe UI", sans-serif; font-size: 1.05rem; letter-spacing: .34em; text-transform: uppercase; color: #fff; margin: 0 0 .9rem; font-weight: 600; }}
.mc-tag {{ font-family: "Segoe UI Variable Display", "Segoe UI Variable Text", "Segoe UI", sans-serif; font-size: clamp(2.5rem, 5.6vw, 5rem); font-weight: 300; letter-spacing: -.025em; line-height: 1.02; color: #fff; margin: 0 0 1.4rem; text-shadow: 0 0 60px rgba(34,211,238,.28); }}
.mc-tag span {{ display: block; font-weight: 650; font-size: .74em; margin-top: .15em; letter-spacing: -.015em; }}
.mc-hero .mc-lead {{ font-size: clamp(1.02rem, 1.45vw, 1.22rem); line-height: 1.55; color: {TEXT}; margin: 0 0 .7rem; max-width: 34rem; }}
.mc-hero .mc-note {{ font-size: .92rem; color: {MUTED}; margin: 0 0 1.8rem; }}
.mc-cta-row {{ display: flex; align-items: center; gap: 1.4rem; flex-wrap: wrap; }}
.mc-cta {{ display: inline-block; padding: .9rem 1.8rem; border-radius: 999px; border: 1px solid rgba(34,211,238,.75);
  background: linear-gradient(180deg, rgba(34,211,238,.28), rgba(34,211,238,.1)); color: #fff !important; font-weight: 600; letter-spacing: .02em; text-decoration: none !important;
  backdrop-filter: blur(10px); box-shadow: 0 0 32px rgba(34,211,238,.25); }}
.mc-cta:hover, .mc-cta:focus-visible {{ background: rgba(34,211,238,.38); outline: 2px solid {ACCENT}; outline-offset: 3px; }}
.mc-hint {{ font-size: .85rem; color: {MUTED}; letter-spacing: .04em; }}
.mc-chips {{ list-style: none !important; margin: 2.4rem 0 0 !important; padding: 0 !important; display: flex; gap: .8rem; flex-wrap: wrap; width: max-content; max-width: 150%; }}
.mc-chips li {{ padding: .7rem 1.1rem; border-radius: 14px; border: 1px solid rgba(120,220,255,.22); background: rgba(8,24,50,.72); backdrop-filter: blur(12px); color: {TEXT}; font-size: .86rem; line-height: 1.3; }}
.mc-chips li b {{ display: block; font-size: 1.25rem; font-weight: 650; color: #fff; letter-spacing: -.01em; }}
/* still artwork shown only while the 3D stage is not running (no WebGL, failure, or before it loads) */
.mc-art-fallback {{ position: fixed; right: 4vw; top: 22vh; width: min(46vw, 640px); opacity: .9; z-index: -1; pointer-events: none; }}
html[data-mc-stage="3d"] .mc-art-fallback {{ display: none; }}

/* ---------------- story: editorial steps, no cards ---------------- */
.mc-steps {{ margin: 0 0 1rem; }}
.mc-step {{ min-height: 78vh; display: flex; align-items: center; max-width: 47%; gap: 1.4rem; }}
.mc-num {{ font-family: "Segoe UI Variable Display", "Segoe UI", sans-serif; font-size: clamp(4.2rem, 9vw, 8rem); font-weight: 200; line-height: 1; color: transparent;
  -webkit-text-stroke: 1px rgba(34,211,238,.6); letter-spacing: -.04em; user-select: none; }}
.mc-copy {{ padding: 1.3rem 2.4rem 1.3rem 1.5rem; border-left: 2px solid rgba(34,211,238,.75);
  background: linear-gradient(90deg, rgba(6,20,43,{STEP_ALPHA}) 0%, rgba(6,20,43,{STEP_ALPHA}) 82%, rgba(6,20,43,0) 100%); }}
.mc-copy h3 {{ margin: 0 0 .5rem; line-height: 1.2; padding: 0; font-family: "Segoe UI Variable Display", "Segoe UI", sans-serif; font-size: clamp(1.4rem, 2.3vw, 1.9rem); font-weight: 500; letter-spacing: -.01em; color: #fff; }}
.mc-copy p {{ margin: 0; line-height: 1.55; font-size: 1.04rem; color: {TEXT}; }}
.mc-tool-eyebrow {{ font-size: .8rem; letter-spacing: .22em; text-transform: uppercase; color: {ACCENT}; margin: 0 0 .6rem; }}

/* ---------------- the tool: one glass panel ---------------- */
.st-key-mc_tool {{ background: rgba({CARD_RGBA[0]},{CARD_RGBA[1]},{CARD_RGBA[2]},{CARD_RGBA[3]}); border: 1px solid rgba(120,220,255,.2);
  border-radius: 26px; box-shadow: 0 30px 80px rgba(0,0,0,.45), inset 0 1px 0 rgba(255,255,255,.06); backdrop-filter: blur(18px);
  padding: 2rem 2.2rem; scroll-margin-top: 1.5rem; transition: opacity .45s ease; }}
.st-key-mc_tool::before {{ content: "Your turn \\2014  check a photo"; display: block; font-size: .8rem; letter-spacing: .22em; text-transform: uppercase; color: {ACCENT}; margin-bottom: .4rem; }}
.st-key-mc_tool h1 {{ font-family: "Segoe UI Variable Display", "Segoe UI", sans-serif; font-weight: 600; letter-spacing: -.02em; }}

/* ---------------- scanning sequence (driven by the real OCR phase) ---------------- */
[data-testid="stMainBlockContainer"] {{ transition: opacity .45s ease; }}
html[data-mc-stage="3d"][data-mc-phase="scanning"] [data-testid="stMainBlockContainer"] {{ opacity: .08; pointer-events: none; }}
#mc-hud {{ position: fixed; left: 50%; bottom: 8vh; transform: translateX(-50%) translateY(12px); z-index: 60; width: min(92vw, 30rem); text-align: center; pointer-events: none;
  opacity: 0; transition: opacity .4s ease, transform .4s ease; padding: 1.1rem 1.4rem 1.3rem; border-radius: 18px; border: 1px solid rgba(34,211,238,.4);
  background: rgba(6,20,43,.86); backdrop-filter: blur(14px); box-shadow: 0 0 60px rgba(34,211,238,.18); }}
#mc-hud b {{ display: block; color: #fff; font-size: 1.15rem; font-weight: 600; letter-spacing: .01em; }}
#mc-hud span {{ display: block; color: {MUTED}; font-size: .9rem; margin: .3rem 0 .9rem; }}
#mc-hud em {{ display: block; height: 3px; border-radius: 3px; background: rgba(34,211,238,.18); position: relative; overflow: hidden; }}
#mc-hud em::after {{ content: ""; position: absolute; inset: 0 auto 0 -40%; width: 40%; background: linear-gradient(90deg, transparent, {ACCENT}, transparent); animation: mc-indet 1.3s ease-in-out infinite; }}
@keyframes mc-indet {{ to {{ left: 100%; }} }}
html[data-mc-phase="scanning"] #mc-hud {{ opacity: 1; transform: translateX(-50%); }}
#mc-brackets {{ position: fixed; z-index: 55; pointer-events: none; opacity: 0; transition: opacity .35s ease; --mc-tint: 34,211,238; }}
#mc-brackets i {{ position: absolute; width: 26px; height: 26px; border: 2px solid rgb(var(--mc-tint)); filter: drop-shadow(0 0 8px rgb(var(--mc-tint))); }}
#mc-brackets i:nth-child(1) {{ left: -8px; top: -8px; border-right: 0; border-bottom: 0; }}
#mc-brackets i:nth-child(2) {{ right: -8px; top: -8px; border-left: 0; border-bottom: 0; }}
#mc-brackets i:nth-child(3) {{ right: -8px; bottom: -8px; border-left: 0; border-top: 0; }}
#mc-brackets i:nth-child(4) {{ left: -8px; bottom: -8px; border-right: 0; border-top: 0; }}
#mc-brackets:not(.mc-lock) {{ animation: mc-breathe 1.1s ease-in-out infinite; }}
@keyframes mc-breathe {{ 50% {{ transform: scale(1.025); }} }}

/* ---------------- portrait screens ---------------- */
@media (max-aspect-ratio: 11/10) {{
  [data-testid="stMainBlockContainer"] {{ padding: 1rem 1.2rem 4rem; }}
  .mc-hero {{ max-width: 100%; padding-top: 40vh; justify-content: flex-start; min-height: 96vh; padding-bottom: 8rem; }}
  .mc-chips {{ width: auto; max-width: 100%; }}
  .mc-step {{ max-width: 100%; min-height: 62vh; flex-direction: column; align-items: flex-start; gap: .2rem; justify-content: center; }}
  .mc-num {{ font-size: 3.6rem; }}
  .mc-copy {{ padding-right: 1.2rem; }}
  .mc-art-fallback {{ right: 5vw; left: 5vw; top: 8vh; width: auto; }}
  .st-key-mc_tool {{ padding: 1.2rem 1rem; }}
}}
@supports (animation-timeline: view()) {{
  .mc-copy, .mc-num {{ animation: mc-rise linear both; animation-timeline: view(); animation-range: entry 0% entry 45%; }}
  @keyframes mc-rise {{ from {{ opacity: 0; transform: translateY(34px); }} to {{ opacity: 1; transform: none; }} }}
}}
@media (prefers-reduced-motion: reduce) {{
  .mc-copy, .mc-num, #mc-brackets, #mc-hud em::after {{ animation: none !important; }}
  html {{ scroll-behavior: auto; }}
}}
html {{ scroll-behavior: smooth; }}
"""

_FALLBACK_SVG = """<svg viewBox="0 0 740 290" xmlns="http://www.w3.org/2000/svg">
<defs><linearGradient id="mcf" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#e3eaf3"/><stop offset="1" stop-color="#8fa1b6"/></linearGradient></defs>
<rect x="6" y="6" width="728" height="278" rx="28" fill="url(#mcf)" opacity=".92"/>
<g fill="#cdeeff" fill-opacity=".35" stroke="#8fe9ff" stroke-width="2">
<rect x="40" y="36" width="150" height="80" rx="40"/><rect x="215" y="36" width="150" height="80" rx="40"/><rect x="390" y="36" width="150" height="80" rx="40"/><rect x="565" y="36" width="150" height="80" rx="40"/>
<rect x="40" y="148" width="150" height="80" rx="40"/><rect x="215" y="148" width="150" height="80" rx="40"/><rect x="390" y="148" width="150" height="80" rx="40"/><rect x="565" y="148" width="150" height="80" rx="40"/></g>
<text x="40" y="262" font-family="Segoe UI, sans-serif" font-size="26" fill="#26323f">B.No. •••••••   Exp •• / ••••</text></svg>"""

# st.html sanitises inline <svg> away, so the still artwork is a CSS background (data URI: no network, not sanitised).
_FALLBACK_URI = "data:image/svg+xml;charset=utf-8," + quote(_FALLBACK_SVG)


def chips(records: int | None, period: str | None) -> tuple[tuple[str, str], ...]:
    """Fact chips; every figure comes from the loaded dataset (nothing hard-coded, no performance claim)."""
    first = (f"{records}", f"records, {period} list") if records and period else ("One list", "CDSCO NSQ, August 2026")
    return (first, CHIP_OFFLINE, CHIP_ABSTAIN)


def hero_html(records: int | None = None, period: str | None = None) -> str:
    tag = "".join(f"<span>{t}</span>" if i == len(TAGLINE) - 1 else f"{t}<br>" for i, t in enumerate(TAGLINE))
    items = "".join(f"<li><b>{a}</b>{b}</li>" for a, b in chips(records, period))
    return (
        '<div class="mc-art-fallback" aria-hidden="true"></div>'
        f'<section class="mc-hero"><div class="mc-eyebrow">CDSCO NSQ list · {period or "August 2026"}</div>'
        f'<div class="mc-brand">MedCheck</div><h1 class="mc-tag">{tag}</h1>'
        f'<p class="mc-lead">{HERO_LEAD}</p><p class="mc-note">{HERO_NOTE}</p>'
        '<div class="mc-cta-row"><a class="mc-cta" href="#mc-tool">Start a check</a><span class="mc-hint">or scroll to see how it works</span></div>'
        f'<ul class="mc-chips">{items}</ul></section>'
    )


def steps_html() -> str:
    steps = "".join(
        f'<article class="mc-step"><div class="mc-num" aria-hidden="true">{n}</div><div class="mc-copy"><h3>{t}</h3><p>{d}</p></div></article>'
        for n, t, d in STEPS)
    return f'<div class="mc-steps">{steps}</div><div id="mc-tool"></div>'


def css() -> str:
    return _CSS + f'.mc-art-fallback {{ aspect-ratio: 740 / 290; background: url("{_FALLBACK_URI}") center / contain no-repeat; }}\n'


def render_theme_and_story(records: int | None = None, period: str | None = None) -> None:
    st.html(f"<style>{css()}</style>")
    st.html(hero_html(records, period))
    st.html(steps_html())
