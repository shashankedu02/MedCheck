"""Hosted-mode privacy wording (D-034). Wording only: it never touches a check, rule or threshold."""
from __future__ import annotations

import re
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from medcheck_ui import hosting, theme

ROOT = Path(__file__).resolve().parent.parent
LOCAL_CLAIMS = re.compile(r"this computer|offline|never leaves|on your computer", re.I)


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    monkeypatch.delenv(hosting.HOSTED_ENV, raising=False)


def test_default_on_a_developer_machine_is_local():
    assert hosting.is_hosted() is False


@pytest.mark.parametrize("value,expected", [("1", True), ("true", True), ("YES", True), ("0", False), ("false", False), ("no", False)])
def test_the_environment_flag_decides(monkeypatch, value, expected):
    monkeypatch.setenv(hosting.HOSTED_ENV, value)
    assert hosting.is_hosted() is expected


def test_the_cloud_mount_path_is_recognised(monkeypatch):
    class Fake:
        def __init__(self, *_a): pass
        def resolve(self): return self
        def as_posix(self): return "/mount/src/medcheck/medcheck_ui/hosting.py"
    monkeypatch.setattr(hosting, "Path", Fake)
    assert hosting.is_hosted() is True
    monkeypatch.setenv(hosting.HOSTED_ENV, "0")   # an explicit local flag wins
    assert hosting.is_hosted() is False


def test_local_wording_is_unchanged():
    story = theme.story_html(220, "AUG-2026")
    assert "everything runs on this computer" in story and "mc-hosted" not in story
    assert hosting.sidebar_note() == hosting.SIDEBAR_LOCAL
    assert "up to two offline engines" in " ".join(t[4] for t in theme.scene_texts("AUG-2026"))


def test_hosted_wording_makes_no_local_only_claim(monkeypatch):
    monkeypatch.setenv(hosting.HOSTED_ENV, "1")
    story = theme.story_html(220, "AUG-2026")
    visible = re.sub(r"<style.*?</style>", "", story, flags=re.S)
    assert 'id="mc-hosted"' in story                      # the marker the scanning panel reads
    assert not LOCAL_CLAIMS.search(visible), LOCAL_CLAIMS.search(visible)
    note = hosting.sidebar_note()
    assert not LOCAL_CLAIMS.search(note) and "sent to the server" in note and "does not save or log" in note
    assert "no other service" in note or "no other service" in note.lower()


def test_hosted_wording_keeps_the_limits_and_never_claims_safety(monkeypatch):
    monkeypatch.setenv(hosting.HOSTED_ENV, "1")
    text = " ".join(t[4] for t in theme.scene_texts("AUG-2026")) + hosting.sidebar_note() + hosting.HERO_NOTE_HOSTED
    assert "not an authenticity or safety test" in text.lower() and "not medical advice" in text.lower()
    assert "can still be wrong" in text                   # the agreement caveat survives
    assert not re.search(r"\b(guarantee|always safe|genuine medicine)\b", text, re.I)


def test_the_hosted_app_shows_the_hosted_sidebar_note(monkeypatch):
    monkeypatch.setenv(hosting.HOSTED_ENV, "1")
    at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=60).run()
    assert not at.exception
    captions = " ".join(c.value for c in at.sidebar.caption)
    assert hosting.SIDEBAR_HOSTED in captions and hosting.SIDEBAR_LOCAL not in captions


def test_the_local_app_keeps_the_local_sidebar_note():
    at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=60).run()
    assert hosting.SIDEBAR_LOCAL in " ".join(c.value for c in at.sidebar.caption)


def test_scene_js_has_both_reading_panel_wordings_and_no_figures():
    js = (ROOT / "medcheck_ui" / "assets" / "scene.js").read_text(encoding="utf-8")
    assert "HUD_LOCAL" in js and "HUD_HOSTED" in js and "getElementById('mc-hosted')" in js
