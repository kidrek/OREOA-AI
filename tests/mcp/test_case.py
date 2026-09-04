"""T3: mcp-case contract (gate, citation verification, narrow detection status)."""

from __future__ import annotations

import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from conftest import CASE_ID, call_tool, record_id, rid_for  # noqa: E402

EXPECTED_TOOLS = {
    "read_case",
    "read_journal",
    "read_state",
    "upsert_hypothesis",
    "upsert_finding",
    "record_gap",
    "mark_detections_reviewed",
}


def _tool_names(server) -> set[str]:
    import asyncio

    return {t.name for t in asyncio.run(server.list_tools())}


def test_case_tool_set(case_server):
    assert _tool_names(case_server) == EXPECTED_TOOLS


def test_reads(case_dir, case_server):
    is_error, text, payload = call_tool(case_server, "read_case", {"case_id": CASE_ID})
    assert not is_error
    assert payload["case"]["id"] == CASE_ID

    is_error, text, payload = call_tool(
        case_server, "read_journal", {"case_id": CASE_ID, "tail": 5}
    )
    assert not is_error and payload["lines"]

    is_error, text, payload = call_tool(case_server, "read_state", {"case_id": CASE_ID})
    assert not is_error and payload == {}


def test_mutation_requires_gate(case_dir, case_server):
    hypothesis = {"id": "H1", "statement": "phishing vector", "confidence": "low"}
    is_error, text, _ = call_tool(
        case_server,
        "upsert_hypothesis",
        {"case_id": CASE_ID, "hypothesis": hypothesis, "confirmed_by_analyst": False},
    )
    assert is_error
    assert "confirmed_by_analyst" in text

    is_error, text, _ = call_tool(
        case_server,
        "mark_detections_reviewed",
        {"case_id": CASE_ID, "record_ids": [rid_for(1000)], "confirmed_by_analyst": False},
    )
    assert is_error and "confirmed_by_analyst" in text

    # nothing written
    data = yaml.safe_load((case_dir / "case.yaml").read_text(encoding="utf-8"))
    assert data["hypotheses"] == []


def test_upsert_hypothesis_gated_ok(case_dir, case_server):
    hypothesis = {
        "id": "H1",
        "statement": "initial access via phishing",
        "confidence": "medium",
        "dfiq_questions": ["Q1001"],
    }
    is_error, text, payload = call_tool(
        case_server,
        "upsert_hypothesis",
        {"case_id": CASE_ID, "hypothesis": hypothesis, "confirmed_by_analyst": True},
    )
    assert not is_error, text
    data = yaml.safe_load((case_dir / "case.yaml").read_text(encoding="utf-8"))
    assert data["hypotheses"][0]["id"] == "H1"
    journal = (case_dir / "journal.md").read_text(encoding="utf-8")
    assert "[mcp-case]" in journal and "H1" in journal


def test_upsert_finding_citation_verification(case_dir, case_server):
    # unresolved citation -> refused + hallucination event journaled
    bad = {
        "id": "F1",
        "description": "fictitious record",
        "record_ids": [record_id("EV-001", "custom:test", "ghost")],
    }
    is_error, text, _ = call_tool(
        case_server,
        "upsert_finding",
        {"case_id": CASE_ID, "finding": bad, "confirmed_by_analyst": True},
    )
    assert is_error and "unresolved" in text
    journal = (case_dir / "journal.md").read_text(encoding="utf-8")
    assert "hallucination" in journal

    # resolved citation -> written
    good = {
        "id": "F1",
        "description": "suspicious powershell",
        "record_ids": [rid_for(2), rid_for(1000)],
    }
    is_error, text, payload = call_tool(
        case_server,
        "upsert_finding",
        {"case_id": CASE_ID, "finding": good, "confirmed_by_analyst": True},
    )
    assert not is_error, text
    data = yaml.safe_load((case_dir / "case.yaml").read_text(encoding="utf-8"))
    assert data["findings"][0]["id"] == "F1"
    assert len(data["findings"][0]["record_ids"]) == 2


def test_record_gap(case_dir, case_server):
    gap = {"host": "WKS-01", "artifact": "WindowsEventLogSecurity", "reason": "not collected"}
    is_error, text, payload = call_tool(
        case_server, "record_gap", {"case_id": CASE_ID, "gap": gap, "confirmed_by_analyst": True}
    )
    assert not is_error, text
    data = yaml.safe_load((case_dir / "case.yaml").read_text(encoding="utf-8"))
    assert data["gaps"][0]["artifact"] == "WindowsEventLogSecurity"


def test_mark_detections_reviewed_narrow_transition(case_dir, case_server):
    d1, d2, d3 = rid_for(1000), rid_for(1001), rid_for(1002)
    is_error, text, payload = call_tool(
        case_server,
        "mark_detections_reviewed",
        {"case_id": CASE_ID, "record_ids": [d1, d2], "confirmed_by_analyst": True},
    )
    assert not is_error, text
    assert payload["reviewed"] == 2

    # second pass on an already-reviewed id -> refused (only new -> reviewed)
    is_error, text, _ = call_tool(
        case_server,
        "mark_detections_reviewed",
        {"case_id": CASE_ID, "record_ids": [d1], "confirmed_by_analyst": True},
    )
    assert is_error and "only new -> reviewed" in text

    # unknown id -> unresolved citation refusal + journal
    is_error, text, _ = call_tool(
        case_server,
        "mark_detections_reviewed",
        {"case_id": CASE_ID, "record_ids": [d3, "ghost"], "confirmed_by_analyst": True},
    )
    assert is_error and "unresolved" in text

    # d3 untouched (still new) - the failed transaction did not write
    is_error, text, payload = call_tool(
        case_server,
        "mark_detections_reviewed",
        {"case_id": CASE_ID, "record_ids": [d3], "confirmed_by_analyst": True},
    )
    assert not is_error, text
