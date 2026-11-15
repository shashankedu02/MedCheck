"""Presentation of a check result: status banner, reading cards, record comparison, notes. Pure functions that turn an
already-computed ScanResult into HTML. Nothing here decides, scores or reclassifies anything: the status, the wording and
every caveat come from the decision engine unchanged, and every dynamic value is HTML-escaped before it is placed in markup.

Rules kept from the project: a clean negative is deliberately neutral (never green, no tick, no shield); colour is never the
only signal (each state also has a word and a glyph); no confidence figure or percentage is shown; the safety wording is
shown in full, in the page, not behind a click. The photo's recognised text is NOT rendered here: it stays in the app's plain
text expander (see app.py).
"""
from __future__ import annotations

from html import escape

from medcheck.decision import LIMITATION_TEXT
from medcheck.models import BatchSource, FieldState, Status

# Accent per outcome, as (text/accent colour, glyph). Alert = red, unable = amber, no alert = neutral sky blue (never green),
# expired = orange, system error = violet. Checked for contrast against the card colours in tests/test_ui_result.py.
ACCENTS = {
    "alert": ("#ff8f8f", "!"),
    "unable": ("#fbbf24", "?"),
    "no_alert": ("#7dd3fc", "i"),
    "expired": ("#fdba74", "!"),
    "system": ("#d8b4fe", "!"),
    "rejected": ("#fbbf24", "!"),
}
CARD_BG = (6, 20, 43)          # solid colour the translucent cards are tested against (the page navy)

FIELD_WORDS = {
    FieldState.READ: "agreed by the OCR passes - not yet checked against the pack",
    FieldState.AMBIGUOUS: "uncertain",
    FieldState.NOT_FOUND: "not found",
}
CHIP_WORDS = {FieldState.READ: "Read", FieldState.AMBIGUOUS: "Uncertain", FieldState.NOT_FOUND: "Not found"}
SOURCE_WORDS = {
    BatchSource.OCR: "read from the photo",
    BatchSource.USER_CORRECTED: "corrected by you",
    BatchSource.USER_ENTERED: "typed by you",
}


def _e(value: object) -> str:
    return escape("" if value is None else str(value), quote=True)


def status_kind(result) -> str:
    """Presentation bucket of a result (a label for styling only; the decision itself is untouched)."""
    if result.rejection is not None:
        return "rejected"
    d = result.decision
    if d is None or d.is_system_error:
        return "system"
    return {Status.ALERT_FOUND: "alert", Status.NO_ALERT_FOUND: "no_alert", Status.EXPIRED: "expired"}.get(d.status, "unable")


def _hero(result, period: str, eyebrow: str = "Result") -> str:
    kind = status_kind(result)
    glyph = ACCENTS[kind][1]
    if kind == "rejected":
        headline, lead, meta = "This photo could not be used", result.rejection.message, ""
    else:
        d = result.decision
        headline, lead = d.headline, d.explanation
        meta = ""
        if kind not in ("system",) and d.batch_as_read:
            how = SOURCE_WORDS.get(d.batch_source, "")
            tags = [how] + (["you compared it with the pack"] if d.batch_confirmed else [])
            meta = (f'<p class="mcr-batch"><span class="mcr-k">Batch checked</span>'
                    f'<b class="mcr-mono">{_e(d.batch_as_read)}</b><em>{_e("; ".join(t for t in tags if t))}</em></p>')
    scope = "" if kind == "rejected" else f'<p class="mcr-scope">Checked against: {_e(period)} CDSCO NSQ list only.</p>'
    role = "alert" if kind in ("alert", "system", "rejected") else "status"
    return (f'<section class="mcr-hero" data-status="{kind}" role="{role}">'
            f'<div class="mcr-glyph" aria-hidden="true">{glyph}</div>'
            f'<div class="mcr-hero-body"><p class="mcr-eyebrow">{_e(eyebrow)}</p><h2 class="mcr-headline">{_e(headline)}</h2>'
            f'<p class="mcr-lead">{_e(lead)}</p>{meta}{scope}</div></section>')


def _photo_alert(result, period: str) -> str:
    """Alert-level section for the photo's preserved alert, shown above the result for the user's own batch."""
    photo = result.preserved_photo_alert
    if photo is None:
        return ""
    d = photo.decision
    lead = result.preserved_photo_alert_text(period)
    return (f'<section class="mcr-hero mcr-photo" data-status="alert" role="alert">'
            f'<div class="mcr-glyph" aria-hidden="true">{ACCENTS["alert"][1]}</div>'
            f'<div class="mcr-hero-body"><p class="mcr-eyebrow">From the photo</p>'
            f'<h2 class="mcr-headline">Alert found for the batch read from the photo</h2>'
            f'<p class="mcr-lead">{_e(lead)}</p>'
            f'<p class="mcr-batch"><span class="mcr-k">Batch read from the photo</span>'
            f'<b class="mcr-mono">{_e(d.batch_as_read)}</b><em>read from the photo</em></p></div></section>'
            f'{_action_check(photo)}{_record(photo)}')


def _action_check(result) -> str:
    d = result.decision
    if d is None or d.is_system_error or d.status is not Status.ALERT_FOUND or not d.action_check:
        return ""
    return (f'<aside class="mcr-callout" data-tone="warn"><p class="mcr-callout-title">Check before acting</p>'
            f'<p>{_e(d.action_check)}</p></aside>')


def _card(label: str, state: FieldState, raw: str | None, note: str, extra: str = "", confirmed: bool = False) -> str:
    value = (f'<p class="mcr-val mcr-mono">{_e(raw)}</p>' if raw else '<p class="mcr-val mcr-none">Not found</p>')
    sub = f'<p class="mcr-sub">{_e(note)}</p>' if note else ""
    chip = (f'<span class="mcr-chip">{_e(CHIP_WORDS[state])}</span>'
            + ('<span class="mcr-chip mcr-chip-ok">Confirmed by you</span>' if confirmed else ""))
    return (f'<li class="mcr-card" data-state="{state.value}"><p class="mcr-k">{_e(label)}</p>{value}'
            f'<p class="mcr-chip-row">{chip}</p>{sub}{extra}</li>')


def _readings(result) -> str:
    d, ex = result.decision, result.extraction
    if result.rejection is not None or d is None or d.is_system_error or ex is None:
        return ""
    extra = ""
    if result.manual is not None and result.manual.source is not BatchSource.OCR:
        who = "corrected by you" if result.manual.source is BatchSource.USER_CORRECTED else "typed by you"
        ok = '<span class="mcr-chip mcr-chip-ok">Confirmed by you</span>' if d.batch_confirmed else ""
        extra = (f'<p class="mcr-used"><span class="mcr-k">Batch used for this result</span>'
                 f'<b class="mcr-mono">{_e(result.manual.raw)}</b><em>{_e(who)}; not read from the photo</em>{ok}</p>')
    own_batch_confirmed = d.batch_confirmed and d.batch_source is BatchSource.OCR  # a user's own value carries its tick in `extra`
    cards = (_card("Batch number", ex.batch.state, ex.batch.raw, ex.batch.reason, extra, own_batch_confirmed)
             + _card("Expiry date", ex.expiry.state, ex.expiry.raw, ex.expiry.reason)
             + _card("Manufacturing date", ex.manufacturing.state, ex.manufacturing.raw, ex.manufacturing.reason))
    states = {ex.batch.state, ex.expiry.state, ex.manufacturing.state}
    legend = ""
    if FieldState.READ in states:
        legend = f'<p class="mcr-legend"><b>Read</b> means {_e(FIELD_WORDS[FieldState.READ])}.</p>'
    return f'<h3 class="mcr-h">What was read from the photo</h3><ul class="mcr-cards">{cards}</ul>{legend}'


def _record(result) -> str:
    d, r = result.decision, result.matched_record
    if d is None or d.is_system_error or d.status is not Status.ALERT_FOUND or r is None:
        return ""
    mine = "Batch read from the photo" if d.batch_source is BatchSource.OCR else "Batch entered by you"
    rows = (("Serial", r.serial), ("Product", r.product_name), ("Manufacturing date", r.manufacturing_date),
            ("Expiry date", r.expiry_date), ("Manufactured by", r.manufactured_by), ("NSQ result", r.nsq_result),
            ("Reported by", f"{r.reporting_source} - {r.reporting_lab_or_state}"), ("Reporting period", r.reporting_month_year))
    dl = "".join(f'<div class="mcr-row"><dt>{_e(k)}</dt><dd>{_e(v)}</dd></div>' for k, v in rows)
    return ('<h3 class="mcr-h">Matched NSQ record (as published by CDSCO)</h3>'
            '<div class="mcr-compare">'
            f'<div class="mcr-side"><p class="mcr-k">{mine}</p><p class="mcr-val mcr-mono">{_e(d.batch_as_read or "-")}</p></div>'
            '<div class="mcr-vs" aria-hidden="true">vs</div>'
            f'<div class="mcr-side"><p class="mcr-k">Listed batch</p><p class="mcr-val mcr-mono">{_e(r.batch_number)}</p></div></div>'
            f'<dl class="mcr-record">{dl}</dl>')


def top_html(result, period: str) -> str:
    """Status banner, the alert's action check, the three reading cards and (for an alert) the matched record. After a manual
    entry that follows a photo alert, the photo's alert (banner, action check, record) is shown first and stays visible."""
    notice = _photo_alert(result, period)
    eyebrow = "Result for the batch you entered" if notice else "Result"
    return (f"<style>{css()}</style><div class=\"mcr\">{notice}{_hero(result, period, eyebrow)}{_action_check(result)}"
            f"{_readings(result)}{_record(result)}</div>")


def bottom_html(result) -> str:
    """Why this result and the notes (always visible). The batch readings seen are clickable buttons in the batch form (app.py)."""
    d, ex = result.decision, result.extraction
    if d is None:
        return ""
    parts: list[str] = []
    if not (result.rejection is not None or d.is_system_error):
        if d.evidence:
            parts.append('<h3 class="mcr-h">Why this result</h3><ul class="mcr-why">'
                         + "".join(f"<li>{_e(line)}</li>" for line in d.evidence) + "</ul>")
    if d.caveats:
        notes = [c for c in d.caveats if c != LIMITATION_TEXT]
        body = "".join(f"<li>{_e(c)}</li>" for c in notes)
        lim = f'<p class="mcr-limit">{_e(LIMITATION_TEXT)}</p>' if LIMITATION_TEXT in d.caveats else ""
        parts.append(f'<h3 class="mcr-h">Please note</h3>' + (f'<ul class="mcr-why">{body}</ul>' if body else "") + lim)
    return f'<div class="mcr">{"".join(parts)}</div>' if parts else ""


def suggestions_intro_html() -> str:
    """Heading of the clickable batch readings (the buttons themselves are native widgets, see app.py)."""
    return ('<p class="mcr-suggest-intro"><span class="mcr-k">Batch readings seen across the passes</span>'
            'Select one to fill the box below exactly as it was read. Selecting does not confirm it: compare it with the pack, '
            'correct it if needed, then tick the confirmation box.</p>')


def steps_html() -> str:
    """The three steps for the batch correction form. Wording keeps the project's look-alike and confirmation rules."""
    return ('<ol class="mcr-steps">'
            '<li><b>Compare</b> the number below with the one printed on the pack.</li>'
            '<li><b>Correct it</b> if it is wrong or missing: type it exactly as printed '
            '(keep letters and digits as they are: O is not 0, I is not 1, S is not 5).</li>'
            '<li><b>Confirm</b> by ticking the box, then press the button.</li></ol>')


def css() -> str:
    a = {k: v[0] for k, v in ACCENTS.items()}
    tones = "".join(
        f'.mcr-hero[data-status="{k}"] {{ --mc-acc: {c}; }}\n' for k, c in a.items())
    return tones + """
.mcr { --mc-text:#eaf4ff; --mc-muted:#b4c7dd; --mc-line:rgba(120,220,255,.18); --mc-card:rgba(255,255,255,.045);
  font-family: "Segoe UI Variable Text","Segoe UI Variable","Segoe UI",system-ui,sans-serif; color: var(--mc-text); margin: 1.4rem 0 0; }
:where(.mcr) :where(p, ul, ol, dl, dd, dt, h2, h3) { margin: 0; padding: 0; }  /* zero specificity: every component rule below can set its own spacing */
.mcr-mono { font-family: "Cascadia Mono","Cascadia Code",Consolas,"Courier New",monospace; font-variant-ligatures: none; letter-spacing: .05em; overflow-wrap: anywhere; }
.mcr-k { display: block; font-size: .72rem; font-weight: 600; letter-spacing: .14em; text-transform: uppercase; color: var(--mc-muted); }
.mcr-h { font-size: .8rem; font-weight: 650; letter-spacing: .16em; text-transform: uppercase; color: #67e8f9; margin: 2.1rem 0 .85rem; display: flex; align-items: center; gap: .8rem; }
.mcr-h::after { content: ""; flex: 1; height: 1px; background: var(--mc-line); }

/* status banner: the first thing on the result */
.mcr-hero { --mc-acc: #7dd3fc; display: flex; gap: 1.4rem; align-items: flex-start; padding: 1.6rem 1.8rem 1.7rem; border-radius: 22px;
  border: 1px solid color-mix(in srgb, var(--mc-acc) 45%, transparent); border-left: 8px solid var(--mc-acc);
  background: linear-gradient(135deg, color-mix(in srgb, var(--mc-acc) 16%, #06142b) 0%, rgba(8,24,50,.9) 70%); }
.mcr-hero[data-status="system"] { border-style: dashed; border-left-style: solid; }
.mcr-photo { margin-bottom: 1.4rem; }
.mcr-glyph { flex: none; width: 3.1rem; height: 3.1rem; border-radius: 50%; border: 2.5px solid var(--mc-acc); color: var(--mc-acc);
  display: grid; place-items: center; font-size: 1.7rem; font-weight: 700; line-height: 1; font-family: Georgia,"Times New Roman",serif; margin-top: .15rem; }
.mcr-hero-body { min-width: 0; }
.mcr-eyebrow { font-size: .74rem; font-weight: 650; letter-spacing: .22em; text-transform: uppercase; color: var(--mc-acc); }
.mcr-headline { font-family: "Segoe UI Variable Display","Segoe UI Variable Text","Segoe UI",sans-serif; font-size: clamp(2rem, 4.6vw, 2.9rem); font-weight: 650;
  letter-spacing: -.025em; line-height: 1.08; color: #fff; margin: .25rem 0 .75rem !important; }
.mcr-lead { font-size: 1.08rem; line-height: 1.6; color: var(--mc-text); max-width: 46rem; }
.mcr-batch, .mcr-used { display: flex; flex-wrap: wrap; align-items: baseline; gap: .35rem 1rem; margin-top: 1.1rem !important; padding-top: 1rem; border-top: 1px solid var(--mc-line); }
.mcr-batch b, .mcr-used b { font-size: 1.45rem; font-weight: 650; color: #fff; }
.mcr-batch em, .mcr-used em { font-style: normal; font-size: .9rem; color: var(--mc-muted); }
.mcr-used { margin-top: .9rem !important; }
.mcr-scope { margin-top: .9rem !important; font-size: .9rem; color: var(--mc-muted); }
.mcr-batch + .mcr-scope { margin-top: .6rem !important; }

/* callouts: the alert's action check, and the notes */
.mcr-callout { margin-top: 1rem; padding: 1.15rem 1.4rem 1.25rem; border-radius: 16px; border: 1px solid rgba(251,191,36,.55); background: rgba(251,191,36,.09); }
.mcr-callout-title { font-size: 1.05rem; font-weight: 650; color: #fcd34d; margin-bottom: .4rem !important; }
.mcr-callout p { line-height: 1.6; font-size: 1rem; }

/* the three readings */
.mcr-cards { list-style: none; display: grid; grid-template-columns: repeat(auto-fit, minmax(14.5rem, 1fr)); gap: .9rem; }
.mcr-card { padding: 1.1rem 1.25rem 1.2rem; border-radius: 16px; border: 1px solid var(--mc-line); background: var(--mc-card); min-width: 0; }
.mcr-card[data-state="ambiguous"] { border-color: rgba(251,191,36,.5); }
.mcr-val { font-size: 1.65rem; font-weight: 650; color: #fff; margin: .45rem 0 .6rem !important; line-height: 1.2; }
.mcr-none { font-size: 1.15rem; font-weight: 500; color: var(--mc-muted); font-style: italic; }
.mcr-chip-row { margin: 0; display: flex; flex-wrap: wrap; gap: .4rem; }
.mcr-chip-ok { border-color: rgba(125,211,252,.8); background: rgba(125,211,252,.12); color: #e0f2fe; }  /* neutral blue, never green */
.mcr-chip { display: inline-block; padding: .18rem .65rem; border-radius: 999px; font-size: .78rem; font-weight: 600; letter-spacing: .03em; border: 1px solid rgba(125,211,252,.45); color: #bae6fd; }
.mcr-card[data-state="ambiguous"] .mcr-chip { border-color: rgba(251,191,36,.6); color: #fcd34d; }
.mcr-card[data-state="not_found"] .mcr-chip-row { display: none; }  /* the value already says "Not found"; do not repeat it as a chip */
.mcr-sub { margin-top: .6rem !important; font-size: .88rem; line-height: 1.5; color: var(--mc-muted); }
.mcr-card .mcr-used { margin-top: .85rem !important; flex-direction: column; gap: .15rem; }
.mcr-card .mcr-used b { font-size: 1.05rem; }
.mcr-legend { margin-top: .8rem !important; font-size: .88rem; color: var(--mc-muted); }
.mcr-legend b { color: var(--mc-text); font-weight: 600; }

/* matched record: batch against listed batch, then the record */
.mcr-compare { display: grid; grid-template-columns: 1fr auto 1fr; gap: .9rem; align-items: stretch; }
.mcr-side { padding: 1.1rem 1.25rem; border-radius: 16px; border: 1px solid var(--mc-line); background: var(--mc-card); min-width: 0; }
.mcr-vs { align-self: center; font-size: .8rem; letter-spacing: .14em; text-transform: uppercase; color: var(--mc-muted); }
.mcr-record { margin-top: .9rem !important; display: grid; grid-template-columns: repeat(auto-fit, minmax(16rem, 1fr)); gap: .25rem 2rem; padding: .6rem 1.25rem; border-radius: 16px; border: 1px solid var(--mc-line); background: var(--mc-card); }
.mcr-row { padding: .65rem 0; border-bottom: 1px solid rgba(120,220,255,.1); min-width: 0; }
.mcr-row dt { font-size: .72rem; font-weight: 600; letter-spacing: .14em; text-transform: uppercase; color: var(--mc-muted); }
.mcr-row dd { font-size: 1.02rem; color: #fff; margin-top: .15rem !important; line-height: 1.4; overflow-wrap: anywhere; }

/* explanation and notes */
.mcr-why { list-style: none; display: grid; gap: .6rem; }
.mcr-why li { position: relative; padding-left: 1.2rem; line-height: 1.6; font-size: .98rem; color: var(--mc-text); }
.mcr-why li::before { content: ""; position: absolute; left: .1rem; top: .72em; width: .4rem; height: .4rem; border-radius: 50%; background: #67e8f9; }
.mcr-limit { margin-top: 1rem !important; padding: 1rem 1.25rem; border-radius: 14px; border: 1px solid var(--mc-line); background: var(--mc-card); font-size: .98rem; line-height: 1.6; color: var(--mc-text); }

/* clickable batch readings (native st.button widgets: keyboard operable, real focus). Selected = filled + check icon, so colour is never the only signal */
.mcr-suggest-intro { font-size: .92rem; line-height: 1.5; color: #b4c7dd; margin: .2rem 0 .7rem !important; }
.mcr-suggest-intro .mcr-k { margin-bottom: .25rem; }
.st-key-mc_suggest { gap: .55rem !important; margin-bottom: 1.1rem; }
[class*="st-key-mc_sugg_"] button { font-family: "Cascadia Mono","Cascadia Code",Consolas,"Courier New",monospace !important; font-size: 1.05rem !important; font-weight: 600 !important;
  letter-spacing: .06em; min-height: 2.6rem; padding: .35rem 1rem !important; border-radius: 12px !important; color: #fde68a !important;
  border: 1.5px solid rgba(251,191,36,.5) !important; background: rgba(251,191,36,.07) !important; }
[class*="st-key-mc_sugg_"] button:hover { border-color: rgba(251,191,36,.9) !important; background: rgba(251,191,36,.16) !important; }
[class*="st-key-mc_sugg_on_"] button { color: #ffffff !important; border: 2px solid #22d3ee !important; background: rgba(34,211,238,.2) !important; }
[class*="st-key-mc_sugg_"] button:focus-visible { outline: 3px solid #67e8f9 !important; outline-offset: 3px !important; }

/* the batch correction and confirmation panel (native widgets, styled) */
.st-key-mc_verify { margin-top: 2rem; padding: 1.6rem 1.8rem 1.8rem; border-radius: 22px; border: 1px solid rgba(34,211,238,.4); background: linear-gradient(160deg, rgba(34,211,238,.09), rgba(8,24,50,.55)); }
.st-key-mc_verify h3 { font-size: 1.3rem; font-weight: 650; letter-spacing: -.01em; color: #fff; padding: 0 !important; margin-bottom: .6rem; }
.mcr-steps { list-style: none; counter-reset: s; display: grid; gap: .6rem; margin: .4rem 0 1.1rem !important; padding: 0 !important; }
.mcr-steps li { counter-increment: s; position: relative; padding-left: 2.4rem; line-height: 1.55; font-size: .98rem; color: #eaf4ff; }
.mcr-steps li::before { content: counter(s); position: absolute; left: 0; top: .05rem; width: 1.6rem; height: 1.6rem; border-radius: 50%; border: 1.5px solid #22d3ee; color: #67e8f9;
  display: grid; place-items: center; font-size: .85rem; font-weight: 700; }
.mcr-steps b { color: #fff; font-weight: 650; }
.mcr-confnote { font-size: .88rem; color: #b4c7dd; margin: 0 0 1rem !important; line-height: 1.5; }
.st-key-manual_text input { font-family: "Cascadia Mono","Cascadia Code",Consolas,"Courier New",monospace !important; font-size: 1.4rem !important; font-weight: 650 !important; letter-spacing: .07em; padding: .75rem 1rem !important; }
.st-key-manual_confirmed { margin: .4rem 0 .8rem; }
.st-key-manual_confirmed label { padding: .9rem 1.1rem; border-radius: 14px; border: 1px solid rgba(120,220,255,.28); background: rgba(255,255,255,.04); width: 100%; align-items: flex-start; }
.st-key-manual_confirmed label:has(input:checked) { border-color: #22d3ee; background: rgba(34,211,238,.12); }
.st-key-mc_verify button[kind="primary"], .st-key-mc_verify button[data-testid="stBaseButton-primary"] { color: #04122a !important; font-weight: 650; padding: .6rem 1.4rem; }

@media (max-width: 720px) {
  .mcr-hero { flex-direction: column; gap: .9rem; padding: 1.2rem 1.15rem 1.3rem; border-left-width: 6px; }
  .mcr-compare { grid-template-columns: 1fr; }
  .mcr-vs { justify-self: center; }
  .st-key-mc_verify { padding: 1.2rem 1rem 1.3rem; }
}
"""
