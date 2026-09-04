"""T1: derived/manifest.json Pydantic models (SPEC case layout + line 98)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from oreoa.manifest_model import (  # noqa: E402
    Evidence,
    Manifest,
    StepResult,
    load_manifest,
    parse_manifest,
    save_manifest,
)


def evidence_file(sha: str = "a" * 64) -> dict:
    return {"path": "EV-001/image.raw", "sha256": sha, "size_bytes": 1024}


def disk_evidence(**overrides) -> dict:
    data = {
        "ev_id": "EV-001",
        "kind": "disk_image",
        "host": "WKS-042",
        "files": [evidence_file()],
        "container_format": "raw",
        "steps": {"hash": {"status": "ok"}},
    }
    data.update(overrides)
    return data


def manifest_payload(**overrides) -> dict:
    data = {
        "schema_version": 1,
        "case_id": "2026-09-INC-042",
        "evidence": [disk_evidence()],
        "updated_at": "2026-09-04T12:00:00",
    }
    data.update(overrides)
    return data


def test_disk_evidence_validates():
    ev = Evidence.model_validate(disk_evidence())
    assert ev.sha256 == "a" * 64
    assert ev.unlock == "not_needed"
    assert ev.encryption == "none"


def test_disk_image_requires_container_format():
    with pytest.raises(Exception):
        Evidence.model_validate(disk_evidence(container_format=None))


def test_invalid_kind_rejected():
    with pytest.raises(Exception):
        Evidence.model_validate(disk_evidence(kind="archive_hydra"))


def test_invalid_ev_id_rejected():
    with pytest.raises(Exception):
        Evidence.model_validate(disk_evidence(ev_id="EV1"))


def test_protector_requires_encryption():
    with pytest.raises(Exception):
        Evidence.model_validate(disk_evidence(protector="recovery_key"))


def test_encrypted_state_consistent():
    ev = Evidence.model_validate(
        disk_evidence(
            encryption="bitlocker",
            protector="recovery_key",
            unlock="key_required",
            vss=[{"index": 0, "created_at": "2026-08-01T00:00:00", "size": 4096}],
        )
    )
    assert ev.unlock == "key_required"
    assert ev.vss[0].index == 0


def test_unlock_without_encryption_rejected():
    with pytest.raises(Exception):
        Evidence.model_validate(disk_evidence(unlock="unlocked"))


def test_symbols_present_requires_file():
    with pytest.raises(Exception):
        Evidence.model_validate(disk_evidence(symbols_status="present"))


def test_symbols_missing_requires_identifier():
    ev = Evidence.model_validate(
        disk_evidence(
            kind="memory_image",
            container_format=None,
            symbols_status="missing",
            symbols_identifier="ntkrnlmp.pdb/9F4AF6D93A0F4B10B0D0E4B10B0D0E41",
        )
    )
    assert ev.symbols_identifier.endswith("1")


def test_invalid_step_status_rejected():
    with pytest.raises(Exception):
        Evidence.model_validate(disk_evidence(steps={"hash": {"status": "done"}}))


def test_step_finish_before_start_rejected():
    with pytest.raises(Exception):
        StepResult.model_validate(
            {
                "status": "ok",
                "started_at": "2026-09-04T12:00:00",
                "finished_at": "2026-09-04T11:00:00",
            }
        )


def test_multi_file_evidence_has_no_single_sha256():
    ev = Evidence.model_validate(
        disk_evidence(files=[evidence_file(), evidence_file("b" * 64)])
    )
    with pytest.raises(ValueError):
        ev.sha256


def test_manifest_validates_and_resolves_evidence():
    manifest = Manifest.model_validate(manifest_payload())
    assert manifest.get_evidence("EV-001").kind == "disk_image"
    with pytest.raises(KeyError):
        manifest.get_evidence("EV-999")


def test_manifest_case_id_pattern_enforced():
    with pytest.raises(Exception):
        Manifest.model_validate(manifest_payload(case_id="bad id!"))


def test_manifest_json_round_trip(tmp_path: Path):
    manifest = Manifest.model_validate(manifest_payload())
    payload = manifest.model_dump_json(indent=2)
    parsed = parse_manifest(payload)
    assert parsed == manifest
    target = tmp_path / "derived" / "manifest.json"
    save_manifest(target, manifest)
    assert not list(tmp_path.rglob("manifest.json.tmp"))
    assert load_manifest(target) == manifest


def test_manifest_empty_evidence_list_ok():
    manifest = Manifest.model_validate(manifest_payload(evidence=[]))
    assert manifest.evidence == []
