"""T3: mcp-knowledge contract (sandbox, read, snapshot, DFIQ loader)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from conftest import call_tool  # noqa: E402

EXPECTED_TOOLS = {"knowledge_list", "knowledge_read", "snapshot", "dfiq_list", "dfiq_get"}


def _tool_names(server) -> set[str]:
    import asyncio

    return {t.name for t in asyncio.run(server.list_tools())}


def test_knowledge_tool_set(knowledge_server):
    assert _tool_names(knowledge_server) == EXPECTED_TOOLS


@pytest.fixture()
def dfiq_tree(case_dir, knowledge_server, tmp_path):
    """Minimal official + internal DFIQ trees under the knowledge root
    (format v1.1.0: name + uuid + internal)."""
    from oreoa import dfiq_loader

    root = tmp_path / "knowledge"
    files = {
        "upstream/dfiq/dfiq/data/questions/Q1001.yaml": (
            "name: What files were downloaded using a web browser?\n"
            "type: question\n"
            "description: Official fixture.\n"
            "uuid: 1f0a9c4e-1111-4a1b-8c2d-000000000003\n"
            "id: Q1001\n"
            "dfiq_version: 1.1.0\n"
            "tags: []\n"
            "parent_ids:\n  - F1001\n"
        ),
        "custom/dfiq/scenarios/S0001.yaml": (
            "name: Host Compromise Assessment\n"
            "type: scenario\n"
            "description: Internal fixture.\n"
            "uuid: 2f0a9c4e-2222-4a1b-8c2d-000000000001\n"
            "id: S0001\n"
            "dfiq_version: 1.1.0\n"
            "internal: true\n"
            "tags:\n  - oreoa-internal\n"
        ),
        "custom/dfiq/facets/F0001.yaml": (
            "name: Initial Access\n"
            "type: facet\n"
            "description: Internal fixture.\n"
            "uuid: 2f0a9c4e-2222-4a1b-8c2d-000000000002\n"
            "id: F0001\n"
            "dfiq_version: 1.1.0\n"
            "internal: true\n"
            "tags:\n  - oreoa-internal\n"
            "parent_ids:\n  - S0001\n"
        ),
        "custom/dfiq/questions/Q0001.yaml": (
            "name: Office document opened followed by suspicious child process\n"
            "type: question\n"
            "description: Internal fixture.\n"
            "uuid: 2f0a9c4e-2222-4a1b-8c2d-000000000003\n"
            "id: Q0001\n"
            "dfiq_version: 1.1.0\n"
            "internal: true\n"
            "tags:\n  - oreoa-internal\n  - area:IA\n"
            "parent_ids:\n  - F0001\n"
        ),
    }
    for rel, content in files.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    dfiq_loader.INDEX_CACHE.clear()
    yield root
    dfiq_loader.INDEX_CACHE.clear()


def test_dfiq_list_official_and_internal(dfiq_tree, knowledge_server):
    is_error, text, payload = call_tool(knowledge_server, "dfiq_list", {})
    assert not is_error
    assert payload["count"] == 2
    ids = {c["id"]: c for c in payload["components"]}
    assert ids["Q0001"]["is_internal"] is True
    assert ids["Q1001"]["is_internal"] is False
    assert payload["sources"]["official_snapshot"]["available"] is True

    is_error, text, payload = call_tool(knowledge_server, "dfiq_list", {"internal": True})
    assert not is_error
    assert [c["id"] for c in payload["components"]] == ["Q0001"]

    is_error, text, payload = call_tool(
        knowledge_server, "dfiq_list", {"component_type": "facet", "internal": True}
    )
    assert not is_error
    assert [c["id"] for c in payload["components"]] == ["F0001"]


def test_dfiq_get_internal_question_with_hunts(dfiq_tree, knowledge_server):
    is_error, text, payload = call_tool(knowledge_server, "dfiq_get", {"dfiq_id": "Q0001"})
    assert not is_error
    assert payload["is_internal"] is True
    assert payload["source"] == "internal"
    assert [p["id"] for p in payload["parents"]] == ["F0001"]
    # hunts come from the real seed mounted via OREOA_HUNTS_CATALOG fallback
    assert isinstance(payload["hunts"], list)


def test_dfiq_get_unknown_refusal(dfiq_tree, knowledge_server):
    is_error, text, _ = call_tool(knowledge_server, "dfiq_get", {"dfiq_id": "Q9999"})
    assert is_error
    assert "unknown DFIQ id" in text


def test_dfiq_missing_official_snapshot_note(case_dir, knowledge_server, tmp_path):
    """Without the official snapshot the tools still serve internal objects
    and report the missing snapshot explicitly (gap, not a crash)."""
    from oreoa import dfiq_loader

    dfiq_loader.INDEX_CACHE.clear()
    is_error, text, payload = call_tool(knowledge_server, "dfiq_list", {})
    assert not is_error
    assert payload["sources"]["official_snapshot"]["available"] is False
    assert "update-knowledge" in payload["sources"]["official_snapshot"]["note"]
    dfiq_loader.INDEX_CACHE.clear()


def test_knowledge_sandbox(case_dir, knowledge_server):
    for bad in ("../outside", "/etc/passwd", "custom/../../secrets"):
        is_error, text, _ = call_tool(
            knowledge_server, "knowledge_read", {"path": bad}
        )
        assert is_error, bad
        assert "escapes" in text


def test_knowledge_list_and_read(case_dir, knowledge_server, tmp_path):
    import os

    root = tmp_path / "knowledge"
    (root / "custom").mkdir(parents=True)
    (root / "custom" / "note.md").write_text("knowlege note content")
    is_error, text, payload = call_tool(knowledge_server, "knowledge_list", {"path": "custom"})
    assert not is_error
    assert payload["entries"][0]["name"] == "note.md"

    is_error, text, payload = call_tool(
        knowledge_server, "knowledge_read", {"path": "custom/note.md"}
    )
    assert not is_error
    assert "knowlege note content" in payload["content"]


def test_snapshot_missing_refusal(case_dir, knowledge_server):
    is_error, text, _ = call_tool(knowledge_server, "snapshot", {})
    assert is_error
    assert "update-knowledge" in text


def test_snapshot_present(case_dir, knowledge_server, tmp_path):
    import json

    root = tmp_path / "knowledge"
    root.mkdir(exist_ok=True)
    (root / "snapshot.json").write_text(json.dumps({"dfiq": "f07e5f2a", "attack": "v19.2"}))
    is_error, text, payload = call_tool(knowledge_server, "snapshot", {})
    assert not is_error
    assert payload["dfiq"] == "f07e5f2a"
