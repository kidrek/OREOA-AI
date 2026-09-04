"""T1: runtime-config generator - completeness and determinism."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from oreoa.runtime_config import ROLES, render  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]

ENV = {
    "LLM_BASE_URL": "http://host.docker.internal:1234/v1",
    "LLM_MODEL_ANALYST": "analyst-x",
    "LLM_MODEL_TRIAGE": "triage-x",
    "LLM_MODEL_REVIEWER": "reviewer-x",
}


def test_render_is_deterministic(tmp_path: Path):
    out1, out2 = tmp_path / "a", tmp_path / "b"
    render(out1, env=ENV)
    render(out2, env=ENV)
    files1 = {p.relative_to(out1): p.read_bytes() for p in out1.rglob("*") if p.is_file()}
    files2 = {p.relative_to(out2): p.read_bytes() for p in out2.rglob("*") if p.is_file()}
    assert files1 == files2


def test_all_roles_rendered(tmp_path: Path):
    render(tmp_path, env=ENV)
    for role in ROLES:
        assert (tmp_path / ".opencode" / "agent" / f"{role.name}.md").is_file()
        assert (tmp_path / ".claude" / "agents" / f"{role.name}.md").is_file()
    assert len(ROLES) == 5


def test_all_commands_rendered(tmp_path: Path):
    render(tmp_path, env=ENV)
    src = {p.name for p in (ROOT / "commands").glob("*.md")}
    oc = {p.name for p in (tmp_path / ".opencode" / "command").glob("*.md")}
    cc = {p.name for p in (tmp_path / ".claude" / "commands").glob("*.md")}
    assert len(src) == 24
    assert src == oc == cc


def test_opencode_json_contents(tmp_path: Path):
    render(tmp_path, env=ENV)
    config = json.loads((tmp_path / "opencode.json").read_text(encoding="utf-8"))
    assert config["model"] == "oreoa/analyst-x"
    assert config["provider"]["oreoa"]["options"]["baseURL"] == "http://host.docker.internal:1234/v1"
    for name in ("evidence", "knowledge", "case", "jobs"):
        assert config["mcp"][name]["url"] == f"http://mcp-{name}:8000/mcp"
    assert config["permission"]["bash"]["sudo *"] == "deny"


def test_role_model_env_wiring(tmp_path: Path):
    render(tmp_path, env=ENV)
    analyst = (tmp_path / ".opencode" / "agent" / "analyst.md").read_text(encoding="utf-8")
    reviewer = (tmp_path / ".opencode" / "agent" / "reviewer.md").read_text(encoding="utf-8")
    assert "model: analyst-x" in analyst
    assert "model: reviewer-x" in reviewer


def test_claude_mcp_json(tmp_path: Path):
    render(tmp_path, env=ENV)
    mcp = json.loads((tmp_path / ".mcp.json").read_text(encoding="utf-8"))
    assert set(mcp["mcpServers"]) == {"evidence", "knowledge", "case", "jobs"}


def test_agent_prompts_are_canonical_sources(tmp_path: Path):
    render(tmp_path, env=ENV)
    src = (ROOT / "agents" / "analyst.md").read_text(encoding="utf-8").rstrip()
    out = (tmp_path / ".opencode" / "agent" / "analyst.md").read_text(encoding="utf-8")
    assert src in out, "prompt body must come from agents/analyst.md verbatim"
