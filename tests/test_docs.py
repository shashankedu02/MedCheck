"""Live documentation must not contain broken relative links (docs/archive is history and exempt)."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LINK = re.compile(r"\]\(([^)#\s]+)(?:#[^)]*)?\)")


def _live_markdown():
    for p in ROOT.rglob("*.md"):
        rel = p.relative_to(ROOT).as_posix()
        if rel.startswith((".venv/", "docs/archive/", "data/")):
            continue
        yield p


def test_no_broken_relative_links_in_live_docs():
    broken = []
    for p in _live_markdown():
        for target in LINK.findall(p.read_text(encoding="utf-8")):
            if target.startswith(("http://", "https://", "mailto:")):
                continue
            if not (p.parent / target).resolve().exists():
                broken.append((p.relative_to(ROOT).as_posix(), target))
    assert broken == []


def test_live_docs_do_not_reference_removed_files():
    removed = ("MATCHING_LOGIC.md", "MATCHING_DECISION_MATRIX.md", "MANIFEST.md", "IMPLEMENTATION_BLUEPRINT.md", "PROJECT_CONTEXT.md")
    offenders = []
    for p in _live_markdown():
        text = p.read_text(encoding="utf-8")
        offenders += [(p.name, r) for r in removed if r in text and p.name not in ("CHANGELOG.md", "BUILD_PROGRESS.md")]
    assert offenders == []
