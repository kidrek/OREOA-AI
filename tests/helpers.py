"""Shared helpers for the OREOA-AI test suite (unit T1 and infra T5)."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_versions_env() -> dict[str, str]:
    values: dict[str, str] = {}
    for line in (ROOT / "versions.env").read_text().splitlines():
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            values[k] = v
    return values


def compose_cmd(profiles: list[str] | None = None) -> list[str]:
    cmd = [
        "docker", "compose", "--env-file", str(ROOT / ".env.example"),
        "-f", str(ROOT / "compose.yaml"),
    ]
    for p in profiles or []:
        cmd += ["--profile", p]
    return cmd


def compose_config(profiles: list[str] | None = None) -> dict:
    """Resolved compose configuration as JSON (docker compose config)."""
    env = os.environ.copy()
    env.update(load_versions_env())
    out = subprocess.run(
        compose_cmd(profiles) + ["config", "--format", "json"],
        capture_output=True, text=True, env=env, cwd=ROOT,
    )
    assert out.returncode == 0, f"compose config failed:\n{out.stderr}"
    return json.loads(out.stdout)


def compose_services(config: dict) -> dict:
    return config["services"]


def run_in_service(service: str, script: str, timeout: int = 120) -> subprocess.CompletedProcess:
    """One-off command in a service container with the entrypoint overridden.

    Runs /bin/sh -c <script> as the service user (compose user applies), with
    --no-deps so no dependency service is started.
    """
    env = os.environ.copy()
    env.update(load_versions_env())
    return subprocess.run(
        compose_cmd() + ["run", "--rm", "--no-deps", "--entrypoint", "/bin/sh", service, "-c", script],
        capture_output=True, text=True, env=env, cwd=ROOT, timeout=timeout,
    )


def image_exists(image: str) -> bool:
    return subprocess.run(
        ["docker", "image", "inspect", image],
        capture_output=True,
    ).returncode == 0
