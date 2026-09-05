"""T1: Redis/RQ job payload models (SPEC pipeline + lines 111/168)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from oreoa.jobs_model import (  # noqa: E402
    KNOWN_KERNEL_PDBS,
    AddKeyPayload,
    ExtractPayload,
    FetchSymbolPayload,
    JobEnvelope,
    UnlockPayload,
    safe_case_relative_path,
    validate_payload,
)

GUID = "9F4AF6D93A0F4B10B0D0E4B10B0D0E41280000"


def fetch_payload(**overrides) -> dict:
    data = {
        "pdb_name": "ntkrnlmp.pdb",
        "guid": GUID,
        "confirmed_by_analyst": True,
    }
    data.update(overrides)
    return data


def test_known_kernel_pdbs_closed_set():
    assert "ntkrnlmp.pdb" in KNOWN_KERNEL_PDBS
    assert "ntkrpamp.pdb" in KNOWN_KERNEL_PDBS


def test_fetch_symbol_valid_payload():
    payload = FetchSymbolPayload.model_validate(fetch_payload())
    assert payload.pdb_name == "ntkrnlmp.pdb"
    assert payload.guid == GUID


def test_fetch_symbol_requires_analyst_confirmation():
    with pytest.raises(Exception):
        FetchSymbolPayload.model_validate(fetch_payload(confirmed_by_analyst=False))


def test_fetch_symbol_rejects_malformed_guid():
    with pytest.raises(Exception):
        FetchSymbolPayload.model_validate(fetch_payload(guid="nothex"))
    with pytest.raises(Exception):
        FetchSymbolPayload.model_validate(fetch_payload(guid=GUID.lower()))


def test_fetch_symbol_rejects_unknown_pdb():
    with pytest.raises(Exception):
        FetchSymbolPayload.model_validate(fetch_payload(pdb_name="explorer.pdb"))


def test_unlock_payload_carries_no_key_material():
    payload = UnlockPayload.model_validate({"ev_id": "EV-001"})
    assert payload.model_dump() == {"ev_id": "EV-001"}
    with pytest.raises(Exception):
        UnlockPayload.model_validate({"ev_id": "EV-1"})


def test_safe_case_relative_path_accepts_normal_paths():
    assert safe_case_relative_path("extracted/Users/x.exe") == "extracted/Users/x.exe"
    assert safe_case_relative_path("archive/dir\\file.txt") == "archive/dir\\file.txt"


def test_safe_case_relative_path_rejects_escape_attempts():
    for bad in (
        "",
        "/etc/passwd",
        "\\Windows\\System32",
        "..\\..\\secret",
        "a/../b",
        "C:\\temp\\x",
        "with\x00nul",
    ):
        with pytest.raises(ValueError):
            safe_case_relative_path(bad)


def test_extract_payload_validates_paths():
    payload = ExtractPayload.model_validate(
        {"ev_id": "EV-001", "paths": ["extracted/x.exe"], "artifacts": ["WindowsPrefetchFiles"]}
    )
    assert payload.paths == ["extracted/x.exe"]


def test_extract_payload_rejects_escape_paths():
    with pytest.raises(Exception):
        ExtractPayload.model_validate({"ev_id": "EV-001", "paths": ["../outside"]})


def test_extract_payload_requires_something():
    with pytest.raises(Exception):
        ExtractPayload.model_validate({"ev_id": "EV-001"})


def test_add_key_payload_key_types():
    assert AddKeyPayload.model_validate({"ev_id": "EV-001", "key_type": "recovery_key"})
    with pytest.raises(Exception):
        AddKeyPayload.model_validate({"ev_id": "EV-001", "key_type": "tpm_only"})


def test_job_envelope_validates_typed_payloads():
    envelope = JobEnvelope.model_validate(
        {
            "job_type": "fetch_symbol",
            "queue": "fetch",
            "case_id": "2026-09-INC-042",
            "payload": fetch_payload(),
        }
    )
    assert envelope.job_type == "fetch_symbol"
    envelope = JobEnvelope.model_validate(
        {
            "job_type": "unlock",
            "queue": "fast",
            "case_id": "2026-09-INC-042",
            "ev_id": "EV-001",
            "payload": {"ev_id": "EV-001"},
        }
    )
    assert envelope.queue == "fast"


def test_job_envelope_requires_case_id_and_refuses_traversal():
    with pytest.raises(Exception):
        JobEnvelope.model_validate({"job_type": "parse", "queue": "fast", "payload": {}})
    with pytest.raises(Exception):
        JobEnvelope.model_validate(
            {"job_type": "parse", "queue": "fast", "case_id": "..", "payload": {}}
        )
    with pytest.raises(Exception):
        JobEnvelope.model_validate(
            {"job_type": "parse", "queue": "fast", "case_id": "a/b", "payload": {}}
        )


def test_job_envelope_refuses_unconfirmed_mutation():
    with pytest.raises(Exception):
        JobEnvelope.model_validate(
            {
                "job_type": "fetch_symbol",
                "queue": "fetch",
                "case_id": "2026-09-INC-042",
                "payload": fetch_payload(confirmed_by_analyst=False),
            }
        )


def test_job_envelope_refuses_bad_queue_and_ev_id():
    with pytest.raises(Exception):
        JobEnvelope.model_validate(
            {"job_type": "parse", "queue": "ultra", "case_id": "c1", "payload": {}}
        )
    with pytest.raises(Exception):
        JobEnvelope.model_validate(
            {"job_type": "parse", "queue": "fast", "case_id": "c1", "ev_id": "EV1"}
        )


def test_queue_for_step_routing():
    from oreoa.jobs_model import DEEP_STEPS, FAST_STEPS, queue_for_step

    for step in FAST_STEPS:
        assert queue_for_step(step) == "fast"
    for step in DEEP_STEPS:
        assert queue_for_step(step) == "deep"
    assert queue_for_step("unlock") == "fast"
    assert queue_for_step("fetch_symbol") == "fetch"
    assert queue_for_step("parse") != queue_for_step("plaso")


def test_validate_payload_passthrough_and_typed():
    assert validate_payload("parse", {"step": "parse"}) == {"step": "parse"}
    typed = validate_payload("unlock", {"ev_id": "EV-001"})
    assert isinstance(typed, UnlockPayload)
    with pytest.raises(Exception):
        validate_payload("extract", {"ev_id": "EV-001", "paths": [".."]})
