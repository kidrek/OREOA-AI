"""T1: worker parse step wiring (work-order step 1.6).

Covers: HANDLERS['parse'] through run_step (manifest statuses, details, A1
writer rule), explicit skip for non-Velociraptor kinds, hash-mismatch
tamper refusal, fast-lane completion notification with only `parse`
registered.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from oreoa import worker  # noqa: E402
from oreoa.corpus_gen import velociraptor  # noqa: E402
from oreoa.corpus_gen.scenario import load_scenarios  # noqa: E402
from oreoa.jobs_model import JobEnvelope  # noqa: E402
from oreoa.manifest_model import Evidence, EvidenceFile, Manifest  # noqa: E402
from oreoa.scaffold import scaffold_case  # noqa: E402

CASE_ID = "2026-09-INC-410"


def _envelope(case_id: str, ev_id: str) -> dict:
    return JobEnvelope(
        case_id=case_id, ev_id=ev_id, job_type="parse", queue="fast", payload={"case_id": case_id, "ev_id": ev_id}
    ).model_dump()


@pytest.fixture()
def velociraptor_case(tmp_path, monkeypatch):
    monkeypatch.setenv("OREOA_CASES", str(tmp_path))
    monkeypatch.setenv("OREOA_MAPPINGS_DIR", str(ROOT / "mappings"))
    scenario = next(s for s in load_scenarios(ROOT / "corpus" / "scenarios") if s.name == "win-workstation-01")
    archive = tmp_path / "source.zip"
    velociraptor.build_archive(scenario, archive)
    sha = hashlib.sha256(archive.read_bytes()).hexdigest()

    cdir = scaffold_case(tmp_path, CASE_ID, "incident")
    evidence_dir = cdir / "evidence"
    evidence_dir.chmod(0o755)
    (evidence_dir / "archive.zip").write_bytes(archive.read_bytes())
    evidence_dir.chmod(0o555)

    manifest = Manifest(
        case_id=CASE_ID,
        evidence=[
            Evidence(
                ev_id="EV-001",
                kind="archive_velociraptor",
                host="WKS-042",
                files=[EvidenceFile(path="evidence/archive.zip", sha256=sha)],
            )
        ],
    )
    (cdir / "derived").mkdir(exist_ok=True)
    (cdir / "derived" / "manifest.json").write_text(manifest.model_dump_json())
    return cdir


def test_parse_step_ok_and_details(velociraptor_case):
    cdir = velociraptor_case
    result = worker.run_step(_envelope(CASE_ID, "EV-001"))
    assert result["status"] == "ok"
    assert result["error"] == ""
    from oreoa.manifest_model import load_manifest

    manifest = load_manifest(cdir / "derived" / "manifest.json")
    step = manifest.get_evidence("EV-001").steps["parse"]
    assert step.status == "ok"
    assert step.details["rows"] > 0
    assert "families" in step.details


def test_parse_step_skips_non_velociraptor(velociraptor_case, monkeypatch):
    cdir = velociraptor_case
    from oreoa.manifest_model import load_manifest, save_manifest

    manifest = load_manifest(cdir / "derived" / "manifest.json")
    manifest.evidence.append(
        Evidence(
            ev_id="EV-002",
            kind="disk_image",
            host="WKS-042",
            container_format="raw",
            files=[EvidenceFile(path="evidence/disk.img", sha256="b" * 64)],
        )
    )
    save_manifest(cdir / "derived" / "manifest.json", manifest)

    result = worker.run_step(_envelope(CASE_ID, "EV-002"))
    assert result["status"] == "skipped"
    saved = load_manifest(cdir / "derived" / "manifest.json")
    step = saved.get_evidence("EV-002").steps["parse"]
    assert step.status == "skipped"
    assert "no parser" in step.details["note"]


def test_parse_step_fails_on_tampered_evidence(velociraptor_case):
    cdir = velociraptor_case
    evidence_dir = cdir / "evidence"
    evidence_dir.chmod(0o755)
    target = evidence_dir / "archive.zip"
    target.write_bytes(target.read_bytes() + b"tampered")
    evidence_dir.chmod(0o555)

    result = worker.run_step(_envelope(CASE_ID, "EV-001"))
    assert result["status"] == "failed"
    assert "sha256 mismatch" in result["error"]


def test_parse_step_fast_done_notification(velociraptor_case):
    cdir = velociraptor_case
    result = worker.run_step(_envelope(CASE_ID, "EV-001"))
    assert result["notifications"], "parse is the only registered fast step -> fast_done"
    phase = json.loads((cdir / "state" / "phase.json").read_text())
    assert phase["hosts"]["WKS-042"]["phase"] == "fast_done"
    journal = (cdir / "journal.md").read_text()
    assert "[pipeline]" in journal and "fast lane complete" in journal
