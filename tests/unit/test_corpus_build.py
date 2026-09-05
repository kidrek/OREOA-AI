"""T1: T0 corpus generators - determinism without Docker (work-order 1.6).

Archives (Velociraptor + KAPE) are built twice from the scenarios and must
be byte-identical (fixed timestamps, sorted entries). The raw NTFS image
determinism is covered by tests/infra/test_corpus_ntfs.py (needs the
one-shot container).
"""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from oreoa.corpus_gen import kape, velociraptor  # noqa: E402
from oreoa.corpus_gen.scenario import load_scenarios  # noqa: E402

CORPUS = ROOT / "corpus"


@pytest.fixture(scope="module")
def scenarios():
    return load_scenarios(CORPUS / "scenarios")


def _sha(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


@pytest.mark.parametrize("scenario_name", ["win-workstation-01", "clean-host-01"])
def test_velociraptor_archive_deterministic(scenarios, scenario_name, tmp_path):
    scenario = next(s for s in scenarios if s.name == scenario_name)
    hashes = set()
    for _ in range(2):
        out = tmp_path / f"{scenario_name}.velociraptor.zip"
        velociraptor.build_archive(scenario, out)
        hashes.add(_sha(out.read_bytes()))
    assert len(hashes) == 1


@pytest.mark.parametrize("scenario_name", ["win-workstation-01", "clean-host-01"])
def test_kape_archive_deterministic(scenarios, scenario_name, tmp_path):
    scenario = next(s for s in scenarios if s.name == scenario_name)
    hashes = set()
    for _ in range(2):
        out = tmp_path / f"{scenario_name}.kape.zip"
        kape.build_archive(scenario, out)
        hashes.add(_sha(out.read_bytes()))
    assert len(hashes) == 1


def test_velociraptor_archive_layout(scenarios, tmp_path):
    scenario = next(s for s in scenarios if s.name == "win-workstation-01")
    out = tmp_path / "archive.zip"
    velociraptor.build_archive(scenario, out)

    import json
    import zipfile

    with zipfile.ZipFile(out) as zf:
        names = zf.namelist()
        assert "client_info.json" in names
        assert "results/Windows.EventLogs.EvtxHunter.json" in names
        assert "results/Windows.System.Prefetch.json" in names
        assert "results/Windows.Sys.Amcache.json" in names
        assert "results/Windows.Applications.Chrome.Extensions.json" in names
        client = json.loads(zf.read("client_info.json"))
        assert client["hostname"] == "WKS-042"
        assert client["os"] == "windows"
        # SPEC T0 traps planted in the archive
        traps = json.loads(zf.read("_OREOA_TRAPS.json"))
        assert traps["hallucination_record_id"] == scenario.traps.hallucination_record_id
        assert any("../" in name for name in names), "zip-slip entry must be planted"
        bomb_info = zf.getinfo(traps["bomb_entry"])
        assert bomb_info.compress_size < 1024 * 1024  # highly compressible
        tamper = zf.read(traps["tamper_entry"])
        assert hashlib.sha256(tamper).hexdigest() == traps["tamper_actual_sha256"]
        assert traps["tamper_declared_sha256"] != traps["tamper_actual_sha256"]
        # uploads carry the file events
        uploads = [name for name in names if name.startswith("uploads/C:")]
        assert any(name.endswith("setup_x.exe") for name in uploads)


def test_kape_archive_module_outputs(scenarios, tmp_path):
    scenario = next(s for s in scenarios if s.name == "win-workstation-01")
    out = tmp_path / "kape.zip"
    kape.build_archive(scenario, out)

    import csv
    import io
    import zipfile

    with zipfile.ZipFile(out) as zf:
        mft = list(csv.DictReader(io.StringIO(zf.read("Module_Output/MFT/MFT.csv").decode())))
        usn = list(csv.DictReader(io.StringIO(zf.read("Module_Output/USN/USN.csv").decode())))
        amcache = list(csv.DictReader(io.StringIO(zf.read("Module_Output/Amcache/Amcache.csv").decode())))
        # timestomping planted in the SI set (H-AF-003): upd.exe SI 2019 vs FN 2026
        upd = next(row for row in mft if row["FileName"].lower() == "upd.exe")
        assert upd["SI_Created"].startswith("2019-01-01")
        assert upd["FN_Created"].startswith("2026-08-30")
        # USN carries the create/delete ops (real USN reason strings)
        ops = {row["Reason"] for row in usn}
        assert {"File Create", "File Delete"} <= ops
        # amcache rows exist (iqvw64e driver)
        assert any(row["Name"].endswith("iqvw64e.sys") for row in amcache)
