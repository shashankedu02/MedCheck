"""Reproducibly build the canonical MedCheck dataset from the official CDSCO extraction.

Approved transformation (documented in docs/DATASET.md):
  1. Drop the traceability-only "Portal Page" column.
  2. Replace every embedded line break (CRLF, CR or LF) inside a cell with ONE
     ordinary space.
  3. Change nothing else: no trimming, no case or punctuation changes, no repair
     of source errors; every cell is kept as text.

The official extraction is never modified. If any integrity check fails the
script stops without writing output.

Usage:
    python scripts/build_dataset.py            # build (refuses to overwrite a different file silently)
    python scripts/build_dataset.py --check    # verify committed outputs are exactly reproducible
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from medcheck import config  # noqa: E402

TRANSFORM_VERSION = 1
_LINE_BREAK = re.compile(r"\r\n|\r|\n")


class SourceIntegrityError(Exception):
    """The official extraction failed an integrity check; generation must stop."""


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_official(path: Path) -> tuple[bytes, list[list[str]]]:
    raw = path.read_bytes()
    digest = sha256_bytes(raw)
    if digest != config.OFFICIAL_SOURCE_SHA256:
        raise SourceIntegrityError(
            f"official extraction SHA-256 mismatch: expected {config.OFFICIAL_SOURCE_SHA256}, got {digest}"
        )
    text = raw.decode("utf-8-sig")  # source was saved with a BOM; strict decode
    rows = list(csv.reader(io.StringIO(text, newline="")))
    if not rows or tuple(rows[0]) != config.SOURCE_COLUMNS:
        raise SourceIntegrityError(f"unexpected header: {rows[0] if rows else None}")
    body = rows[1:]
    if any(len(r) != len(config.SOURCE_COLUMNS) for r in body):
        raise SourceIntegrityError("row with wrong number of columns")
    serial_idx = config.SOURCE_COLUMNS.index("Serial Number")
    month_idx = config.SOURCE_COLUMNS.index("Reporting Month and Year")
    if [r[serial_idx] for r in body] != [str(i) for i in range(1, len(body) + 1)]:
        raise SourceIntegrityError("serial numbers are not the continuous sequence 1..N")
    if any(r[month_idx] != config.DATASET_REPORTING_PERIOD for r in body):
        raise SourceIntegrityError("row outside the reporting period")
    if any(not c.strip() for r in body for c in r):
        raise SourceIntegrityError("blank cell in official extraction")
    return raw, rows


def transform(rows: list[list[str]]) -> list[list[str]]:
    """Apply the approved transformation. Pure function; no I/O."""
    drop = config.SOURCE_COLUMNS.index(config.SOURCE_EXTRA_COLUMN)
    out = []
    for row in rows:
        kept = [c for i, c in enumerate(row) if i != drop]
        out.append([_LINE_BREAK.sub(" ", c) for c in kept])
    return out


def serialize(rows: list[list[str]]) -> bytes:
    buf = io.StringIO(newline="")
    csv.writer(buf, lineterminator="\n").writerows(rows)
    return buf.getvalue().encode("utf-8")  # no BOM, LF row endings


def build_manifest(source_raw: bytes, canonical_bytes: bytes, row_count: int) -> dict:
    return {
        "dataset_id": "cdsco-nsq-aug-2026",
        "label": config.DATASET_LABEL,
        "reporting_period": config.DATASET_REPORTING_PERIOD,
        "record_count": row_count,
        "columns": list(config.CANONICAL_COLUMNS),
        "source": {
            "file": config.OFFICIAL_SOURCE_PATH.name,
            "sha256": sha256_bytes(source_raw),
            "origin": "https://cdscoonline.gov.in/CDSCO/viewPublicNSQDrug (NSQ Drugs, Aug-2026, source 'All')",
            "details": "data/cdsco_august_2026_nsq_extraction_log.md",
        },
        "canonical": {
            "file": config.CANONICAL_DATASET_PATH.name,
            "sha256": sha256_bytes(canonical_bytes),
            "encoding": "utf-8 (no BOM), LF row endings, RFC 4180 quoting",
        },
        "transformation": {
            "version": TRANSFORM_VERSION,
            "script": "scripts/build_dataset.py",
            "steps": [
                "drop 'Portal Page' column",
                "replace each embedded line break inside a cell with one ordinary space",
                "no other change (no trimming, case, punctuation or error repair)",
            ],
        },
        "known_source_anomalies": [
            "serial 72 product name contains 'Potass um' and '?' (preserved)",
            "serial 152 product name contains '?' and an unclosed '(' (preserved)",
            "serial 136 expiry (Jun-2025) precedes manufacture (Jul-2025) (preserved)",
            "serials 150 and 153 batch numbers end with ',' (preserved)",
            "serial 121 batch '0l25038' has a lowercase L (preserved)",
            "serials 38 and 157 batches differ only by digit 0 vs letter O and a space (preserved)",
        ],
    }


def manifest_bytes(manifest: dict) -> bytes:
    return (json.dumps(manifest, indent=2, ensure_ascii=True) + "\n").encode("utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--check", action="store_true", help="verify committed outputs equal a fresh build")
    args = parser.parse_args(argv)

    try:
        raw, rows = read_official(config.OFFICIAL_SOURCE_PATH)
    except (SourceIntegrityError, OSError, UnicodeDecodeError) as exc:
        print(f"STOP: official extraction cannot be trusted: {exc}", file=sys.stderr)
        return 2

    canonical_rows = transform(rows)
    canonical = serialize(canonical_rows)
    manifest = manifest_bytes(build_manifest(raw, canonical, len(canonical_rows) - 1))

    if args.check:
        ok = (
            config.CANONICAL_DATASET_PATH.exists()
            and config.DATASET_MANIFEST_PATH.exists()
            and config.CANONICAL_DATASET_PATH.read_bytes() == canonical
            and config.DATASET_MANIFEST_PATH.read_bytes() == manifest
        )
        print("OK: committed dataset and manifest are exactly reproducible" if ok else "MISMATCH: rebuild required")
        return 0 if ok else 1

    config.CANONICAL_DATASET_PATH.write_bytes(canonical)
    config.DATASET_MANIFEST_PATH.write_bytes(manifest)
    print(f"wrote {config.CANONICAL_DATASET_PATH.name}: {len(canonical_rows) - 1} records, sha256 {sha256_bytes(canonical)}")
    print(f"wrote {config.DATASET_MANIFEST_PATH.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
