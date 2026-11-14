"""Fail-closed loader for the canonical NSQ dataset.

Any problem raises a DatasetError subclass. Callers must treat these as SYSTEM
failures, never as "No alert found".
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
from dataclasses import dataclass
from pathlib import Path

from . import config


class DatasetError(Exception):
    """Base class: the dataset cannot be trusted; matching must not run."""

    code = "dataset_error"


class DatasetMissingError(DatasetError):
    code = "dataset_missing"


class DatasetSchemaError(DatasetError):
    code = "dataset_schema"


class DatasetIntegrityError(DatasetError):
    code = "dataset_integrity"


@dataclass(frozen=True)
class DatasetRecord:
    """One source row; every value is the raw dataset string."""

    serial: int
    product_name: str
    batch_number: str
    manufacturing_date: str
    expiry_date: str
    manufactured_by: str
    nsq_result: str
    reporting_source: str
    reporting_lab_or_state: str
    reporting_month_year: str


@dataclass(frozen=True)
class Dataset:
    records: tuple[DatasetRecord, ...]
    reporting_period: str
    label: str
    sha256: str
    manifest: dict

    def __len__(self) -> int:
        return len(self.records)


def load_dataset(
    csv_path: Path | None = None,
    manifest_path: Path | None = None,
) -> Dataset:
    csv_path = Path(csv_path or config.CANONICAL_DATASET_PATH)
    manifest_path = Path(manifest_path or config.DATASET_MANIFEST_PATH)

    if not manifest_path.is_file():
        raise DatasetMissingError("dataset manifest not found")
    if not csv_path.is_file():
        raise DatasetMissingError("dataset file not found")

    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        expected_sha = manifest["canonical"]["sha256"]
        expected_count = int(manifest["record_count"])
        expected_columns = tuple(manifest["columns"])
        period = str(manifest["reporting_period"])
        label = str(manifest["label"])
    except (ValueError, KeyError, TypeError) as exc:
        raise DatasetSchemaError(f"dataset manifest is malformed: {type(exc).__name__}") from exc

    raw = csv_path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if digest != expected_sha:
        raise DatasetIntegrityError("dataset SHA-256 does not match the manifest")

    try:
        text = raw.decode("utf-8")  # strict; canonical file has no BOM
    except UnicodeDecodeError as exc:
        raise DatasetSchemaError("dataset is not valid UTF-8") from exc
    if text.startswith("﻿"):
        raise DatasetSchemaError("dataset unexpectedly starts with a BOM")

    try:
        rows = list(csv.reader(io.StringIO(text, newline="")))
    except csv.Error as exc:
        raise DatasetSchemaError("dataset is not parseable CSV") from exc

    if not rows or tuple(rows[0]) != expected_columns or expected_columns != config.CANONICAL_COLUMNS:
        raise DatasetSchemaError("dataset headers do not match the expected schema")
    body = rows[1:]
    if len(body) != expected_count:
        raise DatasetIntegrityError("dataset record count does not match the manifest")

    records: list[DatasetRecord] = []
    seen: set[int] = set()
    for row in body:
        if len(row) != len(config.CANONICAL_COLUMNS):
            raise DatasetSchemaError("dataset row has the wrong number of columns")
        try:
            serial = int(row[0])
        except ValueError as exc:
            raise DatasetSchemaError("non-numeric serial number") from exc
        if serial in seen:
            raise DatasetIntegrityError("duplicate serial number")
        seen.add(serial)
        if not row[1].strip() or not row[2].strip():
            raise DatasetIntegrityError("blank product name or batch number")
        if row[9] != period:
            raise DatasetIntegrityError("row outside the dataset reporting period")
        records.append(DatasetRecord(serial, *row[1:]))

    return Dataset(tuple(records), period, label, digest, manifest)
