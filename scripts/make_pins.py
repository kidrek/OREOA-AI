#!/usr/bin/env python3
"""Resolve and refresh versions.env pins (docker_build_spec.md 7).

The only tool allowed to edit versions.env. Line-based rewrite: comments and
order are preserved, only values change. Shows the diff and asks for
confirmation unless --yes. Binary tool pins (hayabusa, chainsaw, ...) are
deliberately not resolved here until their work-order step.

Usage: python3 scripts/make_pins.py [--yes]
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSIONS = ROOT / "versions.env"
UA = {"User-Agent": "oreoa-make-pins/1.0"}


def fetch(url: str, timeout: int = 15) -> bytes:
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def resolve_pip_image(tag: str) -> str | None:
    out = subprocess.run(
        ["docker", "buildx", "imagetools", "inspect", tag],
        capture_output=True, text=True,
    )
    m = re.search(r"^Digest:\s+(sha256:[0-9a-f]{64})$", out.stdout, re.M)
    return m.group(1) if m else None


def resolve_debian_package(package: str, suite: str = "bookworm") -> str | None:
    """Exact version of a Debian package, parsed from packages.debian.org."""
    try:
        html = fetch(f"https://packages.debian.org/{suite}/{package}").decode()
    except Exception:
        return None
    m = re.search(rf"{package} \((\d[^\s)]+)\)", html)
    return m.group(1) if m else None


def resolve_npm(pkg: str) -> str | None:
    url = f"https://registry.npmjs.org/{pkg}/latest"
    try:
        return json.loads(fetch(url)).get("version")
    except Exception:
        return None


def resolve_docker_tags(repo: str, pattern: str) -> str | None:
    url = f"https://registry.hub.docker.com/v2/repositories/{repo}/tags?page_size=100"
    try:
        tags = [t["name"] for t in json.loads(fetch(url))["results"]]
    except Exception:
        return None
    rx = re.compile(pattern)
    cand = [t for t in tags if rx.fullmatch(t)]
    if not cand:
        return None
    def key(t: str) -> tuple[int, ...]:
        return tuple(int(p) for p in re.findall(r"\d+", t))
    return sorted(cand, key=key)[-1]


def resolve_pip(pkg: str) -> str | None:
    try:
        text = fetch(f"https://pypi.org/pypi/{pkg}/json").decode()
        return json.loads(text)["info"]["version"]
    except Exception:
        return None


def resolve_github_head(repo: str) -> str | None:
    try:
        data = json.loads(fetch(f"https://api.github.com/repos/{repo}/commits?per_page=1"))
        return data[0]["sha"] if isinstance(data, list) and data else None
    except Exception:
        return None


def resolve_attack_version() -> str | None:
    try:
        tags = json.loads(fetch("https://api.github.com/repos/mitre-attack/attack-stix-data/tags?per_page=100"))
        names = [t["name"] for t in tags if re.fullmatch(r"v\d+\.\d+", t["name"])]
        if not names:
            return None
        return sorted(names, key=lambda n: tuple(int(p) for p in n[1:].split(".")))[-1]
    except Exception:
        return None


# key -> resolver (versions.env value key, not the env var name)
RESOLVERS: dict[str, callable] = {
    "PYTHON_IMAGE": lambda cur: resolve_pip_image("python:3.12-slim-bookworm"),
    "OPENCODE_VERSION": lambda cur: resolve_npm("opencode-ai"),
    "CLAUDE_CODE_VERSION": lambda cur: resolve_npm("@anthropic-ai/claude-code"),
    "DEBIAN_IMAGE": lambda cur: resolve_pip_image("debian:bookworm-slim"),
    "TINYPROXY_VERSION": lambda cur: resolve_debian_package("tinyproxy"),
    "REDIS_IMAGE": lambda cur: resolve_docker_tags("library/redis", r"\d+\.\d+\.\d+-alpine\d+\.\d+"),
    "DISSECT_VERSION": lambda cur: resolve_pip("dissect.target"),
    "PLASO_VERSION": lambda cur: resolve_pip("plaso"),
    "VOLATILITY3_VERSION": lambda cur: resolve_pip("volatility3"),
    "YARA_PYTHON_VERSION": lambda cur: resolve_pip("yara-python"),
    "PYARROW_VERSION": lambda cur: resolve_pip("pyarrow"),
    "DUCKDB_VERSION": lambda cur: resolve_pip("duckdb"),
    "RQ_VERSION": lambda cur: resolve_pip("rq"),
    "MCP_VERSION": lambda cur: resolve_pip("mcp"),
    "ATTACK_VERSION": lambda cur: resolve_attack_version(),
    "DFIQ_COMMIT": lambda cur: resolve_github_head("google/dfiq"),
    "FORENSIC_ARTIFACTS_COMMIT": lambda cur: resolve_github_head("ForensicArtifacts/artifacts"),
    "SIGMA_COMMIT": lambda cur: resolve_github_head("SigmaHQ/sigma"),
    "HAYABUSA_RULES_COMMIT": lambda cur: resolve_github_head("Yamato-Security/hayabusa-rules"),
    "CHAINSAW_RULES_COMMIT": lambda cur: resolve_github_head("WithSecureLabs/chainsaw"),
    "YARA_ELASTIC_COMMIT": lambda cur: resolve_github_head("elastic/protections-artifacts"),
    "SIGNATURE_BASE_COMMIT": lambda cur: resolve_github_head("Neo23x0/signature-base"),
    "LOLBAS_COMMIT": lambda cur: resolve_github_head("LOLBAS-Project/LOLBAS"),
    "GTFOBINS_COMMIT": lambda cur: resolve_github_head("GTFOBins/GTFOBins.github.io"),
    "LOOBINS_COMMIT": lambda cur: resolve_github_head("infosecB/LOOBins"),
    "HIJACKLIBS_COMMIT": lambda cur: resolve_github_head("wietze/HijackLibs"),
    "LOLDRIVERS_COMMIT": lambda cur: resolve_github_head("magicsword-io/LOLDrivers"),
    "LOLRMM_COMMIT": lambda cur: resolve_github_head("magicsword-io/LOLRMM"),
}


def main() -> int:
    args = set(sys.argv[1:])
    assume_yes = "--yes" in args or "-y" in args

    lines = VERSIONS.read_text().splitlines()
    current: dict[str, str] = {}
    for line in lines:
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            current[k] = v

    diff: list[tuple[str, str, str]] = []  # (key, old, new)
    new_values = dict(current)
    for key, resolver in RESOLVERS.items():
        try:
            value = resolver(current)
        except Exception as exc:  # network hiccup -> keep current, warn
            print(f"warn: {key}: resolution failed ({exc})", file=sys.stderr)
            value = None
        if not value:
            print(f"warn: {key}: unresolved, keeping {current.get(key)!r}", file=sys.stderr)
            continue
        if current.get(key) != value:
            new_values[key] = value
            diff.append((key, current.get(key, "<none>"), value))

    if not diff:
        print("versions.env already up to date")
        return 0

    print(f"{len(diff)} pin(s) to update:")
    for key, old, new in diff:
        print(f"  {key}: {old} -> {new}")

    if not assume_yes:
        try:
            answer = input("write versions.env? [y/N] ")
        except EOFError:
            answer = "n"
        if answer.strip().lower() != "y":
            print("aborted, versions.env unchanged")
            return 1

    out = []
    for line in lines:
        if line and not line.startswith("#") and "=" in line:
            k = line.split("=", 1)[0]
            out.append(f"{k}={new_values[k]}")
        else:
            out.append(line)
    VERSIONS.write_text("\n".join(out) + "\n")
    print(f"versions.env written ({VERSIONS})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
