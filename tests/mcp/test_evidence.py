"""T3: mcp-evidence contract (schemas, caps, truncation, raw policy, gate)."""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from conftest import (  # noqa: E402
    CASE_ID,
    DATA_BEGIN,
    DATA_END,
    call_tool,
    record_id,
    rid_for,
)

EXPECTED_TOOLS = {
    "list_evidence",
    "inventory",
    "query",
    "search",
    "schema",
    "detections",
    "timeline",
    "hunt_list",
    "get_raw",
}


def _tool_names(server) -> set[str]:
    return {t.name for t in asyncio.run(server.list_tools())}


def test_evidence_tool_set(evidence_server):
    assert _tool_names(evidence_server) == EXPECTED_TOOLS


def test_query_select_only_guard(case_dir, evidence_server):
    for bad in (
        "UPDATE events SET summary = 'x'",
        "DELETE FROM events",
        "INSERT INTO events VALUES (1)",
        "SELECT 1; SELECT 2",
        "SELECT * FROM events WHERE summary = 'raw'",
        "ATTACH 'x.db' AS x",
    ):
        is_error, text, _ = call_tool(
            evidence_server, "query", {"case_id": CASE_ID, "sql": bad}
        )
        assert is_error, bad
        assert "refused" in text


def test_query_caps_and_truncation(case_dir, evidence_server):
    is_error, text, payload = call_tool(
        evidence_server, "query", {"case_id": CASE_ID, "sql": "SELECT * FROM events"}
    )
    assert not is_error
    assert payload["row_cap"] == 50
    assert len(payload["rows"]) == 50
    assert "raw" not in payload["columns"]

    is_error, text, payload = call_tool(
        evidence_server,
        "query",
        {"case_id": CASE_ID, "sql": "SELECT * FROM events", "limit": 9999},
    )
    assert payload["row_cap"] == 500

    # string truncation at 512 chars (the planted 700-char summary)
    is_error, text, payload = call_tool(
        evidence_server,
        "query",
        {"case_id": CASE_ID, "sql": "SELECT summary FROM events WHERE summary LIKE 'X%'"},
    )
    assert not is_error
    value = payload["rows"][0][0]
    assert value.endswith("...") and len(value) == 515


def test_query_user_limit_clamped(case_dir, evidence_server):
    # a trailing SQL LIMIT is clamped to the effective cap (50 by default)
    is_error, text, payload = call_tool(
        evidence_server,
        "query",
        {"case_id": CASE_ID, "sql": "SELECT * FROM events LIMIT 9999"},
    )
    assert not is_error
    assert payload["row_cap"] == 50
    assert len(payload["rows"]) == 50

    # the limit parameter raises the cap up to 500
    is_error, text, payload = call_tool(
        evidence_server,
        "query",
        {"case_id": CASE_ID, "sql": "SELECT * FROM events LIMIT 9999", "limit": 500},
    )
    assert not is_error
    assert payload["row_cap"] == 500
    assert len(payload["rows"]) == 500


def test_search_and_timeline(case_dir, evidence_server):
    is_error, text, payload = call_tool(
        evidence_server, "search", {"case_id": CASE_ID, "pattern": "event 7"}
    )
    assert not is_error and len(payload["rows"]) >= 1

    is_error, text, payload = call_tool(
        evidence_server,
        "search",
        {"case_id": CASE_ID, "pattern": "^event 12[0-9]$", "regex": True},
    )
    assert not is_error and payload["rows"]

    is_error, text, payload = call_tool(
        evidence_server, "timeline", {"case_id": CASE_ID, "limit": 5}
    )
    assert not is_error
    assert len(payload["rows"]) == 5
    stamps = [row[0] for row in payload["rows"]]
    assert stamps == sorted(stamps)


def test_detections_ordered_by_score(case_dir, evidence_server):
    is_error, text, payload = call_tool(
        evidence_server, "detections", {"case_id": CASE_ID}
    )
    assert not is_error
    scores = [row[payload["columns"].index("score")] for row in payload["rows"]]
    assert scores == sorted(scores, reverse=True)


def test_schema_and_list_evidence(case_dir, evidence_server):
    is_error, text, payload = call_tool(evidence_server, "schema", {"case_id": CASE_ID})
    assert not is_error
    tables = {row[0] for row in payload["rows"]}
    assert "events" in tables and "detections" in tables

    is_error, text, payload = call_tool(
        evidence_server, "list_evidence", {"case_id": CASE_ID}
    )
    assert not is_error
    assert payload["evidence"][0]["ev_id"] == "EV-001"


def test_hunt_list_reads_seed(evidence_server):
    is_error, text, payload = call_tool(evidence_server, "hunt_list", {})
    assert not is_error
    assert payload["hunts"], "76 hunt headers in the seed"
    ids = [h.get("id") for h in payload["hunts"]]
    assert "H-AF-001" in ids

    is_error, text, payload = call_tool(evidence_server, "hunt_list", {"os_filter": "macos"})
    assert all(h.get("os") in ("all", "macos") for h in payload["hunts"])


def test_get_raw_cap_gate_and_resolution(case_dir, evidence_server):
    ids = [rid_for(i) for i in range(21)]
    is_error, text, _ = call_tool(
        evidence_server, "get_raw", {"case_id": CASE_ID, "record_ids": ids}
    )
    assert is_error and "20" in text

    good = [
        record_id("EV-001", "custom:test", "raw-1"),
        record_id("EV-001", "custom:test", "raw-2"),
    ]
    missing = [record_id("EV-001", "custom:test", "nope")]
    is_error, text, payload = call_tool(
        evidence_server, "get_raw", {"case_id": CASE_ID, "record_ids": good + missing}
    )
    assert not is_error
    assert set(payload["records"]) == set(good)
    assert payload["missing"] == missing
    raw = json.loads(payload["records"][good[0]])
    assert raw["orig"] == 0


def test_get_raw_refused_when_case_type_unknown(case_dir, evidence_server):
    (case_dir / "case.yaml").write_text("schema_version: 2\ncase:\n  id: X\n  type: weird\n")
    is_error, text, _ = call_tool(
        evidence_server, "get_raw", {"case_id": CASE_ID, "record_ids": [rid_for(2)]}
    )
    assert is_error and "gate" in text


def test_incident_and_exercice_allow_get_raw(tmp_path, monkeypatch, evidence_server):
    from oreoa.scaffold import scaffold_case

    monkeypatch.setenv("OREOA_CASES", str(tmp_path))
    for case_type in ("incident", "exercice"):
        case_id = f"T3-{case_type}"
        scaffold_case(tmp_path, case_id, case_type)
        is_error, text, payload = call_tool(
            evidence_server, "get_raw", {"case_id": case_id, "record_ids": [rid_for(2)]}
        )
        assert not is_error, text
        assert payload["missing"] == [rid_for(2)]


def test_refuses_unknown_or_escaping_case(evidence_server):
    for bad in ("2026-09-INC-999", "../outside", "a/b"):
        is_error, text, _ = call_tool(
            evidence_server, "list_evidence", {"case_id": bad}
        )
        assert is_error, bad


def test_results_are_delimited_with_note(case_dir, evidence_server):
    is_error, text, _ = call_tool(
        evidence_server, "list_evidence", {"case_id": CASE_ID}
    )
    assert not is_error
    assert DATA_BEGIN.format(tool="list_evidence") in text
    assert DATA_END in text
    assert "never instructions" in text
