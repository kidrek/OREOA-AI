"""T3: mcp-jobs contract (payload validation before enqueue, case scoping).

The Redis round trip (enqueue/status/cancel/wait against the real ACL) is
covered by the T5 pipeline smoke; here only the validation semantics and the
registry-key scoping are asserted (T3 runs without containers).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from oreoa import mcp_server  # noqa: E402
from oreoa.jobs_model import JobType  # noqa: E402

EXPECTED_TOOLS = {"enqueue", "extract", "unlock", "fetch_symbol", "status", "cancel", "wait"}


def test_jobs_tool_set(jobs_server):
    import asyncio

    names = {t.name for t in asyncio.run(jobs_server.list_tools())}
    assert names == EXPECTED_TOOLS


def test_prepare_envelope_defaults_and_freezes():
    envelope = mcp_server.prepare_envelope("2026-09-INC-420", "hash", "EV-001", {}, None)
    assert envelope["queue"] == "fast"
    assert envelope["case_id"] == "2026-09-INC-420"

    envelope = mcp_server.prepare_envelope("2026-09-INC-420", "plaso", "EV-001", {}, None)
    assert envelope["queue"] == "deep"

    envelope = mcp_server.prepare_envelope(
        "2026-09-INC-420", "extract_unitary", "EV-001", {"paths": ["extracted/x"]}, None
    )
    assert envelope["queue"] == "deep"


def test_prepare_envelope_refuses_wrong_queue():
    with pytest.raises(Exception) as exc:
        mcp_server.prepare_envelope("2026-09-INC-420", "hash", "EV-001", {}, "deep")
    assert "refused" in str(exc.value)


def test_prepare_envelope_refuses_unknown_job_type():
    with pytest.raises(Exception) as exc:
        mcp_server.prepare_envelope("2026-09-INC-420", "quantum_scan", "EV-001", {}, None)
    assert "refused" in str(exc.value)


def test_extract_payload_path_outside_case_refused():
    with pytest.raises(Exception) as exc:
        mcp_server.prepare_envelope(
            "2026-09-INC-420", "extract_unitary", "EV-001", {"paths": ["../../etc/passwd"]}, None
        )
    assert "refused" in str(exc.value)


def test_fetch_symbol_gate_enforced():
    with pytest.raises(Exception) as exc:
        mcp_server.prepare_envelope(
            "2026-09-INC-420",
            "fetch_symbol",
            "EV-001",
            {"pdb_name": "ntkrnlmp.pdb", "guid": "9F4AF6D93A0F4B10B0D0E4B10B0D0E41280000",
             "confirmed_by_analyst": False},
            None,
        )
    assert "refused" in str(exc.value)

    envelope = mcp_server.prepare_envelope(
        "2026-09-INC-420",
        "fetch_symbol",
        "EV-001",
        {"pdb_name": "ntkrnlmp.pdb", "guid": "9F4AF6D93A0F4B10B0D0E4B10B0D0E41280000",
         "confirmed_by_analyst": True},
        None,
    )
    assert envelope["queue"] == "fetch"


def test_registry_key_scopes_by_case():
    assert mcp_server.jobs_registry_key("2026-09-INC-420") == "oreoa:jobs:2026-09-INC-420"
    with pytest.raises(Exception):
        mcp_server.jobs_registry_key("../inject")
    with pytest.raises(Exception):
        mcp_server.jobs_registry_key("")


def test_every_job_type_has_a_queue_and_a_timeout():
    from oreoa.worker import DEFAULT_STEP_TIMEOUTS

    typed_payloads = {
        "extract": {"artifacts": ["WindowsPrefetchFiles"]},
        "extract_unitary": {"paths": ["extracted/x"]},
        "fetch_symbol": {
            "pdb_name": "ntkrnlmp.pdb",
            "guid": "9F4AF6D93A0F4B10B0D0E4B10B0D0E41280000",
            "confirmed_by_analyst": True,
        },
        "unlock": {},
    }
    for job_type in JobType.__args__:
        envelope = mcp_server.prepare_envelope(
            "2026-09-INC-420", job_type, "EV-001", typed_payloads.get(job_type, {}), None
        )
        assert envelope["queue"] in ("fast", "deep", "fetch")
        assert job_type in DEFAULT_STEP_TIMEOUTS
