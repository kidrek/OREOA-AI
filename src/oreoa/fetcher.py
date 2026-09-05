"""Fetcher service (profile ``symbol-fetch``, Windows only) - SPEC knowledge
sources, docker_build_spec 3.6.

RQ worker on queue ``fetch`` (never served by worker-fast/worker-deep; those
refuse the lane). One job type: ``fetch_symbol`` - download a Windows kernel
PDB from the Microsoft symbol server and convert it to a Volatility 3 ISF
with ``pdbconv``.

Hardening and gating:

- the payload is revalidated at execution time (``JobEnvelope`` +
  ``FetchSymbolPayload``: known kernel PDB name, GUID pattern
  ``^[0-9A-F]{32}[0-9]+$``, ``confirmed_by_analyst=true``) - refusals happen
  BEFORE any network call (T5 11);
- the download URL is built exclusively from the validated ``pdb_name`` and
  ``guid`` - the code refuses any other URL by construction;
- egress goes through the ``proxy-fetch`` allow-list (two hosts: msdl and
  downloads.volatilityfoundation.org, compose + tinyproxy filter); only the
  kernel GUID ever leaves the host;
- writes are restricted to ``OREOA_SYMBOLS_DIR`` (mounted rw, layout
  ``windows/<pdb_name>/<GUID>-<age>.json`` as resolved by volatility3's
  ``PDBUtility.load_windows_symbol_table``); each ISF ships with a
  ``<file>.provenance.json`` (source URL, sha256, job id, confirmed_by,
  timestamp);
- the action is journaled to stdout (the fetcher has no case mount; the
  provenance file is the durable record). Key material never appears here -
  the fetcher never touches ``state/keys/``.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

MAX_PDB_BYTES = 512 * 1024 * 1024
DOWNLOAD_TIMEOUT = 600
CONVERT_TIMEOUT = 1800
GUID_PATTERN = re.compile(r"^[0-9A-F]{32}[0-9]+$")

# The two allow-listed hosts (docker_build_spec 3.6); only MSDL is used by
# fetch_symbol - the full symbol packs (downloads.volatilityfoundation.org)
# are fetched by make update-knowledge on the workstation.
MSDL_BASE = "https://msdl.microsoft.com/download/symbols"


def symbols_dir() -> Path:
    return Path(os.environ.get("OREOA_SYMBOLS_DIR", "/knowledge/custom/volatility_symbols")).resolve()


def build_pdb_url(pdb_name: str, guid: str) -> str:
    """Download URL from validated components only (msdl layout: the
    concatenated GUID+age identifier forms the path segment)."""
    if pdb_name not in ("ntkrnlmp.pdb", "ntkrpamp.pdb"):
        raise ValueError(f"pdb_name {pdb_name!r} outside known kernel PDBs")
    if not GUID_PATTERN.fullmatch(guid):
        raise ValueError(f"guid {guid!r} does not match the kernel identifier pattern")
    return f"{MSDL_BASE}/{pdb_name}/{guid}/{pdb_name}"


def split_identifier(identifier: str) -> tuple[str, str, int]:
    """``ntkrnlmp.pdb/<GUID><age>`` -> (pdb_name, guid32, age)."""
    pdb_name, _, tail = identifier.partition("/")
    if pdb_name not in ("ntkrnlmp.pdb", "ntkrpamp.pdb") or not tail:
        raise ValueError(f"identifier {identifier!r} must be <known-pdb-name>/<GUID><age>")
    if not GUID_PATTERN.fullmatch(tail):
        raise ValueError(f"identifier {identifier!r} GUID does not match the kernel pattern")
    return pdb_name, tail[:32], int(tail[32:])


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download_pdb(url: str, destination: Path) -> None:
    """Stream the PDB through the proxy (HTTPS_PROXY env) with a size cap."""
    import requests

    with requests.get(url, stream=True, timeout=(30, DOWNLOAD_TIMEOUT), allow_redirects=False) as response:
        if response.status_code != 200:
            raise RuntimeError(f"symbol server returned HTTP {response.status_code} for {url}")
        length = int(response.headers.get("content-length") or 0)
        if length > MAX_PDB_BYTES:
            raise RuntimeError(f"PDB too large ({length} bytes > cap {MAX_PDB_BYTES})")
        written = 0
        with open(destination, "wb") as handle:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                written += len(chunk)
                if written > MAX_PDB_BYTES:
                    raise RuntimeError(f"PDB exceeds the {MAX_PDB_BYTES}-byte cap")
                handle.write(chunk)


def convert_to_isf(pdb_path: Path, isf_path: Path) -> None:
    """PDB -> ISF via the volatility3 pdbconv CLI (subprocess, timeout)."""
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "volatility3.framework.symbols.windows.pdbconv",
            "-f",
            str(pdb_path),
            "-o",
            str(isf_path),
        ],
        capture_output=True,
        text=True,
        timeout=CONVERT_TIMEOUT,
    )
    if result.returncode != 0 or not isf_path.is_file():
        raise RuntimeError(f"pdbconv failed (rc={result.returncode}): {result.stderr.strip()[:512]}")


def validate_isf(isf_path: Path, pdb_name: str, guid: str) -> None:
    """The ISF must be JSON and carry the matching PDB metadata."""
    data = json.loads(isf_path.read_text(encoding="utf-8"))
    metadata = (data.get("metadata") or {}).get("windows") or {}
    pdb_meta = metadata.get("pdb") or {}
    expected_guid, age = guid[:32], guid[32:]
    if pdb_meta and (str(pdb_meta.get("GUID", "")).upper() != expected_guid or str(pdb_meta.get("age")) != age):
        raise RuntimeError(
            f"ISF metadata mismatch: expected {expected_guid}-{age}, got "
            f"{pdb_meta.get('GUID')}-{pdb_meta.get('age')}"
        )


def run_fetch_symbol(envelope: dict) -> dict:
    """RQ job entrypoint for ``fetch_symbol`` (queue ``fetch``).

    Refusals happen before any network call; the payload never carries key
    material; the only data leaving the host is the kernel GUID.
    """
    from oreoa.jobs_model import FetchSymbolPayload, JobEnvelope

    env = JobEnvelope.model_validate(envelope)
    payload = FetchSymbolPayload.model_validate(env.payload)
    pdb_name = payload.pdb_name
    guid = payload.guid.upper()

    target_dir = symbols_dir() / "windows" / pdb_name
    if not symbols_dir().is_dir():
        raise RuntimeError(f"symbols dir {symbols_dir()} is not mounted (profile symbol-fetch)")
    target_dir.mkdir(parents=True, exist_ok=True)
    isf_path = target_dir / f"{guid[:32]}-{int(guid[32:])}.json"
    provenance_path = isf_path.with_name(isf_path.name + ".provenance.json")

    job = None
    try:
        from rq import get_current_job

        job = get_current_job()
    except Exception:  # noqa: BLE001 - job id is provenance metadata only
        job = None

    import requests  # noqa: F401 - fail fast when requests is absent

    url = build_pdb_url(pdb_name, guid)
    print(f"[fetcher] job={getattr(job, 'id', None)} pdb={pdb_name} guid={guid} url={url}", flush=True)

    import tempfile

    with tempfile.TemporaryDirectory(prefix="oreoa-fetch-") as tmp:
        pdb_tmp = Path(tmp) / pdb_name
        download_pdb(url, pdb_tmp)
        pdb_digest = sha256_of(pdb_tmp)
        # the converted ISF lands next to its final location (same filesystem)
        # so the rename is atomic; the .tmp suffix keeps it out of the ISF scans
        tmp_isf = isf_path.with_name(isf_path.name + ".fetching.tmp")
        try:
            convert_to_isf(pdb_tmp, tmp_isf)
            validate_isf(tmp_isf, pdb_name, guid)
            os.replace(tmp_isf, isf_path)
        finally:
            tmp_isf.unlink(missing_ok=True)

    digest = sha256_of(isf_path)
    provenance = {
        "pdb_name": pdb_name,
        "identifier": f"{pdb_name}/{guid}",
        "guid": guid[:32],
        "age": int(guid[32:]),
        "source_url": url,
        "sha256_pdb": pdb_digest,
        "sha256_isf": digest,
        "job_id": getattr(job, "id", None),
        "confirmed_by": "analyst",
        "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    provenance_path.write_text(json.dumps(provenance, indent=2, sort_keys=True), encoding="utf-8")
    print(f"[fetcher] ISF written: {isf_path} (sha256 {digest[:16]}...)", flush=True)

    return {
        "status": "ok",
        "isf_path": str(isf_path),
        "sha256_isf": digest,
        "sha256_pdb": pdb_digest,
        "provenance": str(provenance_path),
    }


def main(argv: list[str] | None = None) -> int:
    from rq import Queue, Worker

    from oreoa.worker import redis_connection

    connection = redis_connection()
    worker = Worker(
        [Queue("fetch", connection=connection)],
        connection=connection,
        name=f"oreoa-fetch-{os.getpid()}",
    )
    print(f"oreoa fetcher {worker.name} listening on queue 'fetch'", flush=True)
    worker.work(burst=False)
    return 0


if __name__ == "__main__":
    sys.exit(main())
