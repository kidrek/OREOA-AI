"""DuckDB case database: schema, migrations and storage-tier views.

Implementing ``normalized_data_model.md`` exactly, plus the SPEC storage-tier
policy (and its additions ``entities``/``relations``):

- Parquet per evidence per family (``derived/<EV-id>/parquet/<family>.parquet``)
  is the authoritative normalized store and carries ``raw`` verbatim plus the
  ``raw_policy`` marker required by SPEC storage tiers.
- ``case.duckdb`` never stores ``raw``: hot, heavily joined families are
  materialized; massive families are views over
  ``read_parquet(..., union_by_name=true)`` selecting everything except
  ``raw``; ``events`` is materialized (long-form timeline).
- ``schema_version`` tracks applied migrations; migrations run once, inside a
  transaction, in order.
- DuckDB ENUM types are generated from the same closed vocabulary tuples as
  ``oreoa.vocab`` (alignment enforced by tests/unit/test_db.py).

Column order contract (positional INSERTs rely on it): core columns first,
then family-specific columns; in Parquet, ``raw`` sits at the end of the core
block (after ``raw_policy``), so ``parquet minus raw == DuckDB table``.

``duckdb``/``pyarrow`` are lazy imports: the base image ships pydantic+pyyaml
only; workers and (from work-order step 2) mcp-evidence provide their own
requirements.

Timestamps are UTC naive at microsecond precision; unknown is NULL, never
epoch 0 (data-model principle 3).
"""

from __future__ import annotations

from pathlib import Path

from oreoa.vocab import FAMILIES

DB_FILENAME = "case.duckdb"
PARQUET_DIRNAME = "parquet"

MATERIALIZED_FAMILIES: tuple[str, ...] = (
    "executions",
    "persistence",
    "auth_events",
    "accounts",
    "processes",
    "network",
    "installed_software",
    "config_entries",
    "files_of_interest",
    "detections",
    "iocs",
)
VIEW_FAMILIES: tuple[str, ...] = (
    "fs_entries",
    "fs_journal",
    "log_events",
    "registry",
    "browser",
    "user_activity",
)

_CORE_TYPE = "VARCHAR"


def _t(name: str) -> tuple[str, str]:
    return (name, _CORE_TYPE)


ENUM_VOCABS: list[tuple[str, tuple[str, ...]]] = []

CORE_COLUMNS: list[tuple[str, str]] = [
    ("record_id", "VARCHAR"),
    ("case_id", "VARCHAR"),
    ("ev_id", "VARCHAR"),
    ("host", "VARCHAR"),
    ("os", "os_t"),
    ("artifact", "VARCHAR"),
    ("family", "family_t"),
    ("user_name", "VARCHAR"),
    ("user_id", "VARCHAR"),
    ("user_id_type", "user_id_type_t"),
    ("source_tool", "VARCHAR"),
    ("source_path", "VARCHAR"),
    ("source_ref", "VARCHAR"),
    ("parser_version", "VARCHAR"),
    ("mapping_version", "VARCHAR"),
    ("ingested_at", "TIMESTAMP"),
    ("tags", "VARCHAR[]"),
    ("extra", "JSON"),
    ("raw_policy", "raw_policy_t"),
]
RAW_COLUMN: tuple[str, str] = ("raw", "JSON")

FAMILY_COLUMNS: dict[str, list[tuple[str, str]]] = {
    "fs_entries": [
        _t("path"),
        _t("path_norm"),
        _t("name"),
        _t("ext"),
        ("is_dir", "BOOLEAN"),
        ("is_deleted", "BOOLEAN"),
        ("size", "BIGINT"),
        ("inode", "BIGINT"),
        ("parent_inode", "BIGINT"),
        ("ts_created", "TIMESTAMP"),
        ("ts_modified", "TIMESTAMP"),
        ("ts_accessed", "TIMESTAMP"),
        ("ts_metadata_changed", "TIMESTAMP"),
        ("fn_ts_created", "TIMESTAMP"),
        ("fn_ts_modified", "TIMESTAMP"),
        ("fn_ts_accessed", "TIMESTAMP"),
        ("fn_ts_metadata_changed", "TIMESTAMP"),
        _t("owner"),
        _t("mode"),
        ("attributes", "VARCHAR[]"),
        _t("hash_md5"),
        _t("hash_sha1"),
        _t("hash_sha256"),
        ("ads_names", "VARCHAR[]"),
        _t("volume"),
    ],
    "fs_journal": [
        ("ts", "TIMESTAMP"),
        ("op", "fs_journal_op_t"),
        _t("path"),
        _t("path_norm"),
        _t("name"),
        ("inode", "BIGINT"),
        ("parent_inode", "BIGINT"),
        ("usn", "BIGINT"),
        _t("reason_raw"),
        _t("volume"),
    ],
    "log_events": [
        ("ts", "TIMESTAMP"),
        _t("channel"),
        _t("provider"),
        ("event_id", "VARCHAR"),
        ("level", "log_level_t"),
        _t("computer"),
        ("pid", "BIGINT"),
        _t("process_name"),
        _t("message"),
        ("fields", "JSON"),
        ("record_number", "BIGINT"),
    ],
    "executions": [
        ("ts_first", "TIMESTAMP"),
        ("ts_last", "TIMESTAMP"),
        ("run_count", "BIGINT"),
        _t("exe_path"),
        _t("exe_path_norm"),
        _t("exe_name"),
        _t("args"),
        _t("cmdline"),
        _t("cwd"),
        ("pid", "BIGINT"),
        ("ppid", "BIGINT"),
        _t("parent_path"),
        _t("hash_sha1"),
        _t("hash_sha256"),
        _t("signer"),
        ("loaded_files", "VARCHAR[]"),
        _t("volume"),
        ("derived_from", "VARCHAR"),
        ("evidence_type", "exec_evidence_t"),
    ],
    "processes": [
        ("pid", "BIGINT"),
        ("ppid", "BIGINT"),
        _t("name"),
        _t("path"),
        _t("cmdline"),
        ("ts_created", "TIMESTAMP"),
        ("ts_exited", "TIMESTAMP"),
        ("session_id", "BIGINT"),
        ("is_hidden", "BOOLEAN"),
        ("is_injected", "BOOLEAN"),
        _t("injection_detail"),
        ("handles_count", "BIGINT"),
        ("threads_count", "BIGINT"),
        ("dlls", "VARCHAR[]"),
        ("snapshot_ts", "TIMESTAMP"),
    ],
    "persistence": [
        ("mechanism", "mechanism_t"),
        _t("name"),
        _t("location"),
        _t("target_path"),
        _t("target_path_norm"),
        _t("args"),
        ("trigger", "VARCHAR"),
        ("enabled", "BOOLEAN"),
        _t("run_as"),
        ("ts_created", "TIMESTAMP"),
        ("ts_modified", "TIMESTAMP"),
        _t("hash_sha256"),
        _t("signer"),
    ],
    "accounts": [
        _t("full_name"),
        _t("domain"),
        ("groups", "VARCHAR[]"),
        ("is_admin", "BOOLEAN"),
        ("is_disabled", "BOOLEAN"),
        ("is_service", "BOOLEAN"),
        _t("home"),
        _t("shell"),
        ("ts_created", "TIMESTAMP"),
        ("ts_modified", "TIMESTAMP"),
        ("ts_last_logon", "TIMESTAMP"),
        ("ts_password_changed", "TIMESTAMP"),
        ("ts_deleted", "TIMESTAMP"),
        ("logon_count", "BIGINT"),
        ("derived_from", "VARCHAR"),
    ],
    "auth_events": [
        ("ts", "TIMESTAMP"),
        ("event_type", "auth_event_t"),
        _t("logon_type"),
        _t("domain"),
        _t("target_user_name"),
        _t("src_ip"),
        _t("src_host"),
        ("src_port", "BIGINT"),
        _t("dst_host"),
        _t("auth_package"),
        ("outcome", "auth_outcome_t"),
        _t("failure_reason"),
        ("session_id", "BIGINT"),
        ("derived_from", "VARCHAR"),
    ],
    "browser": [
        ("browser", "browser_t"),
        _t("profile"),
        ("entry_type", "browser_entry_t"),
        ("ts", "TIMESTAMP"),
        ("ts_end", "TIMESTAMP"),
        _t("url"),
        _t("domain"),
        _t("title"),
        _t("referrer"),
        _t("transition"),
        ("visit_count", "BIGINT"),
        _t("target_path"),
        _t("target_path_norm"),
        ("size", "BIGINT"),
        _t("mime"),
        _t("state"),
        _t("extension_id"),
        _t("extension_name"),
    ],
    "user_activity": [
        ("activity_type", "activity_t"),
        ("ts", "TIMESTAMP"),
        ("ts_desc", "ts_desc_t"),
        _t("target_path"),
        _t("target_path_norm"),
        _t("target_name"),
        ("target_exists", "BOOLEAN"),
        ("target_size", "BIGINT"),
        _t("source_app"),
        _t("volume_serial"),
        _t("volume_label"),
        _t("machine_id"),
        _t("drive_type"),
        _t("net_share"),
    ],
    "network": [
        ("entry_type", "net_entry_t"),
        ("ts", "TIMESTAMP"),
        ("ts_end", "TIMESTAMP"),
        _t("proto"),
        _t("src_ip"),
        ("src_port", "BIGINT"),
        _t("dst_ip"),
        ("dst_port", "BIGINT"),
        _t("domain"),
        _t("state"),
        ("pid", "BIGINT"),
        _t("process_name"),
        ("bytes_in", "BIGINT"),
        ("bytes_out", "BIGINT"),
        _t("ssid"),
        _t("bssid"),
        _t("interface"),
        _t("direction"),
    ],
    "installed_software": [
        _t("name"),
        _t("version"),
        _t("publisher"),
        ("ts_installed", "TIMESTAMP"),
        ("ts_modified", "TIMESTAMP"),
        _t("install_path"),
        _t("install_path_norm"),
        ("source", "sw_source_t"),
        ("is_removed", "BOOLEAN"),
    ],
    "registry": [
        ("hive", "hive_t"),
        _t("key_path"),
        _t("key_path_norm"),
        _t("value_name"),
        _t("value_type"),
        _t("value_data"),
        ("value_data_raw", "BLOB"),
        ("ts_last_write", "TIMESTAMP"),
        ("is_deleted", "BOOLEAN"),
    ],
    "config_entries": [
        _t("file_path"),
        _t("file_path_norm"),
        _t("section"),
        _t("key"),
        _t("value"),
        ("ts_modified", "TIMESTAMP"),
        ("is_default", "BOOLEAN"),
    ],
    "files_of_interest": [
        _t("path"),
        _t("path_norm"),
        ("size", "BIGINT"),
        _t("hash_md5"),
        _t("hash_sha1"),
        _t("hash_sha256"),
        _t("mime"),
        _t("magic"),
        ("is_signed", "BOOLEAN"),
        _t("signer"),
        ("signature_valid", "BOOLEAN"),
        ("entropy", "DOUBLE"),
        ("yara_matches", "VARCHAR[]"),
        ("strings_of_interest", "VARCHAR[]"),
        _t("stored_at"),
        ("ts_created", "TIMESTAMP"),
        ("ts_modified", "TIMESTAMP"),
    ],
    "detections": [
        ("ts", "TIMESTAMP"),
        ("engine", "engine_t"),
        _t("rule_id"),
        _t("rule_name"),
        _t("rule_version"),
        ("level", "det_level_t"),
        ("technique_ids", "VARCHAR[]"),
        ("tactic_ids", "VARCHAR[]"),
        ("dfiq_question_ids", "VARCHAR[]"),
        ("matched_record_ids", "VARCHAR[]"),
        ("matched_family", "family_t"),
        _t("summary"),
        ("status", "det_status_t"),
        _t("lead_id"),
        _t("finding_id"),
        ("score", "DOUBLE"),
        ("score_factors", "JSON"),
    ],
    "iocs": [
        _t("value"),
        ("ioc_type", "ioc_type_t"),
        _t("source"),
        ("ts_added", "TIMESTAMP"),
        _t("added_by"),
        ("confidence", "confidence_t"),
        ("first_seen_record_id", "VARCHAR"),
        _t("notes"),
    ],
}

EVENTS_COLUMNS: list[tuple[str, str]] = [
    ("ts", "TIMESTAMP"),
    ("ts_desc", "ts_desc_t"),
    ("family", "family_t"),
    ("record_id", "VARCHAR"),
    ("host", "VARCHAR"),
    ("user_name", "VARCHAR"),
    ("summary", "VARCHAR"),
    ("path_norm", "VARCHAR"),
    ("technique_ids", "VARCHAR[]"),
    ("ev_id", "VARCHAR"),
    ("artifact", "VARCHAR"),
    ("source_tool", "VARCHAR"),
]
ENTITIES_COLUMNS: list[tuple[str, str]] = [
    ("entity_id", "VARCHAR"),
    ("type", "entity_type_t"),
    ("value", "VARCHAR"),
    ("first_seen", "TIMESTAMP"),
    ("last_seen", "TIMESTAMP"),
]
RELATIONS_COLUMNS: list[tuple[str, str]] = [
    ("src_entity_id", "VARCHAR"),
    ("dst_entity_id", "VARCHAR"),
    ("relation", "relation_t"),
    ("ts", "TIMESTAMP"),
    ("record_id", "VARCHAR"),
]
HOSTS_COLUMNS: list[tuple[str, str]] = [
    _t("host"),
    ("os", "os_t"),
    _t("os_version"),
    _t("build"),
    _t("arch"),
    _t("domain"),
    _t("tz"),
    ("clock_skew_seconds", "BIGINT"),
    ("ips", "VARCHAR[]"),
    ("ev_ids", "VARCHAR[]"),
    _t("role"),
    ("criticity", "criticity_t"),
]
EVIDENCE_COLUMNS: list[tuple[str, str]] = [
    _t("ev_id"),
    _t("host"),
    ("kind", "evidence_kind_t"),
    _t("sha256"),
    ("collected_at", "TIMESTAMP"),
    ("time_range_start", "TIMESTAMP"),
    ("time_range_end", "TIMESTAMP"),
]


def _build_enum_registry() -> None:
    from oreoa import vocab

    pairs: list[tuple[str, tuple[str, ...]]] = [
        ("os_t", vocab.OS),
        ("family_t", FAMILIES),
        ("user_id_type_t", vocab.USER_ID_TYPE),
        ("raw_policy_t", vocab.RAW_POLICY),
        ("ts_desc_t", vocab.TS_DESC),
        ("fs_journal_op_t", vocab.FS_JOURNAL_OP),
        ("log_level_t", vocab.LOG_LEVEL),
        ("exec_evidence_t", vocab.EXECUTION_EVIDENCE_TYPE),
        ("mechanism_t", vocab.PERSISTENCE_MECHANISM),
        ("auth_event_t", vocab.AUTH_EVENT_TYPE),
        ("auth_outcome_t", vocab.AUTH_OUTCOME),
        ("browser_t", vocab.BROWSER),
        ("browser_entry_t", vocab.BROWSER_ENTRY_TYPE),
        ("activity_t", vocab.USER_ACTIVITY_TYPE),
        ("net_entry_t", vocab.NETWORK_ENTRY_TYPE),
        ("sw_source_t", vocab.SOFTWARE_SOURCE),
        ("hive_t", vocab.REGISTRY_HIVE),
        ("engine_t", vocab.DETECTION_ENGINE),
        ("det_level_t", vocab.DETECTION_LEVEL),
        ("det_status_t", vocab.DETECTION_STATUS),
        ("ioc_type_t", vocab.IOC_TYPE),
        ("confidence_t", vocab.CONFIDENCE),
        ("criticity_t", vocab.CRITICITY),
        ("entity_type_t", vocab.ENTITY_TYPE),
        ("relation_t", vocab.RELATION),
        ("evidence_kind_t", vocab.EVIDENCE_KIND),
    ]
    names = [name for name, _ in pairs]
    if len(names) != len(set(names)):
        raise RuntimeError("duplicate DuckDB enum type name")
    enum_types = set(names)
    for family, columns in list(FAMILY_COLUMNS.items()) + [
        ("events", EVENTS_COLUMNS),
        ("entities", ENTITIES_COLUMNS),
        ("relations", RELATIONS_COLUMNS),
        ("hosts", HOSTS_COLUMNS),
        ("evidence", EVIDENCE_COLUMNS),
    ]:
        for _, col_type in columns:
            base = col_type.rstrip("[]")
            if base.endswith("_t") and base not in enum_types:
                raise RuntimeError(f"{family}: unknown enum type {col_type}")
    for _, col_type in CORE_COLUMNS:
        base = col_type.rstrip("[]")
        if base.endswith("_t") and base not in enum_types:
            raise RuntimeError(f"core: unknown enum type {col_type}")
    ENUM_VOCABS.extend(pairs)


_build_enum_registry()


def _quote(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def _table_columns(family: str) -> list[tuple[str, str]]:
    if family in FAMILY_COLUMNS:
        return CORE_COLUMNS + FAMILY_COLUMNS[family]
    if family == "events":
        return EVENTS_COLUMNS
    if family == "entities":
        return ENTITIES_COLUMNS
    if family == "relations":
        return RELATIONS_COLUMNS
    if family == "hosts":
        return HOSTS_COLUMNS
    if family == "evidence":
        return EVIDENCE_COLUMNS
    raise KeyError(family)


def parquet_columns(family: str) -> list[tuple[str, str]]:
    """Parquet row schema: core (with raw_policy, then raw) + family columns."""
    return CORE_COLUMNS + [RAW_COLUMN] + FAMILY_COLUMNS[family]


def _create_table_sql(table: str, columns: list[tuple[str, str]], not_null: tuple[str, ...] = ()) -> str:
    defs = []
    for name, col_type in columns:
        suffix = " NOT NULL" if name in not_null else ""
        defs.append(f"{_quote(name)} {col_type}{suffix}")
    return f"CREATE TABLE {_quote(table)} ({', '.join(defs)})"


def _enum_ddl() -> list[str]:
    return [
        f"CREATE TYPE {_quote(enum)} AS ENUM ({', '.join(repr(v) for v in values)})"
        for enum, values in ENUM_VOCABS
    ]


MIGRATION_V1_TABLES: list[tuple[str, list[tuple[str, str]], tuple[str, ...]]] = [
    (family, _table_columns(family), ("record_id", "case_id", "ev_id"))
    for family in MATERIALIZED_FAMILIES
] + [
    ("events", EVENTS_COLUMNS, ("record_id", "ev_id")),
    ("entities", ENTITIES_COLUMNS, ("entity_id",)),
    ("relations", RELATIONS_COLUMNS, ()),
    ("hosts", HOSTS_COLUMNS, ("host",)),
    ("evidence", EVIDENCE_COLUMNS, ("ev_id",)),
]

MIGRATIONS: list[tuple[int, str, list[str]]] = [
    (
        1,
        "v1: enums + materialized families + events/entities/relations + hosts/evidence "
        "(normalized_data_model.md + SPEC storage tiers)",
        _enum_ddl()
        + [_create_table_sql(table, cols, not_null) for table, cols, not_null in MIGRATION_V1_TABLES],
    )
]

SCHEMA_VERSION = MIGRATIONS[-1][0]


def db_path(case_dir: Path) -> Path:
    return Path(case_dir) / "derived" / DB_FILENAME


def parquet_path(case_dir: Path, ev_id: str, family: str) -> Path:
    if family not in FAMILIES:
        raise KeyError(f"unknown family {family!r}")
    return Path(case_dir) / "derived" / ev_id / PARQUET_DIRNAME / f"{family}.parquet"


def parquet_glob(case_dir: Path, family: str) -> str:
    return (Path(case_dir) / "derived" / "*" / PARQUET_DIRNAME / f"{family}.parquet").as_posix()


def apply_migrations(con) -> None:
    con.execute(
        "CREATE TABLE IF NOT EXISTS schema_version ("
        "version INTEGER NOT NULL, name VARCHAR, applied_at TIMESTAMP)"
    )
    applied = {row[0] for row in con.execute("SELECT version FROM schema_version").fetchall()}
    for version, name, statements in MIGRATIONS:
        if version in applied:
            continue
        con.execute("BEGIN TRANSACTION")
        try:
            for statement in statements:
                con.execute(statement)
            con.execute("INSERT INTO schema_version VALUES (?, ?, now())", [version, name])
            con.execute("COMMIT")
        except Exception:
            con.execute("ROLLBACK")
            raise


def ensure_views(con, case_dir: Path) -> dict[str, bool]:
    """Create the massive-family tier views over Parquet (SPEC storage tiers).

    A view is created only when at least one Parquet file for the family
    exists (read_parquet binds at creation time); ``CREATE OR REPLACE`` makes
    re-running after new ingests safe. Returns family -> created.
    """
    case_dir = Path(case_dir)
    created: dict[str, bool] = {}
    for family in VIEW_FAMILIES:
        glob = parquet_glob(case_dir, family)
        has_files = bool(list(case_dir.glob(f"derived/*/parquet/{family}.parquet")))
        if not has_files:
            created[family] = False
            continue
        literal = glob.replace("'", "''")
        con.execute(
            f"CREATE OR REPLACE VIEW {_quote(family)} AS "
            f"SELECT * EXCLUDE (raw) FROM read_parquet('{literal}', union_by_name=true)"
        )
        created[family] = True
    return created


def connect(case_dir: Path, read_only: bool = False):
    """Open (and migrate) the case DuckDB; returns a duckdb connection.

    ``read_only=True`` skips migrations and view creation: callers get the
    schema as written by the pipeline (mcp servers, A1 write matrix).
    """
    import duckdb

    case_dir = Path(case_dir)
    if not read_only:
        (case_dir / "derived").mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(db_path(case_dir)), read_only=read_only)
    if not read_only:
        apply_migrations(con)
        ensure_views(con, case_dir)
    return con


def _insert_sql(family: str, source: str) -> tuple[str, list]:
    columns = _table_columns(family)
    names = [name for name, _ in columns]
    enum_types = {enum for enum, _ in ENUM_VOCABS}
    select_parts = []
    for name, col_type in columns:
        base = col_type.rstrip("[]")
        if base in enum_types or col_type == "JSON":
            select_parts.append(f'CAST({_quote(name)} AS {col_type}) AS {_quote(name)}')
        else:
            select_parts.append(_quote(name))
    literal = str(source).replace("'", "''")
    sql = (
        f"INSERT INTO {_quote(family)} ({', '.join(_quote(n) for n in names)}) "
        f"SELECT {', '.join(select_parts)} FROM read_parquet('{literal}', union_by_name=true)"
    )
    return sql, names


def load_evidence_family(con, case_dir: Path, ev_id: str, family: str) -> int:
    """Load one evidence's Parquet into a materialized family (idempotent).

    Delete-then-insert by ``ev_id``: re-ingesting the same evidence replaces
    its rows (same record_ids). Returns the inserted row count.
    """
    if family not in MATERIALIZED_FAMILIES:
        raise ValueError(f"{family!r} is not a materialized family")
    source = parquet_path(case_dir, ev_id, family)
    if not source.exists():
        raise FileNotFoundError(f"missing Parquet for {ev_id}/{family}: {source}")
    con.execute("DELETE FROM " + _quote(family) + " WHERE ev_id = ?", [ev_id])
    sql, _ = _insert_sql(family, source)
    con.execute(sql)
    (count,) = con.execute(
        f"SELECT count(*) FROM {_quote(family)} WHERE ev_id = ?", [ev_id]
    ).fetchone()
    return int(count)


def write_parsed_rows(case_dir: Path, ev_id: str, rows_by_family: dict[str, list[dict]]) -> None:
    """Persist parsed rows for one evidence (shared by the fast-lane
    parsers, S1.6 Velociraptor / S2.1 KAPE):

    - one Parquet file per family (authoritative tier, ``raw`` included);
    - materialized families loaded into DuckDB (idempotent, delete-then-
      insert by ``ev_id``); view families get their Parquet-backed views
      refreshed.
    """
    for family, rows in sorted(rows_by_family.items()):
        write_parquet(case_dir, ev_id, family, rows)
    con = connect(case_dir)
    try:
        for family, _rows in sorted(rows_by_family.items()):
            if family in MATERIALIZED_FAMILIES:
                load_evidence_family(con, case_dir, ev_id, family)
        ensure_views(con, case_dir)
    finally:
        con.close()


def find_raw(con, case_dir: Path, family: str, record_ids: list[str]) -> dict[str, str]:
    """Resolve ``raw`` records from the authoritative Parquet (SPEC get_raw).

    Reads ``derived/<EV-id>/parquet/<family>.parquet`` across the case and
    returns ``record_id -> raw JSON string`` for the requested ids. The
    20-record cap and the case-type gate are enforced by the caller
    (mcp-evidence, work-order step 2).
    """
    if not record_ids:
        return {}
    glob = parquet_glob(case_dir, family)
    if not list(Path(case_dir).glob(f"derived/*/parquet/{family}.parquet")):
        return {}
    literal = glob.replace("'", "''")
    placeholders = ", ".join("?" for _ in record_ids)
    rows = con.execute(
        f"SELECT record_id, raw FROM read_parquet('{literal}', union_by_name=true) "
        f"WHERE record_id IN ({placeholders})",
        record_ids,
    ).fetchall()
    return {row[0]: row[1] for row in rows}


def parquet_arrow_schema(family: str):
    """pyarrow schema of a family's Parquet file (corpus generators, tests)."""
    import pyarrow as pa

    arrow_map = {
        "VARCHAR": pa.string(),
        "TIMESTAMP": pa.timestamp("us"),
        "BOOLEAN": pa.bool_(),
        "BIGINT": pa.int64(),
        "DOUBLE": pa.float64(),
        "JSON": pa.string(),
        "BLOB": pa.binary(),
        "VARCHAR[]": pa.list_(pa.string()),
    }
    enum_types = {enum for enum, _ in ENUM_VOCABS}
    fields = []
    for name, col_type in parquet_columns(family):
        base = col_type.rstrip("[]")
        if base in enum_types:
            arrow_type = pa.string()
        else:
            arrow_type = arrow_map[col_type]
        fields.append(pa.field(name, arrow_type))
    return pa.schema(fields)


def write_parquet(case_dir: Path, ev_id: str, family: str, rows: list[dict]) -> Path:
    """Write ``derived/<EV-id>/parquet/<family>.parquet`` from row dicts.

    Values must match ``parquet_arrow_schema(family)``; ``raw`` carries the
    original record verbatim (NULL for lossless mappings). Returns the path.
    """
    import pyarrow as pa
    import pyarrow.parquet as pq

    schema = parquet_arrow_schema(family)
    columns = [name for name, _ in parquet_columns(family)]
    data = {name: [row.get(name) for row in rows] for name in columns}
    table = pa.table(data, schema=schema)
    target = parquet_path(case_dir, ev_id, family)
    target.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(table, target)
    return target
