"""T1: fast-lane Velociraptor parser end-to-end (work-order step 1.6).

scenario -> archive -> parse_archive -> Parquet + DuckDB, all in-process
(no container). Covers: family counts, key planted rows, deterministic
record ids, idempotent re-parse, raw policy per mapping lossless flag,
find_raw resolution, zip-slip refusal on results entries.
"""

from __future__ import annotations

import hashlib
import json
import sys
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from oreoa import db  # noqa: E402
from oreoa.corpus_gen import velociraptor  # noqa: E402
from oreoa.corpus_gen.scenario import load_scenarios  # noqa: E402
from oreoa.mappings import load_mappings  # noqa: E402
from oreoa.parse_velociraptor import parse_archive  # noqa: E402
from oreoa.scaffold import scaffold_case  # noqa: E402

CASE_ID = "2026-09-INC-410"
MAPPINGS = load_mappings(ROOT / "mappings")


@pytest.fixture(scope="module")
def archive(tmp_path_factory):
    scenario = next(s for s in load_scenarios(ROOT / "corpus" / "scenarios") if s.name == "win-workstation-01")
    out = tmp_path_factory.mktemp("corpus") / "win-workstation-01.velociraptor.zip"
    velociraptor.build_archive(scenario, out)
    return out


@pytest.fixture()
def case(tmp_path, archive):
    cdir = scaffold_case(tmp_path, CASE_ID, "incident")
    evidence_dir = cdir / "evidence"
    evidence_dir.chmod(0o755)
    target = evidence_dir / "win-workstation-01.velociraptor.zip"
    target.write_bytes(archive.read_bytes())
    evidence_dir.chmod(0o555)
    return cdir, target


def test_parse_families_and_counts(case):
    cdir, target = case
    details = parse_archive(target, CASE_ID, "EV-001", "WKS-042", cdir)
    assert details["unmapped_artifacts"] == []
    families = details["families"]
    for family in ("log_events", "executions", "auth_events", "persistence", "registry", "network", "fs_journal", "browser", "user_activity"):
        assert families.get(family, 0) > 0, family

    con = db.connect(cdir)
    try:
        # H-EX-003: certutil -urlcache LOLBin row
        assert con.execute(
            "select count(*) from executions where exe_name = 'certutil.exe'"
        ).fetchone()[0] == 1
        # H-PR-003: 30 logon failures then success
        assert con.execute(
            "select count(*) from auth_events where event_type = 'logon_failure'"
        ).fetchone()[0] == 30
        # H-PE-002/008/009/LM-002/C2-004: service installs projected
        assert con.execute(
            "select count(*) from persistence where mechanism = 'service'"
        ).fetchone()[0] >= 4
        # H-C2-001: 40 beacons
        assert con.execute(
            "select count(*) from network where entry_type = 'connection' and dst_ip = '203.0.113.66'"
        ).fetchone()[0] == 40
        # H-AF-001: 1102 cleared log kept verbatim (lossy raw)
        assert con.execute(
            "select count(*) from log_events where event_id = '1102'"
        ).fetchone()[0] == 1
    finally:
        con.close()


def test_record_ids_deterministic_and_unique(case):
    cdir, target = case
    first = parse_archive(target, CASE_ID, "EV-001", "WKS-042", cdir)
    con = db.connect(cdir)
    try:
        rows = con.execute("select record_id, source_ref from executions order by record_id").fetchall()
    finally:
        con.close()
    assert len({r[0] for r in rows}) == len(rows)
    parse_archive(target, CASE_ID, "EV-001", "WKS-042", cdir)
    con = db.connect(cdir)
    try:
        rows2 = con.execute("select record_id from executions order by record_id").fetchall()
        assert [r[0] for r in rows] == [r[0] for r in rows2]
        assert con.execute("select count(*) from executions").fetchone()[0] == first["families"]["executions"]
    finally:
        con.close()


def test_raw_policy_lossless_vs_lossy(case):
    cdir, target = case
    parse_archive(target, CASE_ID, "EV-001", "WKS-042", cdir)
    con = db.connect(cdir)
    try:
        amcache = con.execute(
            "select record_id from executions where evidence_type = 'amcache' limit 1"
        ).fetchone()[0]
        raws = db.find_raw(con, cdir, "executions", [amcache])
        assert raws.get(amcache) is None  # lossless: raw omitted
        log_row = con.execute("select record_id from log_events limit 1").fetchone()[0]
        raws = db.find_raw(con, cdir, "log_events", [log_row])
        assert raws.get(log_row)  # lossy: raw kept verbatim
    finally:
        con.close()


def test_idempotent_reparse_stable_counts(case):
    cdir, target = case
    d1 = parse_archive(target, CASE_ID, "EV-001", "WKS-042", cdir)
    d2 = parse_archive(target, CASE_ID, "EV-001", "WKS-042", cdir)
    assert d1["families"] == d2["families"]


def test_zip_slip_entry_in_results_refused(case, tmp_path):
    cdir, target = case
    poisoned = tmp_path / "poisoned.zip"
    with zipfile.ZipFile(target) as src, zipfile.ZipFile(poisoned, "w") as dst:
        for name in src.namelist():
            dst.writestr(name, src.read(name))
        dst.writestr("results/../../evil.json", "{}\n")
    with pytest.raises(ValueError, match="zip-slip"):
        parse_archive(poisoned, CASE_ID, "EV-001", "WKS-042", cdir)


def test_upload_entries_ignored_not_extracted(case):
    """The corpus plants a zip-slip entry under uploads/ - the parser must
    ignore uploads entirely (the extract step owns them at work-order 2)."""
    cdir, target = case
    details = parse_archive(target, CASE_ID, "EV-001", "WKS-042", cdir)
    assert all("zipslip" not in warning for warning in details["warnings"])


def test_host_mismatch_warns(case):
    cdir, target = case
    details = parse_archive(target, CASE_ID, "EV-001", "OTHER-HOST", cdir)
    assert any("host mismatch" in w for w in details["warnings"])


def test_unmapped_artifact_reported(case, tmp_path):
    cdir, target = case
    details = parse_archive(target, CASE_ID, "EV-001", "WKS-042", cdir, mappings={})
    assert details["unmapped_artifacts"], "no mapping -> artifact reported"
    assert details["rows"] == 0
