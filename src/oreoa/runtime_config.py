"""Runtime config generator (docker_build_spec.md 3.2, make runtime-config).

Renders runtime-specific configuration from the canonical sources so nothing
is hand-maintained twice:
  - opencode.json            (providers, MCP servers, permissions)
  - .opencode/agent/<role>.md    + .opencode/command/<name>.md
  - .claude/agents/<role>.md     + .claude/commands/<name>.md
  - .mcp.json                (Claude Code MCP wiring)

Deterministic: same inputs -> byte-identical outputs (tested).
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class RoleSpec:
    name: str
    description: str
    mode: str  # primary | subagent | all
    model_env: str  # env var carrying the model name


ROLES: tuple[RoleSpec, ...] = (
    RoleSpec("ingest", "Runs pipeline jobs and summarizes coverage; never reasons about the case.", "subagent", "LLM_MODEL_TRIAGE"),
    RoleSpec("triage", "Post-fast-lane brief: top signals, coverage gaps, candidate hypotheses. Never promotes.", "subagent", "LLM_MODEL_TRIAGE"),
    RoleSpec("analyst", "DFIQ-driven investigation loop; proposes leads with citations; owns the dialogue.", "primary", "LLM_MODEL_ANALYST"),
    RoleSpec("reviewer", "Adversarial review of leads before promotion: citations, benign explanations, injection strings.", "subagent", "LLM_MODEL_REVIEWER"),
    RoleSpec("reporter", "Builds the final report from validated state only.", "subagent", "LLM_MODEL_ANALYST"),
)

MCP_SERVERS: tuple[str, ...] = ("evidence", "knowledge", "case", "jobs")


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _model_value(env: dict[str, str], var: str) -> str:
    return (env.get(var) or "").strip()


def render_opencode_json(env: dict[str, str]) -> str:
    base_url = (env.get("LLM_BASE_URL") or "").strip()
    default_model = _model_value(env, "LLM_MODEL_ANALYST")
    config: dict = {
        "$schema": "https://opencode.ai/config.json",
    }
    if base_url:
        provider = {
            "oreoa": {
                "npm": "@ai-sdk/openai-compatible",
                "name": "OREOA provider",
                "options": {"baseURL": base_url},
            }
        }
        config["provider"] = provider
        if default_model:
            config["model"] = f"oreoa/{default_model}"
    config["mcp"] = {
        name: {"type": "remote", "url": f"http://mcp-{name}:8000/mcp", "enabled": True}
        for name in MCP_SERVERS
    }
    config["permission"] = {
        "edit": "allow",
        "bash": {
            "sudo *": "deny",
            "rm -rf /*": "deny",
            "*": "allow",
        },
    }
    return json.dumps(config, indent=2, sort_keys=True) + "\n"


def render_mcp_json() -> str:
    servers = {
        name: {"type": "http", "url": f"http://mcp-{name}:8000/mcp"}
        for name in MCP_SERVERS
    }
    return json.dumps({"mcpServers": servers}, indent=2, sort_keys=True) + "\n"


def render_opencode_agent(role: RoleSpec, agents_dir: Path, env: dict[str, str]) -> str:
    body = (agents_dir / f"{role.name}.md").read_text(encoding="utf-8")
    model = _model_value(env, role.model_env)
    lines = ["---", f"description: {role.description}", f"mode: {role.mode}"]
    if model:
        lines.append(f"model: {model}")
    lines += ["---", "", body.rstrip(), ""]
    return "\n".join(lines)


def render_claude_agent(role: RoleSpec, agents_dir: Path) -> str:
    body = (agents_dir / f"{role.name}.md").read_text(encoding="utf-8")
    lines = [
        "---",
        f"name: {role.name}",
        f"description: {role.description}",
        "model: inherit",
        "---",
        "",
        body.rstrip(),
        "",
    ]
    return "\n".join(lines)


def render_command(cmd_path: Path) -> str:
    """Canonical command file -> runtime command file (verbatim passthrough).

    The canonical format (YAML frontmatter + prompt body with $ARGUMENTS) is
    already compatible with both runtimes; the generator copies it so that a
    future runtime-specific transformation has a single place to live.
    """
    return cmd_path.read_text(encoding="utf-8")


def _source_dirs() -> tuple[Path, Path]:
    """Canonical sources; the container mounts them at /agents and /commands."""
    agents = Path(os.environ.get("OREOA_AGENTS_DIR", ROOT / "agents"))
    commands = Path(os.environ.get("OREOA_COMMANDS_DIR", ROOT / "commands"))
    if not agents.is_dir() or not commands.is_dir():
        raise FileNotFoundError(
            "agents/ and commands/ must exist (canonical sources; set OREOA_AGENTS_DIR/"
            "OREOA_COMMANDS_DIR in containers)"
        )
    return agents, commands


def render(
    out_root: Path,
    env: dict[str, str] | None = None,
    runtimes: tuple[str, ...] = ("opencode", "claude"),
    layout: str = "project",
) -> list[Path]:
    """Render runtime config. Returns written paths.

    runtimes: "opencode" (opencode.json + agents/commands) and/or "claude"
    (.claude/ + .mcp.json).
    layout: "project" (host repo: opencode.json at root, agents under
    .opencode/) or "global" (container home config dir: agents beside the
    json).
    """
    env = env or dict(os.environ)
    agents_dir, commands_dir = _source_dirs()

    written: list[Path] = []

    if "opencode" in runtimes:
        oc_base = out_root / ".opencode" if layout == "project" else out_root
        _write(out_root / "opencode.json", render_opencode_json(env))
        written.append(out_root / "opencode.json")
        for role in ROLES:
            p = oc_base / "agent" / f"{role.name}.md"
            _write(p, render_opencode_agent(role, agents_dir, env))
            written.append(p)
        for cmd_path in sorted(commands_dir.glob("*.md")):
            p = oc_base / "command" / cmd_path.name
            _write(p, render_command(cmd_path))
            written.append(p)

    if "claude" in runtimes:
        _write(out_root / ".mcp.json", render_mcp_json())
        written.append(out_root / ".mcp.json")
        for role in ROLES:
            p = out_root / ".claude" / "agents" / f"{role.name}.md"
            _write(p, render_claude_agent(role, agents_dir))
            written.append(p)
        for cmd_path in sorted(commands_dir.glob("*.md")):
            p = out_root / ".claude" / "commands" / cmd_path.name
            _write(p, render_command(cmd_path))
            written.append(p)

    return written
