"""MedCheck - Streamlit interface. Run with:  streamlit run app.py

The UI contains no matching rules; it only collects an image, calls the pipeline and shows the result.
Photos stay in memory: nothing is written to disk, logged or sent anywhere.
"""
from __future__ import annotations

import hashlib

import streamlit as st

from medcheck.models import FieldState, Status
from medcheck.pipeline import MedCheckPipeline, ScanResult

st.set_page_config(page_title="MedCheck", page_icon="💊", layout="centered")


@st.cache_resource(show_spinner=False)
def get_pipeline() -> MedCheckPipeline:
    """Dataset + index only (public reference data); never holds user images or text."""
    return MedCheckPipeline.load()


FIELD_WORDS = {FieldState.READ: "read consistently", FieldState.AMBIGUOUS: "uncertain", FieldState.NOT_FOUND: "not found"}


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
        show_field("Batch number", ex.batch.state, ex.batch.raw, ex.batch.reason)
        show_field("Expiry date", ex.expiry.state, ex.expiry.raw, ex.expiry.reason)
        show_field("Manufacturing date", ex.manufacturing.state, ex.manufacturing.raw, ex.manufacturing.reason)

    if d.status is Status.ALERT_FOUND and result.matched_record is not None:
        r = result.matched_record
        st.subheader("Matched NSQ record (as published by CDSCO)")
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
            st.text(f"OCR engine: {result.engine_version}; passes: {result.ocr_passes}; variants: {', '.join(result.variants_used)}; "
                    f"time: {result.elapsed_seconds:.1f}s")
            st.text(ex.product_text or "(no text recognised)")


def main() -> None:
    pipeline = get_pipeline()
    period = pipeline.dataset.reporting_period if pipeline.dataset else "August 2026 (dataset unavailable)"

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

    if data is not None:
        try:
            st.image(data, caption="Your photo (not stored)", use_container_width=True)
        except Exception:  # an unreadable file must reach the pipeline, which explains the problem
            st.caption("A preview is not available for this file.")
        if st.button("Check this photo", type="primary"):
            with st.spinner("Reading the photo..."):
                st.session_state["result"] = pipeline.check(data)
                st.session_state["result_digest"] = digest

    result = st.session_state.get("result")
    if result is not None:
        render_status(result, period)
        render_details(result)
        if st.button("Clear and start over"):
            st.session_state.pop("result", None)
            st.session_state["result_digest"] = None
            st.rerun()
    elif data is None:
        st.caption("Tip: photograph the line that says 'B.No.' or 'Batch No.' in good light, in focus, filling most of the frame.")


main()
