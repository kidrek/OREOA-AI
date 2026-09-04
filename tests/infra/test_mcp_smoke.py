"""T5: MCP smoke in the real image - env wiring + case-id refusal (items 9).

Runs inside the mcp-evidence image (real env: OREOA_CASES=/cases, real SDK):
builds the server, drives the streamable-HTTP transport in-process, checks
the tool set registers, an unknown case id is refused and the smoke case is
readable through the read-only mount.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from helpers import compose_cmd, image_exists, load_versions_env  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
CASE_ID = "smoke-mcp-1"

SCRIPT = r'''
import asyncio
import json
import os

import httpx2
from mcp.client.session import ClientSession
from mcp.client.streamable_http import streamable_http_client
from mcp.server.transport_security import TransportSecuritySettings

from oreoa import mcp_server

assert os.environ.get("OREOA_CASES") == "/cases", os.environ.get("OREOA_CASES")

server = mcp_server.build("evidence")
app = server.streamable_http_app(
    host="127.0.0.1",
    stateless_http=True,
    transport_security=TransportSecuritySettings(
        enable_dns_rebinding_protection=True, allowed_hosts=["testserver"]
    ),
)


async def run():
    client = httpx2.AsyncClient(transport=httpx2.ASGITransport(app=app), timeout=30)
    async with server.session_manager.run():
        async with streamable_http_client(
            "http://testserver/mcp", http_client=client
        ) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                tools = await session.list_tools()
                names = {t.name for t in tools.tools}
                assert "list_evidence" in names and "get_raw" in names, names
                result = await session.call_tool(
                    "list_evidence", {"case_id": "no-such-case-999"}
                )
                assert result.is_error, "unknown case must be refused"
                assert "refused" in result.content[0].text
                result = await session.call_tool(
                    "list_evidence", {"case_id": "@@CASE_ID@@"}
                )
                assert not result.is_error, result.content[0].text
                body = result.content[0].text
                assert "OREOA-DATA-BEGIN" in body and "OREOA-DATA-END" in body
                payload = json.loads(
                    body.split("=== OREOA-DATA-BEGIN (tool=list_evidence) ===")[1]
                    .split("=== OREOA-DATA-END")[0]
                )
                assert payload["evidence"][0]["ev_id"] == "EV-902", payload


asyncio.run(run())
print("SMOKE OK")
'''.replace("@@CASE_ID@@", CASE_ID)


@pytest.fixture(scope="module")
def mcp_image():
    if not image_exists("oreoa/mcp:dev"):
        pytest.skip("image oreoa/mcp:dev not built - run make build")


@pytest.fixture()
def smoke_case():
    from oreoa.manifest_model import Evidence, EvidenceFile, Manifest
    from oreoa.scaffold import scaffold_case

    cases_root = REPO / "cases"
    cases_root.mkdir(exist_ok=True)
    cdir = scaffold_case(cases_root, CASE_ID, "incident")
    manifest = Manifest(
        case_id=CASE_ID,
        evidence=[
            Evidence(
                ev_id="EV-902",
                kind="directory",
                host="SMOKE",
                files=[EvidenceFile(path="evidence/x", sha256="a" * 64, size_bytes=1)],
            )
        ],
    )
    (cdir / "derived").mkdir(exist_ok=True)
    (cdir / "derived" / "manifest.json").write_text(manifest.model_dump_json(indent=2))
    for path in sorted(cdir.rglob("*")):
        os.chmod(path, 0o755 if path.is_dir() else 0o644)
    os.chmod(cdir, 0o755)
    yield cdir
    import shutil

    shutil.rmtree(cdir, ignore_errors=True)


def test_mcp_server_refuses_unknown_case(mcp_image, smoke_case):
    run = subprocess.run(
        compose_cmd()
        + ["run", "--rm", "--no-deps", "--entrypoint", "python", "mcp-evidence", "-c", SCRIPT],
        capture_output=True, text=True, timeout=180, cwd=REPO,
    )
    assert "SMOKE OK" in run.stdout, f"stdout={run.stdout}\nstderr={run.stderr}"
