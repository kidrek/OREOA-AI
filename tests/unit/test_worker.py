"""T1: RQ worker harness (work-order step 1.4).

Covers: envelope revalidation, step dispatch with placeholder handlers,
manifest step statuses, phase derivation + fast_done notification, evidence
read-only refusal, per-step timeout table coverage.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from oreoa import worker  # noqa: E402
from oreoa.jobs_model import FAST_STEPS  # noqa: E402
from oreoa.manifest_model import (  # noqa: E402
    Evidence,
    EvidenceFile,
    Manifest,
    load_manifest,
)
from oreoa.scaffold import scaffold_case  # noqa: E402

SHA = "a" * 64
CASE_ID = "2026-09-INC-410"


@pytest.fixture()
def case(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("OREOA_CASES", str(tmp_path))
    cdir = scaffold_case(tmp_path, CASE_ID, "incident")
    manifest = Manifest(
        case_id=CASE_ID,
        evidence=[
            Evidence(
                ev_id="EV-001",
                kind="directory",
                host="WKS-01",
                files=[EvidenceFile(path="evidence/ev1", sha256=SHA, size_bytes=10)],
            ),
            Evidence(
                ev_id="EV-002",
                kind="directory",
                host="WKS-01",
                files=[EvidenceFile(path="evidence/ev2", sha256=SHA, size_bytes=10)],
            ),
        ],
    )
    (cdir / "derived").mkdir(exist_ok=True)
    (cdir / "derived" / "manifest.json").write_text(manifest.model_dump_json(indent=2))
    # evidence/ must be read-only for the harness to run (T5 6)
    os.chmod(cdir / "evidence", 0o555)
    return cdir


def envelope(ev_id: str = "EV-001", job_type: str = "hash", case: str = CASE_ID) -> dict:
    payload: dict = {}
    if job_type in ("extract", "extract_unitary"):
        payload = {"artifacts": ["WindowsPrefetchFiles"]}
    return {
        "job_type": job_type,
        "queue": "fast",
        "case_id": case,
        "ev_id": ev_id,
        "payload": payload,
    }


def test_run_step_writes_manifest_and_phase(case: Path):
    result = worker.run_step(envelope())
    assert result["status"] == "ok"
    manifest = load_manifest(case / "derived" / "manifest.json")
    step = manifest.get_evidence("EV-001").steps["hash"]
    assert step.status == "ok"
    assert step.started_at is not None and step.finished_at is not None
    phase = json.loads((case / "state" / "phase.json").read_text())
    assert phase["hosts"]["WKS-01"]["phase"] == "dropped"  # EV-002 not done


def test_run_step_placeholder_details(case: Path):
    result = worker.run_step(envelope(job_type="parse"))
    assert result["status"] == "ok"
    manifest = load_manifest(case / "derived" / "manifest.json")
    details = manifest.get_evidence("EV-001").steps["parse"].details
    assert "step 2" in details["note"]


def test_run_step_revalidates_envelope(case: Path):
    bad = envelope()
    bad["queue"] = "deep"  # hash runs on fast
    with pytest.raises(Exception):
        worker.run_step(bad)


def test_run_step_refuses_unknown_evidence(case: Path):
    with pytest.raises(KeyError):
        worker.run_step(envelope(ev_id="EV-999"))


def test_run_step_refuses_writable_evidence(case: Path):
    os.chmod(case / "evidence", 0o755)
    try:
        with pytest.raises(PermissionError):
            worker.run_step(envelope())
    finally:
        os.chmod(case / "evidence", 0o555)


def test_fast_done_notification_and_phase(case: Path):
    for job_type in sorted(FAST_STEPS):
        worker.run_step(envelope(job_type=job_type))
    phase = json.loads((case / "state" / "phase.json").read_text())
    # EV-002 has no registered steps: not complete -> EV-001's host stays dropped
    assert phase["hosts"]["WKS-01"]["phase"] == "dropped"

    for job_type in sorted(FAST_STEPS):
        worker.run_step(envelope(ev_id="EV-002", job_type=job_type))
    phase = json.loads((case / "state" / "phase.json").read_text())
    assert phase["hosts"]["WKS-01"]["phase"] == "fast_done"

    journal = (case / "journal.md").read_text(encoding="utf-8")
    assert "[pipeline]" in journal and "fast lane complete" in journal
    # idempotent: re-running a step does not duplicate the notification
    worker.run_step(envelope(job_type="hash"))
    assert (case / "journal.md").read_text(encoding="utf-8").count(
        "fast lane complete"
    ) == 1


def test_failed_step_marks_manifest(case: Path, monkeypatch: pytest.MonkeyPatch):
    def boom(cdir, env):
        raise RuntimeError("parser exploded")

    monkeypatch.setitem(worker.HANDLERS, "hash", boom)
    result = worker.run_step(envelope())
    assert result["status"] == "failed"
    assert "parser exploded" in result["error"]
    manifest = load_manifest(case / "derived" / "manifest.json")
    step = manifest.get_evidence("EV-001").steps["hash"]
    assert step.status == "failed" and "parser exploded" in step.error
    # a failed fast step blocks fast_done
    phase = json.loads((case / "state" / "phase.json").read_text())
    assert phase["hosts"]["WKS-01"]["phase"] == "dropped"


def test_step_timeout_table_covers_all_types():
    from oreoa.jobs_model import JobType

    for job_type in JobType.__args__:
        assert job_type in worker.DEFAULT_STEP_TIMEOUTS
        assert worker.DEFAULT_STEP_TIMEOUTS[job_type] > 0


def test_step_timeout_pack_override(tmp_path: Path):
    packs = tmp_path / "packs"
    packs.mkdir()
    (packs / "pipeline.yaml").write_text("timeouts:\n  hash: 3600\n")
    assert worker.step_timeout("hash", packs_dir=packs) == 3600
    assert worker.step_timeout("plaso", packs_dir=packs) == 21600
    assert worker.step_timeout("hash") == 600


def test_case_dir_containment(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("OREOA_CASES", str(tmp_path))
    with pytest.raises(ValueError):
        worker.case_dir("..")
    with pytest.raises(ValueError):
        worker.case_dir("a/b")
    with pytest.raises(FileNotFoundError):
        worker.case_dir("2026-09-INC-411")


def test_fetch_lane_refused_by_fast_deep_workers():
    assert worker.main(["fetch"]) == 1
    assert worker.main([]) == 2
    assert worker.main(["ultra"]) == 2
