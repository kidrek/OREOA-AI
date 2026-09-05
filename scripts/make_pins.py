#!/usr/bin/env python3
"""Resolve and refresh versions.env pins (docker_build_spec.md 7).

The only tool allowed to edit versions.env. Line-based rewrite: comments and
order are preserved, only values change. Shows the diff and asks for
confirmation unless --yes. Binary tool pins (hayabusa, chainsaw, zircolite)
are resolved from GitHub releases: the sha256 of the pinned asset is computed
at pin time (trust-on-first-pin, reviewed by PR) and verified at image build.

Usage: python3 scripts/make_pins.py [--yes] [--only KEY[,KEY...]]
"""

from __future__ import annotations

import hashlib
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


# Memo for version+sha256 pairs resolved from the same release payload.
_RELEASE_CACHE: dict[str, tuple[str, str]] = {}


def resolve_github_release(repo: str, asset: str | None) -> tuple[str, str]:
    """Latest release of a repo as (version, sha256) for pin-time checksums.

    ``asset`` is a per-release asset name where ``{V}`` is the version without
    the leading ``v``; ``None`` selects the source tarball of the tag
    (refs/tags/vX.tar.gz) - used when a project ships no binary release and is
    not on PyPI (zircolite). The sha256 is computed at pin time over the TLS
    download (trust-on-first-pin, reviewed by PR) and verified at image build.
    """
    if repo in _RELEASE_CACHE:
        return _RELEASE_CACHE[repo]
    data = json.loads(fetch(f"https://api.github.com/repos/{repo}/releases/latest"))
    tag = data["tag_name"]
    version = tag[1:] if tag.startswith("v") else tag
    if asset is None:
        url = f"https://github.com/{repo}/archive/refs/tags/{tag}.tar.gz"
    else:
        matches = [a for a in data["assets"] if a["name"] == asset.replace("{V}", version)]
        if not matches:
            raise ValueError(f"{repo}: asset {asset!r} not found in release {tag}")
        url = matches[0]["browser_download_url"]
    blob = fetch(url, timeout=180)
    info = (version, hashlib.sha256(blob).hexdigest())
    _RELEASE_CACHE[repo] = info
    return info


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
    "PYCLAMD_VERSION": lambda cur: resolve_pip("pyclamd"),
    # Release binaries (work-order step 2, build order docker_build_spec 11.2).
    # zircolite ships no binary release and is not on PyPI: source tarball.
    # Hayabusa: musl build - the gnu build needs glibc 2.38+, the platform
    # base is debian bookworm (glibc 2.36).
    "HAYABUSA_VERSION": lambda cur: resolve_github_release(
        "Yamato-Security/hayabusa", "hayabusa-{V}-lin-x64-musl.zip")[0],
    "HAYABUSA_SHA256": lambda cur: resolve_github_release(
        "Yamato-Security/hayabusa", "hayabusa-{V}-lin-x64-musl.zip")[1],
    "CHAINSAW_VERSION": lambda cur: resolve_github_release(
        "WithSecureLabs/chainsaw", "chainsaw_x86_64-unknown-linux-gnu.tar.gz")[0],
    "CHAINSAW_SHA256": lambda cur: resolve_github_release(
        "WithSecureLabs/chainsaw", "chainsaw_x86_64-unknown-linux-gnu.tar.gz")[1],
    "ZIRCOLITE_VERSION": lambda cur: resolve_github_release("wagga40/Zircolite", None)[0],
    "ZIRCOLITE_SHA256": lambda cur: resolve_github_release("wagga40/Zircolite", None)[1],
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

    only: set[str] | None = None
    for arg in sorted(args - {"--yes", "-y"}):
        if arg.startswith("--only="):
            only = {k.strip() for k in arg.split("=", 1)[1].split(",") if k.strip()}
        elif arg == "--only":
            print("usage: --only=KEY[,KEY...]", file=sys.stderr)
            return 2
        else:
            print(f"unknown argument: {arg}", file=sys.stderr)
            return 2
    if only:
        unknown = only - set(RESOLVERS)
        if unknown:
            print(f"unknown pin key(s): {', '.join(sorted(unknown))}", file=sys.stderr)
            return 2

    lines = VERSIONS.read_text().splitlines()
    current: dict[str, str] = {}
    for line in lines:
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            current[k] = v

    diff: list[tuple[str, str, str]] = []  # (key, old, new)
    new_values = dict(current)
    for key, resolver in RESOLVERS.items():
        if only is not None and key not in only:
            continue
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
