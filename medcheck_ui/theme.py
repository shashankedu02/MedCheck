"""Theme and story for the cinematic interface. Static, trusted text only (nothing user-supplied is ever rendered here).

Wording rules are the project's: never "safe", "genuine" or "authentic" except in explicit negation; always say the check
covers one list; Unable to verify is presented as a normal, deliberate result. No performance figure appears here, and the
water scene is labelled as an illustration (MedCheck never tests or dissolves a medicine).
"""
from __future__ import annotations

from urllib.parse import quote

import streamlit as st

# Palette (checked by tests/test_ui_scene.py against WCAG 2.x AA).
TEXT = "#eaf4ff"
MUTED = "#b4c7dd"
ACCENT = "#22d3ee"
NAVY = (6, 20, 43)
CARD_RGBA = (8, 24, 50, 0.86)   # glass panel of the tool; the worst case behind it is a bright highlight (white)
STEP_ALPHA = 0.85               # backing of the scene captions (navy over whatever the canvas shows)

TAGLINE = ("Read the batch.", "Check the list.", "Say so when unsure.")
HERO_LEAD = "Scan a medicine strip and check its batch number against the CDSCO August 2026 NSQ list. When the evidence is unclear, MedCheck says Unable to verify."
HERO_NOTE = "A lookup aid on this computer. Not an authenticity or safety test, and not medical advice."
CHIP_OFFLINE = ("Offline", "everything runs on this computer")
CHIP_ABSTAIN = ("Abstains", "when the evidence is unclear")

# The five connected scenes (ids match SCENES in assets/scene.js). Scene 1's text is the hero (see story_html).
SCENES = (
    ("medicine", "01", "The medicine", "Every pack carries a batch number.",
     "A strip or box leaves the factory with a printed batch. That number is what MedCheck reads."),
    ("transformation", "02", "The transformation", "A medicine leaves a trail.",
     "This scene is an illustration only. MedCheck does not test, dissolve or analyse a medicine: it reads what is printed on the pack."),
    ("evidence", "03", "Evidence emerges", "The trail becomes text.",
     "Two offline text-recognition engines read the photo independently. A batch counts only when both passes agree; otherwise MedCheck reports it as uncertain."),
    ("inspection", "04", "The inspection", "Look at the printed batch.",
     "Photograph the line marked B.No., Batch or Lot so it fills the frame. The photo stays in memory on this computer and is never saved."),
    ("comparison", "05", "The comparison", "Compare it with one list.",
     "The batch is compared with the CDSCO NSQ list ({period}). Before a \"No alert found\" is ever shown you check the printed number on the pack, and anything unclear is Unable to verify."),
)
HEIGHTS_VH = (135, 235, 195, 225, 175)     # scroll length of each scene (vh)

_CSS = f"""
html, body, [data-testid="stApp"], button, input, textarea, select {{
  font-family: "Segoe UI Variable Text", "Segoe UI Variable", "Segoe UI", system-ui, -apple-system, sans-serif;
}}
html, body {{ background: rgb({NAVY[0]},{NAVY[1]},{NAVY[2]}); }}
/* the WebGL canvas sits behind the app; Streamlit's own layers are made transparent so it shows through */
#mc-stage {{ position: fixed; inset: 0; width: 100vw; height: 100vh; z-index: -1; pointer-events: none; }}
[data-testid="stApp"], [data-testid="stAppViewContainer"], [data-testid="stMain"], [data-testid="stHeader"] {{ background: transparent !important; }}
[data-testid="stMainBlockContainer"] {{ max-width: 1240px; padding: 1.5rem 3rem 5rem; transition: opacity .45s ease; }}
h1, h2, h3, p, label, li, [data-testid="stCaptionContainer"] {{ color: {TEXT}; }}
[data-testid="stCaptionContainer"] {{ color: {MUTED}; }}

/* the sidebar stays out of the way: collapsed by default, glass when opened */
[data-testid="stSidebar"] {{ background: rgba(8,24,50,.86) !important; backdrop-filter: blur(16px); border-right: 1px solid rgba(120,220,255,.14); }}
[data-testid="stSidebar"] [data-testid="stSidebarHeader"] {{ padding-bottom: 0; }}
[data-testid="stExpandSidebarButton"], [data-testid="stSidebarCollapseButton"] {{ opacity: .75; }}

/* ---------------- navigation: skip to the tool, scene dots ---------------- */
.mc-skip {{ position: fixed; top: 1rem; left: 4.2rem; z-index: 70; opacity: var(--mc-skip, 1); padding: .5rem 1.05rem; border-radius: 999px; border: 1px solid rgba(34,211,238,.6);
  background: rgba(6,20,43,.78); backdrop-filter: blur(10px); color: #fff !important; font-size: .85rem; letter-spacing: .03em; text-decoration: none !important; }}
.mc-skip:hover, .mc-skip:focus-visible {{ background: rgba(34,211,238,.28); outline: 2px solid {ACCENT}; outline-offset: 2px; }}
.mc-dots {{ position: fixed; right: 1.3rem; top: 50%; transform: translateY(-50%); z-index: 70; display: flex; flex-direction: column; gap: .9rem; }}
.mc-dots a {{ width: 11px; height: 11px; border-radius: 50%; border: 1.5px solid rgba(180,220,255,.7); background: transparent; display: block; transition: all .3s ease; }}
.mc-dots a:hover, .mc-dots a:focus-visible {{ border-color: #fff; outline: 2px solid {ACCENT}; outline-offset: 3px; }}
.mc-dots a.mc-on {{ background: {ACCENT}; border-color: {ACCENT}; box-shadow: 0 0 12px {ACCENT}; transform: scale(1.25); }}
html:not([data-mc-stage="3d"]) .mc-dots {{ display: none; }}

/* ---------------- the five scenes: a tall scroll section each, with a sticky caption ---------------- */
.mc-scene {{ position: relative; }}
.mc-cap {{ position: sticky; top: 22vh; max-width: 33rem; padding: 1.2rem 2.6rem 1.4rem 1.5rem; opacity: var(--op, 1); isolation: isolate;
  border-left: 2px solid rgba(34,211,238,.75); }}
/* soft-edged backing (fades out on the right, top and bottom) keeps the text readable over any frame of the scene */
.mc-cap::before {{ content: ""; position: absolute; inset: -1rem 0 -1rem 0; z-index: -1; pointer-events: none;
  background: linear-gradient(90deg, rgba(6,20,43,{STEP_ALPHA}) 0%, rgba(6,20,43,{STEP_ALPHA}) 80%, rgba(6,20,43,0) 100%);
  -webkit-mask-image: linear-gradient(to bottom, transparent, #000 9%, #000 91%, transparent); mask-image: linear-gradient(to bottom, transparent, #000 9%, #000 91%, transparent); }}
.mc-eyebrow {{ font-size: .78rem; letter-spacing: .24em; text-transform: uppercase; color: {ACCENT}; margin: 0 0 .9rem; display: flex; align-items: center; gap: .8rem; }}
.mc-eyebrow b {{ font-weight: 600; color: #fff; letter-spacing: .1em; }}
.mc-cap h2 {{ font-family: "Segoe UI Variable Display", "Segoe UI Variable Text", "Segoe UI", sans-serif; font-size: clamp(1.9rem, 3.6vw, 3rem); font-weight: 350; letter-spacing: -.02em;
  line-height: 1.08; color: #fff; margin: 0 0 .8rem; padding: 0; }}
.mc-cap p {{ margin: 0 0 .7rem; line-height: 1.55; font-size: 1.04rem; color: {TEXT}; }}
.mc-cap .mc-note {{ font-size: .9rem; color: {MUTED}; }}
/* scene 1 is the hero; scenes 3 to 5 keep their caption at the top so the centred subject (text, package, panels) stays clear */
.mc-scene[data-scene="1"] .mc-cap {{ top: 12vh; max-width: 40rem; }}
.mc-scene[data-scene="3"] .mc-cap, .mc-scene[data-scene="4"] .mc-cap, .mc-scene[data-scene="5"] .mc-cap {{ top: 7vh; max-width: 30rem; }}
.mc-brand {{ font-family: "Segoe UI Variable Display", "Segoe UI Variable Text", "Segoe UI", sans-serif; font-size: 1.05rem; letter-spacing: .34em; text-transform: uppercase; color: #fff; margin: 0 0 .9rem; font-weight: 600; }}
.mc-tag {{ font-family: "Segoe UI Variable Display", "Segoe UI Variable Text", "Segoe UI", sans-serif; font-size: clamp(2.4rem, 5.2vw, 4.7rem); font-weight: 300; letter-spacing: -.025em; line-height: 1.02; color: #fff; margin: 0 0 1.3rem; text-shadow: 0 0 60px rgba(34,211,238,.28); }}
.mc-tag span {{ display: block; font-weight: 650; font-size: .74em; margin-top: .15em; letter-spacing: -.015em; }}
.mc-cta-row {{ display: flex; align-items: center; gap: 1.4rem; flex-wrap: wrap; margin-top: 1.2rem; }}
.mc-cta {{ display: inline-block; padding: .85rem 1.7rem; border-radius: 999px; border: 1px solid rgba(34,211,238,.75);
  background: linear-gradient(180deg, rgba(34,211,238,.28), rgba(34,211,238,.1)); color: #fff !important; font-weight: 600; letter-spacing: .02em; text-decoration: none !important;
  backdrop-filter: blur(10px); box-shadow: 0 0 32px rgba(34,211,238,.25); }}
.mc-cta:hover, .mc-cta:focus-visible {{ background: rgba(34,211,238,.38); outline: 2px solid {ACCENT}; outline-offset: 3px; }}
.mc-hint {{ font-size: .85rem; color: {MUTED}; letter-spacing: .04em; }}
.mc-chips {{ list-style: none !important; margin: 1.6rem 0 0 !important; padding: 0 !important; display: flex; gap: .7rem; flex-wrap: wrap; }}
.mc-chips li {{ padding: .6rem 1rem; border-radius: 14px; border: 1px solid rgba(120,220,255,.22); background: rgba(8,24,50,.72); color: {TEXT}; font-size: .82rem; line-height: 1.3; }}
.mc-chips li b {{ display: block; font-size: 1.15rem; font-weight: 650; color: #fff; letter-spacing: -.01em; }}
/* still artwork shown only while the 3D stage is not running (no WebGL, failure, or before it loads) */
.mc-art-fallback {{ position: fixed; right: 4vw; top: 22vh; width: min(46vw, 640px); opacity: .9; z-index: -1; pointer-events: none; }}
html[data-mc-stage="3d"] .mc-art-fallback {{ display: none; }}
html:not([data-mc-stage="3d"]) .mc-scene {{ min-height: 0 !important; padding: 1.2rem 0; }}
html:not([data-mc-stage="3d"]) .mc-cap {{ position: static; opacity: 1; }}
.mc-tool-eyebrow {{ font-size: .8rem; letter-spacing: .22em; text-transform: uppercase; color: {ACCENT}; margin: 0 0 .6rem; }}

/* ---------------- the tool: one glass panel, the destination of the story ---------------- */
.st-key-mc_tool {{ background: rgba({CARD_RGBA[0]},{CARD_RGBA[1]},{CARD_RGBA[2]},{CARD_RGBA[3]}); border: 1px solid rgba(120,220,255,.2);
  border-radius: 26px; box-shadow: 0 30px 80px rgba(0,0,0,.45), inset 0 1px 0 rgba(255,255,255,.06); backdrop-filter: blur(18px);
  padding: 2rem 2.2rem; scroll-margin-top: 1.5rem; }}
.st-key-mc_tool::before {{ content: "Your turn \\2014  check a photo"; display: block; font-size: .8rem; letter-spacing: .22em; text-transform: uppercase; color: {ACCENT}; margin-bottom: .4rem; }}
.st-key-mc_tool h1 {{ font-family: "Segoe UI Variable Display", "Segoe UI", sans-serif; font-weight: 600; letter-spacing: -.02em; }}

/* ---------------- scanning sequence (driven by the real OCR phase) ---------------- */
html[data-mc-stage="3d"][data-mc-phase="scanning"] [data-testid="stMainBlockContainer"] {{ opacity: 0; pointer-events: none; }}
html[data-mc-stage="3d"][data-mc-phase="scanning"] .mc-dots, html[data-mc-stage="3d"][data-mc-phase="scanning"] .mc-skip {{ opacity: .15; }}
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
#mc-brackets i {{ position: absolute; width: 24px; height: 24px; border: 2px solid rgb(var(--mc-tint)); filter: drop-shadow(0 0 8px rgb(var(--mc-tint))); }}
#mc-brackets i:nth-child(1) {{ left: -8px; top: -8px; border-right: 0; border-bottom: 0; }}
#mc-brackets i:nth-child(2) {{ right: -8px; top: -8px; border-left: 0; border-bottom: 0; }}
#mc-brackets i:nth-child(3) {{ right: -8px; bottom: -8px; border-left: 0; border-top: 0; }}
#mc-brackets i:nth-child(4) {{ left: -8px; bottom: -8px; border-right: 0; border-top: 0; }}
#mc-brackets:not(.mc-lock) {{ animation: mc-breathe 1.1s ease-in-out infinite; }}
@keyframes mc-breathe {{ 50% {{ transform: scale(1.025); }} }}

/* ---------------- portrait screens ---------------- */
@media (max-aspect-ratio: 11/10) {{
  [data-testid="stMainBlockContainer"] {{ padding: 1rem 1.2rem 4rem; }}
  .mc-cap {{ position: sticky; top: auto; bottom: 6vh; max-width: 100%; padding-right: 1.2rem; }}
  .mc-scene[data-scene="1"] .mc-cap {{ top: auto; bottom: 6vh; }}
  .mc-dots {{ right: .6rem; gap: .7rem; }}
  .mc-skip {{ left: 3.4rem; font-size: .78rem; }}
  .mc-art-fallback {{ right: 5vw; left: 5vw; top: 8vh; width: auto; }}
  .st-key-mc_tool {{ padding: 1.2rem 1rem; }}
}}
@media (prefers-reduced-motion: reduce) {{
  #mc-brackets, #mc-hud em::after {{ animation: none !important; }}
  html {{ scroll-behavior: auto; }}
}}
html {{ scroll-behavior: smooth; }}
"""

_FALLBACK_SVG = """<svg viewBox="0 0 400 220" xmlns="http://www.w3.org/2000/svg">
<defs><linearGradient id="mcf" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#9fd8ff"/><stop offset="1" stop-color="#1b4fd8"/></linearGradient></defs>
<g transform="rotate(-28 200 110)"><rect x="70" y="70" width="260" height="80" rx="40" fill="url(#mcf)" opacity=".9"/>
<rect x="196" y="70" width="6" height="80" fill="#0a2b9e" opacity=".5"/><rect x="92" y="84" width="170" height="16" rx="8" fill="#fff" opacity=".45"/></g></svg>"""

# st.html sanitises inline <svg> away, so the still artwork is a CSS background (data URI: no network, not sanitised).
_FALLBACK_URI = "data:image/svg+xml;charset=utf-8," + quote(_FALLBACK_SVG)


def chips(records: int | None, period: str | None) -> tuple[tuple[str, str], ...]:
    """Fact chips; every figure comes from the loaded dataset (nothing hard-coded, no performance claim)."""
    first = (f"{records}", f"records, {period} list") if records and period else ("One list", "CDSCO NSQ, August 2026")
    return (first, CHIP_OFFLINE, CHIP_ABSTAIN)


def scene_texts(period: str | None) -> tuple[tuple[str, str, str, str, str], ...]:
    p = period or "August 2026"
    return tuple((i, n, e, t, b.format(period=p)) for i, n, e, t, b in SCENES)


def story_html(records: int | None = None, period: str | None = None) -> str:
    tag = "".join(f"<span>{t}</span>" if i == len(TAGLINE) - 1 else f"{t}<br>" for i, t in enumerate(TAGLINE))
    items = "".join(f"<li><b>{a}</b>{b}</li>" for a, b in chips(records, period))
    parts = ['<a class="mc-skip" href="#mc-tool">Skip to the check</a>', '<div class="mc-art-fallback" aria-hidden="true"></div>']
    texts = scene_texts(period)
    parts.append('<nav class="mc-dots" aria-label="Story scenes">' + "".join(
        f'<a href="#mc-scene-{k}" aria-label="Scene {n}: {e}"></a>' for k, (_i, n, e, _t, _b) in enumerate(texts, 1)) + "</nav>")
    for k, (sid, n, eyebrow, title, body) in enumerate(texts, 1):
        if k == 1:
            inner = (f'<div class="mc-eyebrow"><b>{n}</b> {eyebrow} · CDSCO NSQ list · {period or "August 2026"}</div>'
                     f'<div class="mc-brand">MedCheck</div><h1 class="mc-tag">{tag}</h1>'
                     f'<p>{HERO_LEAD}</p><p class="mc-note">{HERO_NOTE}</p>'
                     '<div class="mc-cta-row"><a class="mc-cta" href="#mc-tool">Start a check</a><span class="mc-hint">or scroll to watch how it works</span></div>'
                     f'<ul class="mc-chips">{items}</ul>')
        else:
            cta = '<div class="mc-cta-row"><a class="mc-cta" href="#mc-tool">Start a check</a></div>' if k == 5 else ""
            inner = f'<div class="mc-eyebrow"><b>{n}</b> {eyebrow}</div><h2>{title}</h2><p>{body}</p>{cta}'
        parts.append(f'<section class="mc-scene" id="mc-scene-{k}" data-scene="{k}" data-id="{sid}" style="min-height:{HEIGHTS_VH[k - 1]}vh"><div class="mc-cap">{inner}</div></section>')
    parts.append('<div id="mc-tool"></div>')
    return "".join(parts)


def css() -> str:
    return _CSS + f'.mc-art-fallback {{ aspect-ratio: 400 / 220; background: url("{_FALLBACK_URI}") center / contain no-repeat; }}\n'


def render_theme_and_story(records: int | None = None, period: str | None = None) -> None:
    st.html(f"<style>{css()}</style>")
    st.html(story_html(records, period))
