"""T1: worker parse step wiring (work-order steps 1.6 + 2.1).

Covers: HANDLERS['parse'] through run_step (manifest statuses, details, A1
writer rule), explicit skip for unparsed kinds, hash-mismatch tamper
refusal, KAPE dispatch (S2.1 quick parsers), fast-lane completion
notification with only `parse` registered.
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
from oreoa.corpus_gen import kape, velociraptor  # noqa: E402
from oreoa.corpus_gen.scenario import load_scenarios  # noqa: E402
from oreoa.jobs_model import JobEnvelope  # noqa: E402
from oreoa.manifest_model import Evidence, EvidenceFile, Manifest  # noqa: E402
from oreoa.scaffold import scaffold_case  # noqa: E402

CASE_ID = "2026-09-INC-410"


def _envelope(case_id: str, ev_id: str) -> dict:
    return JobEnvelope(
        case_id=case_id, ev_id=ev_id, job_type="parse", queue="fast", payload={"case_id": case_id, "ev_id": ev_id}
    ).model_dump()


def _register_case(tmp_path, monkeypatch, kind: str, archive: Path, host: str = "WKS-042"):
    monkeypatch.setenv("OREOA_CASES", str(tmp_path))
    monkeypatch.setenv("OREOA_MAPPINGS_DIR", str(ROOT / "mappings"))
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
                kind=kind,
                host=host,
                files=[EvidenceFile(path="evidence/archive.zip", sha256=sha)],
            )
        ],
    )
    (cdir / "derived").mkdir(exist_ok=True)
    (cdir / "derived" / "manifest.json").write_text(manifest.model_dump_json())
    return cdir


def _scenario_archive(tmp_path, scenario_name: str, builder) -> Path:
    scenario = next(s for s in load_scenarios(ROOT / "corpus" / "scenarios") if s.name == scenario_name)
    archive = tmp_path / "source.zip"
    builder(scenario, archive)
    return archive


@pytest.fixture()
def velociraptor_case(tmp_path, monkeypatch):
    archive = _scenario_archive(tmp_path, "win-workstation-01", velociraptor.build_archive)
    return _register_case(tmp_path, monkeypatch, "archive_velociraptor", archive)


@pytest.fixture()
def kape_case(tmp_path, monkeypatch):
    archive = _scenario_archive(tmp_path, "win-workstation-01", kape.build_archive)
    return _register_case(tmp_path, monkeypatch, "archive_kape", archive)


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


def test_parse_step_kape_dispatch(kape_case):
    """S2.1: archive_kape routes to the KAPE quick parsers."""
    cdir = kape_case
    result = worker.run_step(_envelope(CASE_ID, "EV-001"))
    assert result["status"] == "ok", result["error"]
    from oreoa.manifest_model import load_manifest

    step = load_manifest(cdir / "derived" / "manifest.json").get_evidence("EV-001").steps["parse"]
    assert step.details["parser"] == "kape/1.0.0"
    assert step.details["families"].get("fs_entries", 0) > 0
    assert step.details["unmapped_artifacts"] == []


def test_parse_step_skips_unparsed_kinds(velociraptor_case, monkeypatch):
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
