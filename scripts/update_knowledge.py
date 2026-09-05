"""Fetch the pinned knowledge sources on the workstation (SPEC "Knowledge
sources"; docker_build_spec 8).

This is the only path by which external knowledge enters the tool. It runs
on the analyst's workstation or a build host - never inside the agent/workers
containers (their egress is limited to LLM endpoints).

Default (minimal profile, S1.5 arbitration):

- the 14 pinned git/file sources of versions.env land under
  ``knowledge/upstream/<name>/`` at their pinned commit/tag;
- the ClamAV database is refreshed through a one-shot container
  (``CLAMAV_IMAGE``) writing to ``knowledge/upstream/clamav_db/`` - no
  freshclam installation on the host; failures are non-blocking but visible
  in the summary and recorded in ``knowledge/snapshot.json``;
- ``knowledge/snapshot.json`` records every source: {name, url, commit,
  fetched_at, licence} (+ sha256 for symbols) - the file
  ``case.yaml.sessions[].knowledge_snapshot`` copies.

Options (SPEC decision (h) - both on demand, never by default):

- ``--full-symbols``  official Volatility ISF packs (3 zips, sha256-pinned
  in versions.env via VOL_SYMBOLS_*_SHA256);
- ``--symbol <os> <identifier>``  one ISF on demand - Windows:
  ``ntkrnlmp.pdb/<GUID><age>`` downloaded from msdl and converted with
  pdbconv (needs volatility3 on the host); Linux/macOS: dwarf2json guidance
  printed (nothing to download from a fixed host exists);
- ``--nsrl``  curated NSRL subset - refused with a clear message until the
  NIST dataset pin is arbitrated (no NSRL_* pin exists in versions.env yet);
- ``--no-clamav``  skip the ClamAV refresh (CI, hosts without Docker).

Idempotent: sources already at their pinned commit are skipped (``--force``
re-fetches). Pins are updated deliberately (PR to the repo), never here.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UPSTREAM = ROOT / "knowledge" / "upstream"
SNAPSHOT_PATH = ROOT / "knowledge" / "snapshot.json"
SYMBOLS_CUSTOM = ROOT / "knowledge" / "custom" / "volatility_symbols"

VOL_SYMBOLS_BASE = "https://downloads.volatilityfoundation.org/volatility3/symbols"
MSDL_BASE = "https://msdl.microsoft.com/download/symbols"

GIT_REF_RE = re.compile(r"^[0-9a-f]{40}$|^[0-9A-Za-z][0-9A-Za-z._-]*$")


@dataclass(frozen=True)
class Source:
    name: str
    url: str
    pin_var: str
    licence: str  # SPEC-stated licence; "*" = detect from the LICENSE file
    kind: str = "git"  # git | file


# The 14 pinned sources (versions.env). velociraptor_artifacts has no pin yet
# (reference only, SPEC table) and is deliberately not fetched at S1.5.
SOURCES: tuple[Source, ...] = (
    Source("dfiq", "https://github.com/google/dfiq", "DFIQ_COMMIT", "Apache-2.0"),
    Source(
        "forensic_artifacts",
        "https://github.com/ForensicArtifacts/artifacts",
        "FORENSIC_ARTIFACTS_COMMIT",
        "Apache-2.0",
    ),
    Source(
        "attack",
        "https://github.com/mitre-attack/attack-stix-data",
        "ATTACK_VERSION",
        "MITRE Terms of Use",
        kind="file",
    ),
    Source("sigma", "https://github.com/SigmaHQ/sigma", "SIGMA_COMMIT", "Detection Rule License 1.1"),
    Source(
        "hayabusa_rules",
        "https://github.com/Yamato-Security/hayabusa-rules",
        "HAYABUSA_RULES_COMMIT",
        "*",
    ),
    Source(
        "chainsaw_rules",
        "https://github.com/WithSecureLabs/chainsaw",
        "CHAINSAW_RULES_COMMIT",
        "GPL-3.0",
    ),
    Source(
        "yara_elastic",
        "https://github.com/elastic/protections-artifacts",
        "YARA_ELASTIC_COMMIT",
        "Elastic License 2.0",
    ),
    Source(
        "signature_base",
        "https://github.com/Neo23x0/signature-base",
        "SIGNATURE_BASE_COMMIT",
        "*",
    ),
    Source("lolbas", "https://github.com/LOLBAS-Project/LOLBAS", "LOLBAS_COMMIT", "GPL-3.0 (data use only)"),
    Source(
        "gtfobins",
        "https://github.com/GTFOBins/GTFOBins.github.io",
        "GTFOBINS_COMMIT",
        "GPL-3.0 (data use only)",
    ),
    Source("loobins", "https://github.com/infosecB/LOOBins", "LOOBINS_COMMIT", "*"),
    Source(
        "hijacklibs",
        "https://github.com/wietze/HijackLibs",
        "HIJACKLIBS_COMMIT",
        "*",
    ),
    Source(
        "loldrivers",
        "https://github.com/magicsword-io/LOLDrivers",
        "LOLDRIVERS_COMMIT",
        "GPL-3.0 (data use only)",
    ),
    Source("lolrmm", "https://github.com/magicsword-io/LOLRMM", "LOLRMM_COMMIT", "*"),
)


def load_pins() -> dict[str, str]:
    """Parse versions.env (KEY=VALUE lines; comments ignored)."""
    pins: dict[str, str] = {}
    for line in (ROOT / "versions.env").read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        pins[key.strip()] = value.strip()
    return pins


def run_git(args: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, timeout=600)


def detect_licence(directory: Path) -> str:
    """Licence detected from the source tree (fallback when SPEC has no
    explicit statement): the LICENSE/COPYING file's leading words."""
    for candidate in sorted(directory.glob("LICENSE*")) + sorted(directory.glob("COPYING*")):
        head = candidate.read_text(encoding="utf-8", errors="replace")[:200].lower()
        if "gnu general public license" in head:
            return "GPL (see LICENSE)"
        if "apache license" in head:
            return "Apache-2.0 (see LICENSE)"
        if "mit license" in head:
            return "MIT (see LICENSE)"
        if "creative commons" in head:
            return "CC (see LICENSE)"
        return "custom (see LICENSE)"
    return "unknown"


def fetch_git_source(source: Source, pin: str, dest: Path, force: bool) -> tuple[str, str, bool]:
    """Shallow-fetch the pinned commit into dest; returns (resolved_ref,
    licence, fetched_now)."""
    if dest.is_dir() and not force:
        head = run_git(["rev-parse", "HEAD"], cwd=dest)
        if head.returncode == 0 and head.stdout.strip() == pin:
            licence = detect_licence(dest) if source.licence == "*" else source.licence
            return pin, licence, False
        shutil.rmtree(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.is_dir():
        shutil.rmtree(dest)
    tmp = dest.with_suffix(".tmp-fetch")
    if tmp.is_dir():
        shutil.rmtree(tmp)
    fetch = run_git(["clone", "--filter=blob:none", "--no-checkout", source.url, str(tmp)])
    if fetch.returncode != 0:
        raise RuntimeError(f"git clone failed for {source.name}: {fetch.stderr.strip()[:300]}")
    checkout = run_git(["fetch", "--depth", "1", "origin", pin], cwd=tmp)
    if checkout.returncode != 0:
        run_git(["remote", "set-branches", "origin", "*"], cwd=tmp)
        checkout = run_git(["fetch", "--depth", "1", "origin", pin], cwd=tmp)
        if checkout.returncode != 0:
            raise RuntimeError(f"git fetch {pin} failed for {source.name}: {checkout.stderr.strip()[:300]}")
    rev = run_git(["rev-parse", "FETCH_HEAD"], cwd=tmp)
    if rev.returncode != 0:
        raise RuntimeError(f"cannot resolve FETCH_HEAD for {source.name}")
    resolved = rev.stdout.strip()
    co = run_git(["checkout", "FETCH_HEAD"], cwd=tmp)
    if co.returncode != 0:
        raise RuntimeError(f"git checkout failed for {source.name}: {co.stderr.strip()[:300]}")
    tmp.rename(dest)
    licence = detect_licence(dest) if source.licence == "*" else source.licence
    return resolved, licence, True


def attack_file_url(version: str) -> tuple[str, str]:
    """(url, filename) for the pinned ATT&CK STIX bundle - a versioned file,
    never the whole repository (docker_build_spec: pin a versioned file)."""
    numeric = version.lstrip("v")
    filename = f"enterprise-attack-{numeric}.json"
    url = f"https://raw.githubusercontent.com/mitre-attack/attack-stix-data/{version}/enterprise-attack/{filename}"
    return url, filename


def fetch_file_source(source: Source, pin: str, dest: Path, force: bool) -> tuple[str, str, bool]:
    """Download one pinned file (attack: enterprise-attack-<ver>.json)."""
    dest.mkdir(parents=True, exist_ok=True)
    url, filename = attack_file_url(pin)
    target = dest / filename
    if target.is_file() and not force:
        return pin, source.licence, False
    urllib.request.urlretrieve(url, target)  # noqa: S310 - pinned https URL
    return pin, source.licence, True


def refresh_clamav(pins: dict[str, str], summary: dict) -> dict:
    """Refresh the ClamAV db through a one-shot container (host stays clean).

    Non-blocking on failure: the error is recorded in the snapshot and
    printed in the summary.
    """
    image = pins.get("CLAMAV_IMAGE")
    db_dir = UPSTREAM / "clamav_db"
    if not image:
        return {"status": "skipped", "message": "no CLAMAV_IMAGE pin in versions.env"}
    db_dir.mkdir(parents=True, exist_ok=True)
    docker = shutil.which("docker")
    if docker is None:
        return {"status": "error", "message": "docker not found on host (use --no-clamav)"}
    result = subprocess.run(
        [
            docker,
            "run",
            "--rm",
            # run as the host user: files land host-owned (no root pollution
            # of the checkout) and freshclam may write the datadir
            "--user",
            f"{os.getuid()}:{os.getgid()}",
            "--entrypoint",
            "freshclam",
            "-v",
            f"{db_dir.resolve()}:/var/lib/clamav",
            image,
            "--datadir=/var/lib/clamav",
            # the log goes into the writable bind (the image's /var/log path
            # belongs to the container user)
            "--log=/var/lib/clamav/freshclam.log",
            "--stdout",
        ],
        capture_output=True,
        text=True,
        timeout=900,
    )
    if result.returncode != 0:
        return {
            "status": "error",
            "message": f"freshclam failed (rc={result.returncode}): {result.stderr.strip()[-300:]}",
        }
    databases = sorted(p.name for p in db_dir.glob("*.cvd")) + sorted(p.name for p in db_dir.glob("*.cld"))
    if not databases:
        return {"status": "error", "message": "freshclam produced no database files"}
    return {"status": "ok", "image": image, "databases": databases, "updated_at": utc_now()}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def fetch_full_symbols(pins: dict[str, str]) -> list[dict]:
    """Official Volatility ISF packs (3 zips, sha256-pinned in versions.env)."""
    entries = []
    for os_name, pin_var in (
        ("windows", "VOL_SYMBOLS_WINDOWS_SHA256"),
        ("mac", "VOL_SYMBOLS_MAC_SHA256"),
        ("linux", "VOL_SYMBOLS_LINUX_SHA256"),
    ):
        expected = pins.get(pin_var, "")
        if not expected:
            raise RuntimeError(
                f"{pin_var} is empty - pin the sha256 in versions.env (make pins) before --full-symbols"
            )
        url = f"{VOL_SYMBOLS_BASE}/{os_name}.zip"
        dest = UPSTREAM / "volatility_symbols"
        dest.mkdir(parents=True, exist_ok=True)
        target = dest / f"{os_name}.zip"
        print(f"  downloading {url} ...", flush=True)
        urllib.request.urlretrieve(url, target)  # noqa: S310 - pinned https URL
        digest = sha256_of(target)
        if digest != expected:
            raise RuntimeError(f"{os_name}.zip sha256 mismatch: {digest} != pinned {expected}")
        entries.append({"name": f"volatility_symbols_{os_name}", "url": url, "sha256": digest})
    return entries


def fetch_single_symbol(pins: dict[str, str], os_name: str, identifier: str) -> dict:
    """One ISF on demand (command mode, works air-gapped for the guidance).

    Windows: ``ntkrnlmp.pdb/<GUID><age>`` -> PDB from msdl, converted with
    pdbconv (requires volatility3 on the host). Linux/macOS: dwarf2json
    guidance is printed - nothing to download from a fixed host exists
    (SPEC knowledge sources, command mode).
    """
    if os_name == "windows":
        try:
            from oreoa.fetcher import build_pdb_url, split_identifier

            pdb_name, guid, _age = split_identifier(identifier)
            url = build_pdb_url(pdb_name, guid + str(_age))
        except ValueError as exc:
            raise SystemExit(f"error: {exc}")
        SYMBOLS_CUSTOM.mkdir(parents=True, exist_ok=True)
        target_dir = SYMBOLS_CUSTOM / "windows" / pdb_name
        target_dir.mkdir(parents=True, exist_ok=True)
        try:
            import requests  # noqa: F401
        except ImportError:
            raise SystemExit("error: requests is required on the host for --symbol (pip install requests)")
        print(f"  downloading {url} ...", flush=True)
        with tempfile.TemporaryDirectory(prefix="oreoa-symbol-") as tmp:
            pdb_tmp = Path(tmp) / pdb_name
            with requests.get(url, stream=True, timeout=(30, 600)) as response:
                if response.status_code != 200:
                    raise SystemExit(f"error: symbol server returned HTTP {response.status_code}")
                with open(pdb_tmp, "wb") as handle:
                    for chunk in response.iter_content(chunk_size=1024 * 1024):
                        handle.write(chunk)
            isf_path = target_dir / f"{guid}-{_age}.json"
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "volatility3.framework.symbols.windows.pdbconv",
                    "-f",
                    str(pdb_tmp),
                    "-o",
                    str(isf_path),
                ],
                capture_output=True,
                text=True,
                timeout=1800,
            )
            if result.returncode != 0 or not isf_path.is_file():
                raise SystemExit(
                    f"error: pdbconv failed (is volatility3 installed on the host?): "
                    f"{result.stderr.strip()[-300:]}"
                )
        provenance = {
            "identifier": f"{pdb_name}/{guid}{_age}",
            "source_url": url,
            "sha256_isf": sha256_of(isf_path),
            "confirmed_by": "analyst (workstation command mode)",
            "fetched_at": utc_now(),
        }
        (isf_path.with_name(isf_path.name + ".provenance.json")).write_text(
            json.dumps(provenance, indent=2, sort_keys=True), encoding="utf-8"
        )
        return {"name": f"symbol_{pdb_name}", "isf_path": str(isf_path), **provenance}

    print(
        f"dwarf2json guidance for {os_name}: the ISF is generated on the workstation "
        f"from the kernel debug package (Linux: distro dbgsym/dmesg banner match, "
        f"macOS: KernelDebugKit):\n"
        f"  dwarf2json linux --elf <vmlinux-with-debug-symbols> --system-map <System.map> "
        f"> knowledge/custom/volatility_symbols/linux/<banner>.json\n"
        f"  dwarf2json mac --volatility3 <kernel.dwarf> > "
        f"knowledge/custom/volatility_symbols/mac/<kdk-id>.json\n"
        f"Then rerun /ingest.",
        flush=True,
    )
    return {"name": f"symbol_{os_name}_guidance", "status": "guidance_printed"}


def write_snapshot(payload: dict) -> None:
    SNAPSHOT_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = SNAPSHOT_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    tmp.replace(SNAPSHOT_PATH)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--force", action="store_true", help="re-fetch sources already at their pin")
    parser.add_argument("--no-clamav", action="store_true", help="skip the ClamAV db refresh (default: on)")
    parser.add_argument("--full-symbols", action="store_true", help="download the official Volatility ISF packs")
    parser.add_argument("--symbol", nargs=2, metavar=("OS", "IDENTIFIER"), help="one ISF on demand")
    parser.add_argument("--nsrl", action="store_true", help="curated NSRL subset (not pinned yet - refused)")
    args = parser.parse_args(argv)

    pins = load_pins()
    UPSTREAM.mkdir(parents=True, exist_ok=True)

    sources_entries: list[dict] = []
    errors: list[str] = []
    for source in SOURCES:
        pin = pins.get(source.pin_var, "")
        if not pin:
            errors.append(f"{source.name}: pin {source.pin_var} missing from versions.env")
            continue
        if not GIT_REF_RE.fullmatch(pin):
            errors.append(f"{source.name}: invalid pin {pin!r}")
            continue
        dest = UPSTREAM / source.name
        try:
            if source.kind == "git":
                resolved, licence, fetched = fetch_git_source(source, pin, dest, args.force)
            else:
                resolved, licence, fetched = fetch_file_source(source, pin, dest, args.force)
            sources_entries.append(
                {
                    "name": source.name,
                    "url": source.url,
                    "commit": resolved,
                    "fetched_at": utc_now() if fetched else "cached",
                    "licence": licence,
                }
            )
            print(f"  {source.name}: {'fetched' if fetched else 'cached'} at {resolved[:12]} ({licence})")
        except Exception as exc:  # noqa: BLE001 - one bad source must not abort the rest
            errors.append(f"{source.name}: {exc}")
            print(f"  {source.name}: ERROR {exc}", file=sys.stderr)

    clamav_status: dict = {"status": "skipped", "message": "--no-clamav"}
    if not args.no_clamav:
        print("clamav: refreshing db via one-shot container ...", flush=True)
        clamav_status = refresh_clamav(pins, {})
        print(f"  clamav: {clamav_status.get('status')}: {clamav_status.get('message', 'ok')}")

    symbols_entries: list[dict] = []
    if args.full_symbols:
        symbols_entries.extend(fetch_full_symbols(pins))
    if args.symbol:
        symbols_entries.append(fetch_single_symbol(pins, args.symbol[0], args.symbol[1]))

    if args.nsrl:
        errors.append(
            "nsrl: no NSRL pin exists in versions.env yet - the curated NIST subset "
            "is arbitrated with the architect before implementation (refused, nothing fetched)"
        )

    snapshot = {
        "version": 1,
        "generated_at": utc_now(),
        "sources": sources_entries,
        "symbols": symbols_entries,
        "clamav_db": clamav_status,
        "errors": errors,
    }
    write_snapshot(snapshot)

    print(f"snapshot written: {SNAPSHOT_PATH} ({len(sources_entries)} sources)")
    if errors:
        print(f"{len(errors)} error(s):", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
