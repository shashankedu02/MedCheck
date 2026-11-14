"""Theme, hero and story for the 3D interface. Static, trusted text only (nothing user-supplied is ever rendered here).

Wording rules are the project's: never "safe", "genuine" or "authentic" except in explicit negation; always say the check
covers one list; Unable to verify is presented as a normal, deliberate result.
"""
from __future__ import annotations

from urllib.parse import quote

import streamlit as st

# Palette (checked by tests/test_ui_scene.py against WCAG 2.x AA).
TEXT = "#eaf4ff"
MUTED = "#b4c7dd"
ACCENT = "#22d3ee"
NAVY = (6, 20, 43)
CARD_RGBA = (8, 24, 50, 0.86)  # glass card; the worst case behind it is a bright foil highlight (white)

HERO_TITLE = "MedCheck"
HERO_LEAD = "Scan a medicine strip and check its batch number against the CDSCO August 2026 NSQ list. When the evidence is unclear, MedCheck says Unable to verify."
HERO_NOTE = "A lookup aid on this computer. Not an authenticity or safety test, and not medical advice."
STEPS = (
    ("1", "Photograph the batch line", "Take or upload a photo of the strip or box. It stays in memory on this computer and is never saved."),
    ("2", "Read it locally", "Two text-recognition engines read the photo offline. A batch counts only when the passes agree; anything else is reported as uncertain."),
    ("3", "Compare, then confirm", "The batch is compared with one monthly list. You check the printed number on the pack before a \"No alert found\" is ever shown."),
)

_CSS = f"""
html, body, [data-testid="stApp"], button, input, textarea, select {{
  font-family: "Segoe UI Variable Text", "Segoe UI Variable", "Segoe UI", system-ui, -apple-system, sans-serif;
}}
html, body {{ background: rgb({NAVY[0]},{NAVY[1]},{NAVY[2]}); }}
/* the WebGL canvas sits behind the app; Streamlit's own layers are made transparent so it shows through */
#mc-stage {{ position: fixed; inset: 0; width: 100vw; height: 100vh; z-index: -1; pointer-events: none; }}
[data-testid="stApp"], [data-testid="stAppViewContainer"], [data-testid="stMain"], [data-testid="stHeader"] {{ background: transparent !important; }}
[data-testid="stMainBlockContainer"] {{ max-width: 1120px; padding-top: 2.5rem; }}
h1, h2, h3, p, label, li, [data-testid="stCaptionContainer"] {{ color: {TEXT}; }}
[data-testid="stCaptionContainer"] {{ color: {MUTED}; }}

.mc-hero {{ min-height: 86vh; display: flex; flex-direction: column; justify-content: center; max-width: 44%; position: relative; }}
.mc-hero h1 {{ font-size: clamp(2.6rem, 6vw, 4.6rem); font-weight: 650; letter-spacing: -0.02em; margin: 0 0 .6rem; line-height: 1.02; color: #fff; text-shadow: 0 0 40px rgba(34,211,238,.35); }}
.mc-hero .mc-lead {{ font-size: clamp(1.05rem, 1.7vw, 1.35rem); line-height: 1.5; color: {TEXT}; margin: 0 0 .8rem; }}
.mc-hero .mc-note {{ font-size: .95rem; color: {MUTED}; margin: 0 0 1.6rem; }}
.mc-cta {{ display: inline-block; align-self: flex-start; padding: .8rem 1.5rem; border-radius: 999px; border: 1px solid rgba(34,211,238,.7);
  background: rgba(34,211,238,.14); color: #fff !important; font-weight: 600; text-decoration: none !important; backdrop-filter: blur(10px); }}
.mc-cta:hover, .mc-cta:focus-visible {{ background: rgba(34,211,238,.3); outline: 2px solid {ACCENT}; outline-offset: 3px; }}
/* SVG hero shown only while the 3D stage is not running (no WebGL, failure, or before it loads) */
.mc-art-fallback {{ position: fixed; right: 4vw; top: 22vh; width: min(46vw, 640px); opacity: .9; z-index: -1; pointer-events: none; }}
html[data-mc-stage="3d"] .mc-art-fallback {{ display: none; }}
@media (max-aspect-ratio: 11/10) {{
  .mc-hero {{ max-width: 100%; padding-top: 38vh; justify-content: flex-start; min-height: 92vh; }}
  .mc-art-fallback {{ right: 5vw; left: 5vw; top: 8vh; width: auto; }}
}}

.mc-steps {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 1rem; margin: 1rem 0 3rem; }}
.mc-card, .st-key-mc_tool {{ background: rgba({CARD_RGBA[0]},{CARD_RGBA[1]},{CARD_RGBA[2]},{CARD_RGBA[3]}); border: 1px solid rgba(120,220,255,.2);
  border-radius: 20px; box-shadow: 0 18px 50px rgba(0,0,0,.35); backdrop-filter: blur(16px); }}
.mc-card {{ padding: 1.4rem 1.5rem; }}
.mc-card .mc-n {{ display: inline-flex; width: 2rem; height: 2rem; align-items: center; justify-content: center; border-radius: 50%;
  background: rgba(34,211,238,.18); border: 1px solid rgba(34,211,238,.6); color: #fff; font-weight: 650; margin-bottom: .7rem; }}
.mc-card h3 {{ margin: 0 0 .4rem; font-size: 1.2rem; color: #fff; }}
.mc-card p {{ margin: 0; line-height: 1.5; color: {TEXT}; }}
.st-key-mc_tool {{ padding: 1.6rem 1.8rem; scroll-margin-top: 1.5rem; }}
@supports (animation-timeline: view()) {{
  .mc-card {{ animation: mc-rise linear both; animation-timeline: view(); animation-range: entry 0% entry 55%; }}
  @keyframes mc-rise {{ from {{ opacity: 0; transform: translateY(40px); }} to {{ opacity: 1; transform: none; }} }}
}}
@media (prefers-reduced-motion: reduce) {{ .mc-card {{ animation: none !important; }} html {{ scroll-behavior: auto; }} }}
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


def hero_html() -> str:
    return (
        f'<div class="mc-art-fallback" aria-hidden="true"></div><section class="mc-hero"><h1>{HERO_TITLE}</h1><p class="mc-lead">{HERO_LEAD}</p>'
        f'<p class="mc-note">{HERO_NOTE}</p><a class="mc-cta" href="#mc-tool">Start a check</a></section>'
    )


def steps_html() -> str:
    cards = "".join(f'<div class="mc-card"><span class="mc-n">{n}</span><h3>{t}</h3><p>{d}</p></div>' for n, t, d in STEPS)
    return f'<div class="mc-steps">{cards}</div><div id="mc-tool"></div>'


def css() -> str:
    return _CSS + f'.mc-art-fallback {{ aspect-ratio: 740 / 290; background: url("{_FALLBACK_URI}") center / contain no-repeat; }}\n'


def render_theme_and_story() -> None:
    st.html(f"<style>{css()}</style>")
    st.html(hero_html())
    st.html(steps_html())
