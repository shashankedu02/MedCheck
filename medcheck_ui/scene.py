"""Mounts the 3D stage (Components V2). The stage is purely decorative: it is given ONLY a phase and a status name.

Privacy boundary (enforced by tests/test_ui_scene.py): no image, filename, OCR text, batch number or record ever reaches
the browser component. The colour of a status is a tint, never a verdict: no_alert is a calm cyan, never a green tick.
"""
from __future__ import annotations

import functools
import mimetypes
from pathlib import Path

import streamlit as st

from medcheck.models import Decision, Status

ASSETS = Path(__file__).resolve().parent / "assets"
ALLOWED_FIELDS = ("phase", "status")
PHASES = ("idle", "scanning", "result")
STATUSES = ("alert", "unable", "no_alert", "error")

# Streamlit serves ./static with the type the OS reports for the extension; on a machine whose registry maps .js
# to text/plain the browser would refuse the module (X-Content-Type-Options: nosniff). Make the type explicit.
mimetypes.add_type("text/javascript", ".js")
mimetypes.add_type("text/javascript", ".mjs")


def status_key(decision: Decision | None) -> str | None:
    """Tint category for a finished decision. Derived only from the decision's status; never from its content."""
    if decision is None:
        return None
    if decision.is_system_error:
        return "error"
    return {Status.ALERT_FOUND: "alert", Status.NO_ALERT_FOUND: "no_alert", Status.EXPIRED: "unable",
            Status.UNABLE_TO_VERIFY: "unable"}.get(decision.status)


def scene_payload(phase: str, status: str | None = None) -> dict:
    """The complete, closed set of data given to the browser component."""
    if phase not in PHASES:
        raise ValueError(f"unknown phase {phase!r}")
    if status is not None and status not in STATUSES:
        raise ValueError(f"unknown status {status!r}")
    return {"phase": phase, "status": status if phase == "result" else None}


@functools.cache
def _component():
    # Registered once per server process (re-registering the same name on every rerun logs a warning).
    return st.components.v2.component("medcheck_stage", html="", js=(ASSETS / "scene.js").read_text(encoding="utf-8"))


def render_scene(slot, phase: str, status: str | None = None) -> None:
    """Draw/update the stage inside `slot` (an st.empty()).

    No widget key: one script run mounts the component up to three times (idle, scanning, result) and Streamlit rejects a
    duplicate key. Each mount is a new instance, but the browser keeps ONE scene (window.__mcStage) and only updates its state."""
    payload = scene_payload(phase, status)
    with slot:
        _component()(data=payload, height=1)
