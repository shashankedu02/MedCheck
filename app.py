"""MedCheck - Streamlit interface. Run with:  streamlit run app.py

The UI contains no matching rules; it only collects an image, calls the pipeline and shows the result.
Photos stay in memory: nothing is written to disk, logged or sent anywhere.
"""
from __future__ import annotations

import hashlib

import streamlit as st

try:
    from medcheck.models import BatchSource, FieldState, Status
    from medcheck.pipeline import ManualEntryError, MedCheckPipeline, ScanResult
except ImportError:  # the code changed on disk while this server kept the old modules in memory
    st.error(
        "MedCheck's code was updated while this page was running, so the running copy is out of date. "
        "Stop the app (Ctrl+C in the terminal where it is running), start it again with "
        "`streamlit run app.py`, then reload this page."
    )
    st.stop()

st.set_page_config(page_title="MedCheck", page_icon="💊", layout="centered")

try:  # presentation layer (3D stage, theme, story); the app works without it (MEDCHECK_PLAIN_UI=1, or if it fails to load)
    from medcheck_ui import plain_ui
    from medcheck_ui.scene import render_scene, status_key
    from medcheck_ui.theme import render_theme_and_story
except Exception:  # noqa: BLE001 - any failure here must fall back to the plain interface, never break a check
    def plain_ui() -> bool:  # type: ignore[misc]
        return True


@st.cache_resource(show_spinner=False)
def get_pipeline() -> MedCheckPipeline:
    """Dataset + index only (public reference data); never holds user images or text."""
    pipeline = MedCheckPipeline.load()
    pipeline.warm_up()  # load the OCR models once at start, not inside the first check
    return pipeline


FIELD_WORDS = {FieldState.READ: "agreed by the OCR passes - not yet checked against the pack", FieldState.AMBIGUOUS: "uncertain", FieldState.NOT_FOUND: "not found"}


def show_field(label: str, state: FieldState, raw: str | None, note: str = "") -> None:
    value = raw if raw else "-"
    st.text(f"{label}: {value}   [{FIELD_WORDS[state]}]" + (f" - {note}" if note else ""))


def render_status(result: ScanResult, period: str) -> None:
    if result.rejection is not None:
        st.error(f"This photo could not be used. {result.rejection.message}")
        return
    d = result.decision
    assert d is not None
    if d.is_system_error:
        st.error(f"**{d.headline}**\n\n{d.explanation}")
    elif d.status is Status.ALERT_FOUND:
        st.error(f"**{d.headline}**\n\n{d.explanation}")
        if d.action_check:
            st.warning(f"**Check before acting:** {d.action_check}")
    elif d.status is Status.EXPIRED:
        st.warning(f"**{d.headline}**\n\n{d.explanation}")
    elif d.status is Status.UNABLE_TO_VERIFY:
        st.warning(f"**{d.headline}**\n\n{d.explanation}")
    else:  # No alert found: deliberately neutral, never a green "safe" style
        st.info(f"**{d.headline}**\n\n{d.explanation}")
    st.caption(f"Checked against: {period} CDSCO NSQ list only.")


def render_details(result: ScanResult) -> None:
    d = result.decision
    if result.rejection is not None or d is None or d.is_system_error:
        if d is not None:
            for c in d.caveats:
                st.caption(c)
        return

    ex = result.extraction
    if ex is not None:
        st.subheader("What was read from the photo")
        show_field("Batch number (OCR)", ex.batch.state, ex.batch.raw, ex.batch.reason)
        if result.manual is not None and result.manual.source is not BatchSource.OCR:
            who = "corrected by you" if result.manual.source is BatchSource.USER_CORRECTED else "typed by you"
            st.text(f"Batch used for this result: {result.manual.raw}   [{who}; not read from the photo]")
        show_field("Expiry date", ex.expiry.state, ex.expiry.raw, ex.expiry.reason)
        show_field("Manufacturing date", ex.manufacturing.state, ex.manufacturing.raw, ex.manufacturing.reason)

    if d.status is Status.ALERT_FOUND and result.matched_record is not None:
        r = result.matched_record
        st.subheader("Matched NSQ record (as published by CDSCO)")
        read_from = "read from the photo" if d.batch_source is BatchSource.OCR else "entered by you"
        st.text(f"Compare: batch {read_from} = {d.batch_as_read or '-'}   |   listed batch = {r.batch_number}")
        for label, value in (
            ("Serial", r.serial), ("Product", r.product_name), ("Batch", r.batch_number),
            ("Manufacturing date", r.manufacturing_date), ("Expiry date", r.expiry_date),
            ("Manufactured by", r.manufactured_by), ("NSQ result", r.nsq_result),
            ("Reported by", f"{r.reporting_source} - {r.reporting_lab_or_state}"),
            ("Reporting period", r.reporting_month_year),
        ):
            st.text(f"{label}: {value}")

    if d.evidence:
        st.subheader("Why")
        for line in d.evidence:
            st.text(f"- {line}")

    if d.status is Status.UNABLE_TO_VERIFY and ex is not None and ex.batch.readings:
        st.text("Batch readings seen: " + " | ".join(ex.batch.readings))

    st.subheader("Please note")
    for c in d.caveats:
        st.caption(c)

    if ex is not None:
        with st.expander("Technical details (recognised text)"):
            st.text(f"OCR engines: {result.engine_version}; passes: {result.ocr_passes}; views: {', '.join(result.variants_used)}; "
                    f"time: {result.elapsed_seconds:.1f}s")
            if ex.batch.reading_sources:
                st.text("Batch readings by source: " + " | ".join(f"{raw} [{src}]" for raw, src in ex.batch.reading_sources))
            if ex.edge_ignored:
                st.caption("A batch-like line touching the edge of the photo was ignored because it may be cut off: " + " | ".join(ex.edge_ignored))
            for note in result.notes:
                st.caption(note)
            st.text(ex.product_text or "(no text recognised)")


MANUAL_KEYS = ("manual_text", "manual_confirmed")


def render_manual_entry(pipeline: MedCheckPipeline, result: ScanResult) -> None:
    """Review / correct / enter the batch. The typed value is never OCR evidence: it goes through the same
    matching rules, and product corroboration still comes only from the photo's text."""
    ex = result.extraction
    if result.rejection is not None or ex is None:
        return
    st.subheader("Check or enter the batch number yourself")
    if result.decision is not None and result.decision.reason_code == "ocr_batch_unconfirmed":
        st.info("Next step: compare the number below with the one printed on the pack, correct it if needed, tick the box and press the button.")
    st.caption(
        "Compare the number below with the one printed on the pack. If it is wrong or missing, type it exactly as printed "
        "(keep letters and digits as they are: O is not 0, I is not 1, S is not 5). "
        "Confirming means you checked the printed batch number; it does not show the medicine is genuine or safe."
    )
    if "manual_text" not in st.session_state:
        st.session_state["manual_text"] = ex.batch.raw if ex.batch.state is FieldState.READ and ex.batch.raw else ""
    # A confirmation belongs to the number it was given for: editing the number clears the tick.
    st.text_input("Batch number as printed on the pack", key="manual_text", max_chars=30,
                  on_change=lambda: st.session_state.__setitem__("manual_confirmed", False))
    st.checkbox("I compared this number with the one printed on the pack (this confirms the printed number only)", key="manual_confirmed")
    if st.button("Check this batch number"):
        try:
            st.session_state["result"] = pipeline.verify_manual(result, st.session_state["manual_text"], bool(st.session_state.get("manual_confirmed")))
            st.rerun()
        except ManualEntryError as exc:
            st.warning(str(exc))


def set_stage(stage, phase: str, result: ScanResult | None = None) -> None:
    """Update the decorative 3D stage. It gets only a phase and a status name; any failure is ignored (it is decoration)."""
    if stage is None:
        return
    try:
        render_scene(stage, phase, status_key(result.decision) if (phase == "result" and result is not None) else None)
    except Exception:  # noqa: BLE001
        pass


def render_tool(pipeline: MedCheckPipeline, period: str, stage) -> None:
    st.title("MedCheck")
    st.write(
        "Upload or take a photo of a medicine strip or box. MedCheck reads the batch number and checks it against the "
        f"**{period} CDSCO NSQ (Not of Standard Quality) alert list only**."
    )
    st.info(
        "This is a lookup aid, not an authenticity or safety test, and not medical advice. A result of "
        "'No alert found' only means no matching entry was found in this one-month list."
    )

    with st.sidebar:
        st.header("About this check")
        if pipeline.dataset is not None:
            st.text(f"List: {pipeline.dataset.label}")
            st.text(f"Records: {len(pipeline.dataset)}")
            st.text(f"Data fingerprint: {pipeline.dataset.sha256[:12]}")
        else:
            st.error("The NSQ list could not be loaded. Checks are disabled.")
        st.caption("Photos are processed in memory on the computer running this app. They are not saved, logged or sent elsewhere.")

    tab_upload, tab_camera = st.tabs(["Upload a photo", "Use the camera"])
    with tab_upload:
        uploaded = st.file_uploader("Photo of the batch/expiry area (JPEG, PNG or WebP, up to 10 MB)", type=["jpg", "jpeg", "png", "webp"])
    with tab_camera:
        captured = st.camera_input("Take a photo")
    source = uploaded or captured
    data = source.getvalue() if source is not None else None

    digest = hashlib.sha256(data).hexdigest() if data else None
    if st.session_state.get("result_digest") != digest and st.session_state.get("result_digest") is not None:
        st.session_state.pop("result", None)  # the image changed or was removed: drop the old result
        st.session_state["result_digest"] = None
        for k in MANUAL_KEYS:
            st.session_state.pop(k, None)

    if data is not None:
        try:
            st.image(data, caption="Your photo (not stored)", use_container_width=True)
        except Exception:  # an unreadable file must reach the pipeline, which explains the problem
            st.caption("A preview is not available for this file.")
        if st.button("Check this photo", type="primary"):
            set_stage(stage, "scanning")  # the beam sweeps while the real OCR below runs
            with st.spinner("Reading the photo..."):
                st.session_state["result"] = pipeline.check(data)
                st.session_state["result_digest"] = digest
                for k in MANUAL_KEYS:
                    st.session_state.pop(k, None)
            set_stage(stage, "result", st.session_state["result"])

    result = st.session_state.get("result")
    if result is not None:
        render_status(result, period)
        render_details(result)
        render_manual_entry(pipeline, result)
        if st.button("Clear and start over"):
            st.session_state.pop("result", None)
            st.session_state["result_digest"] = None
            for k in MANUAL_KEYS:
                st.session_state.pop(k, None)
            st.rerun()
    elif data is None:
        st.caption("Tip: photograph the line that says 'B.No.' or 'Batch No.' in good light, in focus, filling most of the frame.")


def main() -> None:
    pipeline = get_pipeline()
    period = pipeline.dataset.reporting_period if pipeline.dataset else "August 2026 (dataset unavailable)"
    stage = None
    if not plain_ui():
        try:
            render_theme_and_story()
            stage = st.empty()
        except Exception:  # noqa: BLE001 - the interface works without the presentation layer
            stage = None
        prior = st.session_state.get("result")
        set_stage(stage, "result" if prior is not None else "idle", prior)
    with st.container(key="mc_tool"):
        render_tool(pipeline, period, stage)


main()
