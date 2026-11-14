"""Real-photograph evaluation workflow: discovery, safety, records, ground truth, run history."""
from __future__ import annotations

import csv
import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path

import pytest
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import run_evaluation  # noqa: E402
import set_ground_truth  # noqa: E402

from medcheck import real_eval as ev  # noqa: E402
from medcheck.ocr import OCREngineUnavailable, find_engine  # noqa: E402
from medcheck.pipeline import MedCheckPipeline  # noqa: E402
from tests.helpers import encode, font_path, render_label  # noqa: E402


def _img(path: Path, size=(400, 350), color="white"):
    Image.new("RGB", size, color).save(path)


@pytest.fixture(scope="module")
def pipe():
    return MedCheckPipeline.load()


@pytest.fixture()
def photos(tmp_path):
    d = tmp_path / "photos"
    d.mkdir()
    _img(d / "2.jpeg")
    _img(d / "10.jpeg", color="gray")
    _img(d / "1.jpeg", color="black")
    return d


def test_ids_are_stable_and_numeric_sorted(photos):
    assert [ev.test_id_for(p) for p in ev.discover(photos)] == ["T001", "T002", "T010"]
    assert ev.test_id_for(Path("front pack.JPG")) == "T-FRONT_PACK"


def test_every_file_gets_a_record_and_bad_files_do_not_stop_the_run(photos, pipe):
    (photos / "3.jpeg").write_bytes(b"not an image at all")
    (photos / "4.gif").write_bytes(b"GIF89a")
    (photos / "notes.txt").write_text("x")
    recs = ev.process_folder(photos, pipe.check, "run_x", {})
    by = {r.filename: r for r in recs}
    assert len(recs) == 6
    assert by["3.jpeg"].actual_outcome == ev.OUT_REJECTED
    assert by["4.gif"].actual_outcome == ev.OUT_UNSUPPORTED
    assert by["notes.txt"].actual_outcome == ev.OUT_UNSUPPORTED
    assert by["1.jpeg"].width == "400" and by["1.jpeg"].height == "350"
    assert by["3.jpeg"].width == ""  # unreadable image: no dimensions invented


def test_checker_exception_is_recorded_by_type_only(photos):
    def boom(_data):
        raise RuntimeError("secret text from the image")

    recs = ev.process_folder(photos, boom, "run_x", {})
    assert {r.actual_outcome for r in recs} == {ev.OUT_ERROR}
    assert all(r.processing_error == "RuntimeError" for r in recs)
    assert "secret" not in repr(recs)


def test_duplicate_content_flagged_and_duplicate_id_not_processed(tmp_path, pipe):
    d = tmp_path / "p"
    d.mkdir()
    _img(d / "1.jpeg")
    (d / "2.jpeg").write_bytes((d / "1.jpeg").read_bytes())  # same bytes, different id
    _img(d / "01.png")  # same id T001 as 1.jpeg
    calls = []
    recs = ev.process_folder(d, lambda b: calls.append(1) or pipe.check(b), "r", {})
    by = {r.filename: r for r in recs}
    assert by["2.jpeg"].duplicate_of == "T001" and by["2.jpeg"].actual_outcome != ev.OUT_DUPLICATE_ID
    dup = [r for r in recs if r.actual_outcome == ev.OUT_DUPLICATE_ID]
    assert len(dup) == 1 and len(calls) == 2


def test_no_ground_truth_means_pending_never_correct(photos, pipe):
    recs = ev.process_folder(photos, pipe.check, "r", {})
    assert {r.expected_outcome for r in recs} == {ev.PENDING}
    assert {r.evaluation_status for r in recs} == {ev.STATUS_PENDING}


def test_scoring_keeps_actual_expected_and_status_separate():
    s = ev.score
    assert s("Unable to verify", ev.PENDING)[0] == ev.STATUS_PENDING
    assert s("Alert found", "Alert found", "4", "4")[0] == ev.STATUS_CORRECT
    assert s("Alert found", "Alert found", "150", "4")[0] == ev.STATUS_INCORRECT  # wrong record
    assert s("Alert found", "No alert found")[0] == ev.STATUS_INCORRECT
    assert s("Unable to verify", "Alert found")[0] == ev.STATUS_INCORRECT  # abstention = miss
    assert s("Unable to verify", "Unable to verify")[0] == ev.STATUS_CORRECT
    assert s(ev.OUT_REJECTED, "Alert found")[0] == ev.STATUS_INCONCLUSIVE
    assert s(ev.OUT_SYSTEM, "No alert found")[0] == ev.STATUS_INCONCLUSIVE


def test_ground_truth_roundtrip_validation_and_no_clobbering(tmp_path):
    f = tmp_path / "gt.csv"
    gt = ev.ensure_ground_truth(f, ["T001", "T002"])
    assert {g["expected_outcome"] for g in gt.values()} == {ev.PENDING}
    ev.set_ground_truth(f, "T001", "Alert found", verified_by="pack + official list", serial="4", batch="X1")
    ev.ensure_ground_truth(f, ["T001", "T002", "T003"])  # later run must keep the label
    gt = ev.load_ground_truth(f)
    assert gt["T001"]["expected_outcome"] == "Alert found" and gt["T003"]["expected_outcome"] == ev.PENDING
    with pytest.raises(ValueError):
        ev.set_ground_truth(f, "T002", "No alert found", verified_by="")  # provenance mandatory
    with pytest.raises(ValueError):
        ev.set_ground_truth(f, "T002", "Alert found", verified_by="me")  # needs serial/batch
    with pytest.raises(ValueError):
        ev.set_ground_truth(f, "T002", "Safe", verified_by="me")
    f.write_text("test_id,expected_outcome\nT009,Maybe\n")
    with pytest.raises(ValueError):
        ev.load_ground_truth(f)


def test_cli_end_to_end_history_report_and_rescore(photos, tmp_path, capsys):
    results, gtf = tmp_path / "results", tmp_path / "gt.csv"
    before = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in photos.iterdir()}
    args = ["--photos", str(photos), "--results", str(results), "--ground-truth", str(gtf)]
    assert run_evaluation.main(args) == 0
    assert run_evaluation.main(args) == 0  # second run must not overwrite the first
    runs = sorted(p.name for p in (results / "runs").iterdir())
    assert len(runs) == 2 and runs[0] != runs[1]
    for name in ("evaluation_results.csv", "evaluation_report.md"):
        assert (results / name).exists()
    rows = list(csv.DictReader((results / "evaluation_results.csv").open(encoding="utf-8-sig")))
    assert [r["test_id"] for r in rows] == ["T001", "T002", "T010"]
    assert {r["evaluation_status"] for r in rows} == {"Pending"}
    report = (results / "evaluation_report.md").read_text(encoding="utf-8")
    assert "no accuracy statement can be made" in report
    info = json.loads((results / "runs" / runs[-1] / "run_info.json").read_text())
    assert info["originals_unchanged"] is True and len(info["dataset_sha256"]) == 64
    assert before == {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in photos.iterdir()}

    # label one image, rescore the older run: a NEW run appears, the old one is untouched
    old_csv = (results / "runs" / runs[0] / "evaluation_results.csv").read_bytes()
    assert set_ground_truth.main(["T001", "Unable to verify", "--verified-by", "test", "--file", str(gtf)]) == 0
    assert set_ground_truth.main(["T002", "Alert found", "--file", str(gtf)]) == 1  # no provenance -> refused
    assert run_evaluation.main(args[:4] + ["--ground-truth", str(gtf), "--rescore", runs[0]]) == 0
    assert (results / "runs" / runs[0] / "evaluation_results.csv").read_bytes() == old_csv
    assert len(list((results / "runs").iterdir())) == 3
    latest = {r["test_id"]: r for r in csv.DictReader((results / "evaluation_results.csv").open(encoding="utf-8-sig"))}
    assert latest["T001"]["expected_outcome"] == "Unable to verify" and latest["T001"]["evaluation_status"] == "Correct"
    assert latest["T002"]["evaluation_status"] == "Pending"


def test_run_ids_never_collide(tmp_path):
    now = datetime(2026, 1, 2, 3, 4, 5)
    a = ev.new_run_id(tmp_path, now)
    (tmp_path / "runs" / a).mkdir(parents=True)
    assert ev.new_run_id(tmp_path, now) != a


def _ocr_ok():
    try:
        find_engine()
        return font_path() is not None
    except OCREngineUnavailable:
        return False


@pytest.mark.skipif(not _ocr_ok(), reason="needs Tesseract and a TrueType font")
def test_records_reflect_the_real_pipeline_not_a_second_algorithm(tmp_path, pipe):
    ds = pipe.dataset.records[3]  # serial 4, used by the README demo
    lines = [ds.product_name, f"B.No.: {ds.batch_number}", "Mfg: 01/2025   Exp: 12/2026"]
    (tmp_path / "1.png").write_bytes(encode(render_label(lines), "PNG"))
    [rec] = ev.process_folder(tmp_path, pipe.check, "r", {})
    direct = pipe.check((tmp_path / "1.png").read_bytes())
    assert rec.actual_outcome == direct.decision.headline
    assert rec.batch_raw == (direct.extraction.batch.raw or "")
    assert rec.ocr_passes and rec.ocr_engine
    if rec.actual_outcome == "Alert found":
        assert rec.matched_serial == "4" and rec.matched_dataset_product
    assert "Expired" != rec.actual_outcome  # expiry stays disabled
