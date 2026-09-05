"""T1: fast-lane KAPE quick-parser end-to-end (work-order step 2.1).

scenario -> KAPE archive -> parse_archive -> Parquet + DuckDB, all in-process
(no container). Covers: family counts, key planted rows (H-AF-003
timestomping SI/FN skew, H-DC-002 USN create/delete, amcache executions),
deterministic + unique record ids, idempotent re-parse, lossless raw policy,
zip-slip refusal, unmapped CSV report, clean-host yardstick, and the SPEC
round-trip contract (normalized_data_model.md: every source column
re-derivable from the mapped columns + extra for lossless mappings).
"""

from __future__ import annotations

import csv
import io
import json
import sys
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from oreoa import db  # noqa: E402
from oreoa.corpus_gen import kape  # noqa: E402
from oreoa.corpus_gen.scenario import load_scenarios  # noqa: E402
from oreoa.mappings import load_mappings  # noqa: E402
from oreoa.normalize import record_id as compute_record_id  # noqa: E402
from oreoa.parse_kape import CSV_ARTIFACTS, parse_archive  # noqa: E402
from oreoa.scaffold import scaffold_case  # noqa: E402

CASE_ID = "2026-09-INC-410"
CLEAN_CASE_ID = "2026-09-INC-411"
MAPPINGS = load_mappings(ROOT / "mappings")


def _build_archive(scenario_name: str, out: Path) -> Path:
    scenario = next(s for s in load_scenarios(ROOT / "corpus" / "scenarios") if s.name == scenario_name)
    kape.build_archive(scenario, out)
    return out


def _source_rows(archive: Path, entry: str) -> list[dict[str, str]]:
    with zipfile.ZipFile(archive) as zf:
        payload = zf.read(entry).decode("utf-8")
    return list(csv.DictReader(io.StringIO(payload, newline="")))


def _kape_rows(case_dir: Path, ev_id: str, family: str) -> dict[str, dict]:
    con = db.connect(case_dir)
    try:
        # DuckDB tables = core columns without ``raw`` + family columns
        # (decision 7); the authoritative Parquet keeps raw.
        columns = [name for name, _ in db._table_columns(family)]
        rows = con.execute(
            f"select {', '.join(columns)} from {family} where ev_id = ? and source_tool = 'kape'",
            [ev_id],
        ).fetchall()
        return {r[columns.index("source_ref")]: dict(zip(columns, r)) for r in rows}
    finally:
        con.close()


@pytest.fixture(scope="module")
def archive(tmp_path_factory):
    return _build_archive(
        "win-workstation-01", tmp_path_factory.mktemp("corpus") / "win-workstation-01.kape.zip"
    )


@pytest.fixture()
def case(tmp_path, archive):
    cdir = scaffold_case(tmp_path, CASE_ID, "incident")
    evidence_dir = cdir / "evidence"
    evidence_dir.chmod(0o755)
    target = evidence_dir / "win-workstation-01.kape.zip"
    target.write_bytes(archive.read_bytes())
    evidence_dir.chmod(0o555)
    return cdir, target


def test_parse_families_and_counts(case):
    cdir, target = case
    details = parse_archive(target, CASE_ID, "EV-001", "WKS-042", cdir)
    assert details["unmapped_artifacts"] == []
    assert details["parser"] == "kape/1.0.0"
    families = details["families"]
    assert families.get("fs_entries", 0) > 0
    assert families.get("fs_journal", 0) > 0
    assert families.get("executions", 0) > 0

    con = db.connect(cdir)
    try:
        # H-DC-002: docs.7z create + delete in the USN module output
        assert con.execute(
            "select count(*) from fs_journal where name = 'docs.7z' and op in ('create', 'delete')"
        ).fetchone()[0] == 2
        # amcache executions loaded into DuckDB
        assert con.execute(
            "select count(*) from executions where evidence_type = 'amcache'"
        ).fetchone()[0] == families["executions"]
    finally:
        con.close()


def test_timestomping_si_fn_skew_planted(case):
    """H-AF-003 (step2 lane): upd.exe SI set forged to 2019, FN set keeps
    the real 2026 times - the MFT quick parser exposes both sets."""
    cdir, target = case
    parse_archive(target, CASE_ID, "EV-001", "WKS-042", cdir)
    con = db.connect(cdir)
    try:
        rows = con.execute(
            "select path, ts_created, fn_ts_created from fs_entries where name = 'upd.exe'"
        ).fetchall()
    finally:
        con.close()
    assert len(rows) == 1
    path, ts_created, fn_ts_created = rows[0]
    assert path.endswith("upd.exe")
    assert ts_created.year == 2019, "SI set must carry the forged time"
    assert fn_ts_created.year == 2026, "FN set must keep the real time"


def test_usn_ops_projected_on_closed_vocab(case):
    cdir, target = case
    parse_archive(target, CASE_ID, "EV-001", "WKS-042", cdir)
    con = db.connect(cdir)
    try:
        rows = con.execute(
            "select op, reason_raw from fs_journal where source_tool = 'kape' order by usn"
        ).fetchall()
    finally:
        con.close()
    assert {op for op, _ in rows} <= {"create", "delete", "modify", "truncate", "other"}
    for op, reason_raw in rows:
        if reason_raw == "File Create":
            assert op == "create"
        if reason_raw == "File Delete":
            assert op == "delete"
        if reason_raw == "Data Overwrite":
            assert op == "modify"


def test_record_ids_deterministic_and_unique(case):
    cdir, target = case
    first = parse_archive(target, CASE_ID, "EV-001", "WKS-042", cdir)
    con = db.connect(cdir)
    try:
        rows = con.execute(
            "select record_id, source_ref from executions order by record_id"
        ).fetchall()
    finally:
        con.close()
    assert len({r[0] for r in rows}) == len(rows)
    for record_id, source_ref in rows:
        assert record_id == compute_record_id("EV-001", "WindowsAmcache", source_ref)
    parse_archive(target, CASE_ID, "EV-001", "WKS-042", cdir)
    con = db.connect(cdir)
    try:
        rows2 = con.execute("select record_id from executions order by record_id").fetchall()
        assert [r[0] for r in rows] == [r[0] for r in rows2]
        assert con.execute("select count(*) from executions").fetchone()[0] == first["families"]["executions"]
    finally:
        con.close()


def test_raw_policy_lossless(case):
    cdir, target = case
    parse_archive(target, CASE_ID, "EV-001", "WKS-042", cdir)
    con = db.connect(cdir)
    try:
        for family in ("fs_entries", "fs_journal", "executions"):
            count, = con.execute(
                f"select count(*) from {family} where source_tool = 'kape' and raw_policy != 'omitted_lossless'"
            ).fetchone()
            assert count == 0, family
        sample = con.execute(
            "select record_id from executions where evidence_type = 'amcache' limit 1"
        ).fetchone()[0]
        raws = db.find_raw(con, cdir, "executions", [sample])
        assert raws.get(sample) is None, "lossless: raw omitted from Parquet"
    finally:
        con.close()


def test_zip_slip_entry_refused(case, tmp_path):
    cdir, target = case
    poisoned = tmp_path / "poisoned.zip"
    with zipfile.ZipFile(target) as src, zipfile.ZipFile(poisoned, "w") as dst:
        for name in src.namelist():
            dst.writestr(name, src.read(name))
        dst.writestr("Module_Output/../../evil.csv", "A\n1\n")
    with pytest.raises(ValueError, match="zip-slip"):
        parse_archive(poisoned, CASE_ID, "EV-001", "WKS-042", cdir)


def test_unmapped_csv_reported(case):
    cdir, target = case
    details = parse_archive(target, CASE_ID, "EV-001", "WKS-042", cdir, mappings={})
    assert sorted(details["unmapped_artifacts"]) == sorted(CSV_ARTIFACTS)
    assert details["rows"] == 0


def test_unknown_entry_warns(case, tmp_path):
    cdir, target = case
    extra = tmp_path / "extra.zip"
    with zipfile.ZipFile(target) as src, zipfile.ZipFile(extra, "w") as dst:
        for name in src.namelist():
            dst.writestr(name, src.read(name))
        dst.writestr("Module_Output/Unknown/Other.csv", "A\n1\n")
    details = parse_archive(extra, CASE_ID, "EV-001", "WKS-042", cdir)
    assert any("Module_Output/Unknown/Other.csv" in w for w in details["warnings"])


def test_clean_host_yardstick(tmp_path):
    """clean-host-01: parses with its single known amcache entry (svchost.exe,
    baseline software) and one USN modify - zero attack signal (T0 FP yardstick)."""
    archive = _build_archive("clean-host-01", tmp_path / "clean-host-01.kape.zip")
    cdir = scaffold_case(tmp_path, CLEAN_CASE_ID, "incident")
    evidence_dir = cdir / "evidence"
    evidence_dir.chmod(0o755)
    target = evidence_dir / "clean-host-01.kape.zip"
    target.write_bytes(archive.read_bytes())
    evidence_dir.chmod(0o555)

    details = parse_archive(target, CLEAN_CASE_ID, "EV-001", "WKS-077", cdir)
    con = db.connect(cdir)
    try:
        assert con.execute(
            "select count(*) from executions where evidence_type = 'amcache'"
        ).fetchone()[0] == 1
        assert con.execute(
            "select exe_name from executions where evidence_type = 'amcache'"
        ).fetchone()[0] == "svchost.exe"
        assert con.execute(
            "select count(*) from fs_journal where op = 'delete'"
        ).fetchone()[0] == 0
        assert con.execute(
            "select count(*) from fs_entries where name = 'budget.xlsx'"
        ).fetchone()[0] == 1
    finally:
        con.close()
    assert details["families"]["fs_journal"] == 1


def test_round_trip_per_mapping(case):
    """SPEC normalized_data_model.md: for lossless mappings the source record
    is re-derivable from the mapped columns + extra. Rebuild each source CSV
    row from its normalized row and compare verbatim."""
    cdir, target = case
    parse_archive(target, CASE_ID, "EV-001", "WKS-042", cdir)

    def iso(ts) -> str:
        return ts.strftime("%Y-%m-%dT%H:%M:%S.%fZ") if ts is not None else ""

    def parent_of(path: str, name: str) -> str:
        if path == name:
            return ""
        assert path.endswith("\\" + name), (path, name)
        return path[: -(len(name) + 1)]

    for entry, artifact in sorted(CSV_ARTIFACTS.items()):
        mapping = MAPPINGS[artifact]
        assert mapping.lossless, artifact
        parsed = _kape_rows(cdir, "EV-001", mapping.family)
        for index, source in enumerate(_source_rows(target, entry), start=1):
            row = parsed[f"csv:{entry}:{index}"]
            if artifact == "kape.MFT":
                rebuilt = {
                    "RecordNumber": str(row["inode"]),
                    "FileName": row["name"],
                    "ParentPath": parent_of(row["path"], row["name"]),
                    "IsDirectory": "1" if row["is_dir"] else "0",
                    "FileSize": str(row["size"]),
                    "Attributes": (row["attributes"] or [""])[0],
                    "SI_Created": iso(row["ts_created"]),
                    "SI_Modified": iso(row["ts_modified"]),
                    "SI_Accessed": iso(row["ts_accessed"]),
                    "SI_MFT_Changed": iso(row["ts_metadata_changed"]),
                    "FN_Created": iso(row["fn_ts_created"]),
                    "FN_Modified": iso(row["fn_ts_modified"]),
                    "FN_Accessed": iso(row["fn_ts_accessed"]),
                    "FN_MFT_Changed": iso(row["fn_ts_metadata_changed"]),
                }
            elif artifact == "kape.USN":
                rebuilt = {
                    "USN": str(row["usn"]),
                    "Timestamp": iso(row["ts"]),
                    "FileName": row["name"],
                    "ParentPath": parent_of(row["path"], row["name"]),
                    "Reason": row["reason_raw"],
                }
            else:
                extra = json.loads(row["extra"])
                rebuilt = {
                    "KeyPath": extra.get("KeyPath", ""),
                    "Name": row["exe_name"],
                    "Path": row["exe_path"],
                    "Sha256": row["hash_sha256"],
                    "Size": extra.get("Size", ""),
                    "LastWriteTimestamp": iso(row["ts_last"]),
                    "Signer": row["signer"],
                }
            assert rebuilt == source, f"{artifact} row {index}: round-trip mismatch"
