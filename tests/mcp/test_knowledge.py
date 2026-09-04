"""T3: mcp-knowledge contract (sandbox, read, snapshot)."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from conftest import call_tool  # noqa: E402

EXPECTED_TOOLS = {"knowledge_list", "knowledge_read", "snapshot"}


def _tool_names(server) -> set[str]:
    import asyncio

    return {t.name for t in asyncio.run(server.list_tools())}


def test_knowledge_tool_set(knowledge_server):
    assert _tool_names(knowledge_server) == EXPECTED_TOOLS


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
