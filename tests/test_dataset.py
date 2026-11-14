"""Dataset pipeline and loader tests (milestone M1)."""
from __future__ import annotations

import csv
import io
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from medcheck import config
from medcheck.dataset import (
    DatasetIntegrityError,
    DatasetMissingError,
    DatasetSchemaError,
    load_dataset,
)

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import build_dataset as bd  # noqa: E402


# ---------- transformation unit tests (synthetic) ----------
def test_transform_drops_portal_page_and_flattens_each_break_to_one_space():
    rows = [
        list(config.SOURCE_COLUMNS),
        ["1", "1", "Name\nLine2", "B1", "Jan-2026", "Feb-2027", "Maker\r\nX", "Res\rY", "State Lab", "L", "AUG-2026"],
    ]
    out = bd.transform(rows)
    assert tuple(out[0]) == config.CANONICAL_COLUMNS
    assert out[1][1] == "Name Line2"
    assert out[1][5] == "Maker X"  # CRLF is ONE break -> one space
    assert out[1][6] == "Res Y"


def test_transform_preserves_everything_else():
    tricky = ["1", "1", "Potass um ?  (x", "0l25038,", "Jul-2025", "Jun-2025", " m ", "r", "s", "l", "AUG-2026"]
    out = bd.transform([list(config.SOURCE_COLUMNS), tricky])
    assert out[1] == tricky[1:]


def test_serialize_has_no_bom_and_lf_endings():
    data = bd.serialize([["a", "b c"], ["1", "x,y"]])
    assert not data.startswith(b"\xef\xbb\xbf") and b"\r" not in data


# ---------- committed artefacts ----------
def test_official_source_hash_is_pinned_and_valid():
    raw, rows = bd.read_official(config.OFFICIAL_SOURCE_PATH)
    assert bd.sha256_bytes(raw) == config.OFFICIAL_SOURCE_SHA256
    assert len(rows) == 221


def test_committed_dataset_is_exactly_reproducible():
    assert bd.main(["--check"]) == 0


def test_committed_dataset_matches_independent_flatten_of_official():
    """Independent re-derivation: compare cell by cell, not via the build code path."""
    off = list(csv.reader(io.StringIO(config.OFFICIAL_SOURCE_PATH.read_bytes().decode("utf-8-sig"), newline="")))[1:]
    can = list(csv.reader(io.StringIO(config.CANONICAL_DATASET_PATH.read_text(encoding="utf-8"), newline="")))[1:]
    assert len(off) == len(can) == 220
    for o, c in zip(off, can):
        for ov, cv in zip(o[1:], c):
            assert ov.replace("\r\n", " ").replace("\n", " ").replace("\r", " ") == cv


def test_loads_real_dataset():
    ds = load_dataset()
    assert len(ds) == 220 and ds.reporting_period == "AUG-2026"
    by_serial = {r.serial: r for r in ds.records}
    # source anomalies preserved verbatim, never silently corrected
    assert "Potass um" in by_serial[72].product_name
    assert by_serial[150].batch_number == "GTF2327C,"
    assert by_serial[153].batch_number == "GBT26241,"
    assert by_serial[121].batch_number == "0l25038"
    assert (by_serial[136].manufacturing_date, by_serial[136].expiry_date) == ("Jul-2025", "Jun-2025")
    assert by_serial[38].batch_number == "BKBP02601" and by_serial[157].batch_number == "BKBP O2601"


def test_no_newlines_remain_in_canonical_cells():
    for r in load_dataset().records:
        for v in vars(r).values():
            assert "\n" not in str(v) and "\r" not in str(v)


# ---------- fail-closed behaviour ----------
@pytest.fixture()
def tmp_dataset(tmp_path):
    csv_p, man_p = tmp_path / "d.csv", tmp_path / "m.json"
    shutil.copy(config.CANONICAL_DATASET_PATH, csv_p)
    shutil.copy(config.DATASET_MANIFEST_PATH, man_p)
    return csv_p, man_p


def _rewrite_manifest(man_p, csv_p, **overrides):
    m = json.loads(man_p.read_text())
    m["canonical"]["sha256"] = bd.sha256_bytes(csv_p.read_bytes())
    m.update(overrides)
    man_p.write_text(json.dumps(m))


def test_missing_csv(tmp_dataset):
    csv_p, man_p = tmp_dataset
    csv_p.unlink()
    with pytest.raises(DatasetMissingError):
        load_dataset(csv_p, man_p)


def test_missing_manifest(tmp_dataset):
    csv_p, man_p = tmp_dataset
    man_p.unlink()
    with pytest.raises(DatasetMissingError):
        load_dataset(csv_p, man_p)


def test_tampered_file_fails_hash(tmp_dataset):
    csv_p, man_p = tmp_dataset
    csv_p.write_bytes(csv_p.read_bytes().replace(b"BKBP02601", b"BKBP02602"))
    with pytest.raises(DatasetIntegrityError):
        load_dataset(csv_p, man_p)


def test_header_drift_fails(tmp_dataset):
    csv_p, man_p = tmp_dataset
    csv_p.write_bytes(csv_p.read_bytes().replace(b"Batch Number", b"Batch No", 1))
    _rewrite_manifest(man_p, csv_p)
    with pytest.raises(DatasetSchemaError):
        load_dataset(csv_p, man_p)


def test_bom_rejected(tmp_dataset):
    csv_p, man_p = tmp_dataset
    csv_p.write_bytes(b"\xef\xbb\xbf" + csv_p.read_bytes())
    _rewrite_manifest(man_p, csv_p)
    with pytest.raises(DatasetSchemaError):
        load_dataset(csv_p, man_p)


def test_truncated_file_fails_count(tmp_dataset):
    csv_p, man_p = tmp_dataset
    lines = csv_p.read_bytes().split(b"\n")
    csv_p.write_bytes(b"\n".join(lines[:-3]) + b"\n")
    _rewrite_manifest(man_p, csv_p)
    with pytest.raises(DatasetIntegrityError):
        load_dataset(csv_p, man_p)


def test_malformed_manifest(tmp_dataset):
    csv_p, man_p = tmp_dataset
    man_p.write_text("{not json")
    with pytest.raises(DatasetSchemaError):
        load_dataset(csv_p, man_p)


def test_wrong_reporting_period_fails(tmp_dataset):
    csv_p, man_p = tmp_dataset
    _rewrite_manifest(man_p, csv_p, reporting_period="SEP-2026")
    with pytest.raises(DatasetIntegrityError):
        load_dataset(csv_p, man_p)


# ---------- build script refuses an untrusted source ----------
def test_build_stops_when_source_hash_differs(tmp_path, monkeypatch):
    bad = tmp_path / "src.csv"
    bad.write_bytes(config.OFFICIAL_SOURCE_PATH.read_bytes().replace(b"Aug", b"Sep", 1) + b" ")
    with pytest.raises(bd.SourceIntegrityError):
        bd.read_official(bad)


def test_build_script_check_runs_as_cli():
    r = subprocess.run([sys.executable, str(ROOT / "scripts" / "build_dataset.py"), "--check"], capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
