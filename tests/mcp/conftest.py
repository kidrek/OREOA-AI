"""Shared harness for the T3 MCP contract tests (in-process, no network).

The servers are exercised over the real streamable-HTTP transport using an
ASGI in-transport client (httpx2 ASGITransport): same code path as compose,
no sockets. ``build_case`` scaffolds a case and populates its DuckDB +
Parquet tier with fixture rows.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

import httpx2
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from oreoa import db, mcp_server  # noqa: E402
from oreoa.manifest_model import (  # noqa: E402
    Evidence,
    EvidenceFile,
    Manifest,
)
from oreoa.normalize import record_id  # noqa: E402
from oreoa.scaffold import scaffold_case  # noqa: E402

SHA = "b" * 64
CASE_ID = "2026-09-INC-420"
DATA_BEGIN = "=== OREOA-DATA-BEGIN (tool={tool}) ==="
DATA_END = "=== OREOA-DATA-END ==="

CORE = [
    "record_id", "case_id", "ev_id", "host", "os", "artifact", "family",
    "user_name", "user_id", "user_id_type", "source_tool", "source_path",
    "source_ref", "parser_version", "mapping_version", "ingested_at",
    "tags", "extra", "raw_policy", "raw",
]


def core_row(rid: str, family: str, **overrides) -> dict:
    row = {name: None for name in CORE}
    row.update(
        record_id=rid,
        case_id=CASE_ID,
        ev_id="EV-001",
        host="WKS-01",
        os="windows",
        artifact="custom:test",
        family=family,
        source_tool="manual",
        source_ref="fixture",
        parser_version="1",
        mapping_version="1",
        raw_policy="kept",
    )
    row.update(overrides)
    return row


@pytest.fixture()
def case_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("OREOA_CASES", str(tmp_path))
    monkeypatch.setenv("OREOA_KNOWLEDGE", str(tmp_path / "knowledge"))
    cdir = scaffold_case(tmp_path, CASE_ID, "incident")
    (cdir / "derived").mkdir(exist_ok=True)
    manifest = Manifest(
        case_id=CASE_ID,
        evidence=[
            Evidence(
                ev_id="EV-001",
                kind="directory",
                host="WKS-01",
                files=[EvidenceFile(path="evidence/ev1", sha256=SHA, size_bytes=10)],
            )
        ],
    )
    (cdir / "derived" / "manifest.json").write_text(manifest.model_dump_json(indent=2))
    os.chmod(cdir / "evidence", 0o555)
    populate_db(cdir)
    return cdir


def populate_db(cdir: Path) -> None:
    """Parquet tier (with raw) + DuckDB: events rows, detections, fs_entries."""
    base = datetime(2026, 9, 1, 8, 0, 0)

    raw_ids = {
        "raw1": record_id("EV-001", "custom:test", "raw-1"),
        "raw2": record_id("EV-001", "custom:test", "raw-2"),
    }
    long_summary = "X" * 700

    events_rows = []
    for i in range(510):
        summary = long_summary if i == 0 else f"event {i}"
        if i == 0:
            rid = raw_ids["raw1"]
        elif i == 1:
            rid = raw_ids["raw2"]
        else:
            rid = rid_for(i)
        events_rows.append(
            {
                "ts": base + timedelta(minutes=i),
                "ts_desc": "logged",
                "family": "log_events",
                "record_id": rid,
                "host": "WKS-01",
                "user_name": "jdoe",
                "summary": summary,
                "path_norm": f"c:/users/jdoe/file{i}.log",
                "technique_ids": ["T1059.001"] if i % 10 == 0 else [],
                "ev_id": "EV-001",
                "artifact": "custom:test",
                "source_tool": "manual",
            }
        )
    (cdir / "derived" / "EV-001").mkdir(exist_ok=True)
    (cdir / "derived" / "EV-001" / "parquet").mkdir(exist_ok=True)
    parquet_rows = []
    for i, row in enumerate(events_rows):
        prow = core_row(row["record_id"], "log_events", source_ref=f"raw-{i}")
        prow["raw"] = json.dumps({"orig": i, "summary": row["summary"]})
        parquet_rows.append(prow)
    db.write_parquet(cdir, "EV-001", "log_events", parquet_rows)

    detections = []
    for i in range(3):
        row = core_row(rid_for(1000 + i), "detections", source_ref=f"det-{i}")
        row.update(
            {
                "ts": base + timedelta(hours=i),
                "engine": "sigma",
                "rule_id": f"R-{i}",
                "rule_name": f"rule {i}",
                "level": "high" if i == 0 else "low",
                "matched_record_ids": [rid_for(i)],
                "matched_family": "log_events",
                "summary": f"detection {i}",
                "status": "new",
                "score": 90.0 - i,
                "score_factors": json.dumps({"base": i}),
            }
        )
        detections.append(row)
    db.write_parquet(cdir, "EV-001", "detections", detections)

    con = db.connect(cdir)
    try:
        columns = list(events_rows[0].keys())
        placeholders = ", ".join("?" for _ in columns)
        names = ", ".join('"' + c + '"' for c in columns)
        con.executemany(
            f"INSERT INTO events ({names}) VALUES ({placeholders})",
            [[row[c] for c in columns] for row in events_rows],
        )
        db.load_evidence_family(con, cdir, "EV-001", "detections")
    finally:
        con.close()


def rid_for(i: int) -> str:
    return record_id("EV-001", "custom:test", f"fixture-{i}")


@pytest.fixture()
def evidence_server():
    return mcp_server.build("evidence")


@pytest.fixture()
def case_server():
    return mcp_server.build("case")


@pytest.fixture()
def jobs_server():
    return mcp_server.build("jobs")


@pytest.fixture()
def knowledge_server():
    return mcp_server.build("knowledge")


def call_tool(server, tool: str, args: dict) -> tuple[bool, str, dict | None]:
    """Call a tool over the real HTTP transport (in-process ASGI).

    Returns (is_error, text, parsed_json_between_markers_or_None).
    """
    from mcp.client.session import ClientSession
    from mcp.client.streamable_http import streamable_http_client
    from mcp.server.transport_security import TransportSecuritySettings

    app = server.streamable_http_app(
        host="127.0.0.1",
        stateless_http=True,
        transport_security=TransportSecuritySettings(
            enable_dns_rebinding_protection=True, allowed_hosts=["testserver"]
        ),
    )

    async def run() -> tuple[bool, str]:
        client = httpx2.AsyncClient(
            transport=httpx2.ASGITransport(app=app), timeout=30
        )
        async with server.session_manager.run():
            async with streamable_http_client(
                "http://testserver/mcp", http_client=client
            ) as (read_stream, write_stream):
                async with ClientSession(read_stream, write_stream) as session:
                    result = await session.call_tool(tool, args)
                    text = result.content[0].text if result.content else ""
                    return bool(result.is_error), text

    is_error, text = asyncio.run(run())
    payload = None
    if not is_error and DATA_BEGIN.format(tool=tool) in text:
        body = text.split(DATA_BEGIN.format(tool=tool), 1)[1]
        body = body.split(DATA_END, 1)[0].strip()
        payload = json.loads(body)
    return is_error, text, payload
