"""T1: mapping loader (work-order step 1.6, "mappings as data").

Covers: strict validation (family/column/transform/type), field resolution
(paths, indexes, consts, defaults), transforms, summary rendering (deterministic,
<= 160 chars), lossless round-trip (every source top-level key is either fully
projected or captured in extra), duplicate artifact rejection.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from oreoa.mappings import (  # noqa: E402
    Mapping,
    load_mapping,
    load_mappings,
    mappings_root,
)

MAPPINGS = ROOT / "mappings"


@pytest.fixture(scope="module")
def mappings():
    loaded = load_mappings(MAPPINGS)
    assert loaded, "no mapping found"
    return loaded


def test_mappings_root_resolves_repo():
    import os

    os.environ.pop("OREOA_MAPPINGS_DIR", None)
    original_cwd = Path.cwd()
    try:
        import os as _os

        _os.chdir(ROOT)
        assert mappings_root() == ROOT / "mappings"
    finally:
        import os as _os

        _os.chdir(original_cwd)


def test_every_mapping_loads_with_valid_family(mappings):
    from oreoa.vocab import FAMILIES

    for artifact, mapping in mappings.items():
        assert mapping.artifact == artifact
        assert mapping.family in FAMILIES
        assert mapping.source_tool == "velociraptor"
        assert mapping.version == 1


def test_evtx_mapping_projects_semantic_families(mappings):
    mapping = mappings["Windows.EventLogs.EvtxHunter"]
    families = {projection.family for projection in mapping.projections}
    assert {"executions", "auth_events", "accounts", "persistence", "network", "fs_journal"} <= families
    assert mapping.lossless is False  # partial EventData projection


def test_field_resolution_paths_and_consts():
    mapping = load_mapping(MAPPINGS / "velociraptor" / "Windows.System.Prefetch.yaml")
    row = mapping.build_row(
        {
            "SourceFilename": "C:\\Users\\j.dupont\\AppData\\Local\\Temp\\upd.exe",
            "RunCount": 3,
            "Times": ["2026-08-30T02:14:11Z", "2026-08-30T02:47:00Z"],
            "FilesLoaded": ["C:\\Windows\\System32\\ntdll.dll"],
            "PrefetchHash": "abc",
        },
        "windows",
    )
    assert row["exe_name"] == "upd.exe"
    assert row["exe_path_norm"] == "c:/users/j.dupont/appdata/local/temp/upd.exe"
    assert row["run_count"] == 3
    assert row["ts_first"].isoformat() == "2026-08-30T02:14:11"
    assert row["evidence_type"] == "prefetch"  # const
    assert row["ts_last"].isoformat() == "2026-08-30T02:47:00"


def test_missing_field_resolves_to_none():
    mapping = load_mapping(MAPPINGS / "velociraptor" / "Windows.Sys.Amcache.yaml")
    row = mapping.build_row({}, "windows")
    assert row["exe_path"] is None
    assert row["hash_sha256"] is None


def test_transform_user_name_and_service_key():
    payload = {
        "version": 1,
        "source_tool": "velociraptor",
        "artifact": "X.Test",
        "family": "persistence",
        "lossless": True,
        "fields": {
            "user_name": {"path": "U", "type": "str", "transform": "user_name"},
            "location": {"path": "N", "type": "str", "transform": "service_key"},
        },
    }
    mapping = Mapping(payload, Path("test.yaml"))
    row = mapping.build_row({"U": "CORP\\j.dupont", "N": "Svc1"}, "windows")
    assert row["user_name"] == "j.dupont"
    assert row["location"] == "HKLM\\SYSTEM\\CurrentControlSet\\Services\\Svc1"


def test_summary_deterministic_and_capped():
    mapping = load_mapping(MAPPINGS / "velociraptor" / "Windows.Registry.AllValues.yaml")
    row = mapping.build_row(
        {
            "Hive": "SOFTWARE",
            "KeyPath": "SOFTWARE\\Microsoft\\Windows NT\\CurrentVersion\\Image File Execution Options\\sethc.exe",
            "ValueName": "Debugger",
            "ValueType": "REG_SZ",
            "ValueData": "C:\\Users\\Public\\sethc_backdoor.exe",
            "LastWriteTimestamp": "2026-08-30T02:26:00Z",
        },
        "windows",
    )
    first = mapping.render_summary(row)
    second = mapping.render_summary(row)
    assert first == second
    assert len(first) <= 160
    assert first.startswith("[registry]")


def test_unknown_family_or_column_rejected(tmp_path):
    bad = tmp_path / "velociraptor" / "Bad.yaml"
    bad.parent.mkdir()
    bad.write_text(
        "version: 1\nsource_tool: velociraptor\nartifact: X\nfamily: nope\nfields:\n  a: {path: A}\n"
    )
    with pytest.raises(ValueError, match="family"):
        load_mapping(bad)

    bad2 = tmp_path / "velociraptor" / "Bad2.yaml"
    bad2.write_text(
        "version: 1\nsource_tool: velociraptor\nartifact: X\nfamily: executions\nfields:\n  not_a_column: {path: A}\n"
    )
    with pytest.raises(ValueError, match="not a column"):
        load_mapping(bad2)


def test_unknown_transform_rejected(tmp_path):
    bad = tmp_path / "velociraptor" / "Bad.yaml"
    bad.parent.mkdir()
    bad.write_text(
        "version: 1\nsource_tool: velociraptor\nartifact: X\nfamily: executions\n"
        "fields:\n  exe_name: {path: A, transform: slash_delete}\n"
    )
    with pytest.raises(ValueError, match="transform"):
        load_mapping(bad)


def test_duplicate_artifact_rejected(tmp_path):
    dup = tmp_path / "velociraptor"
    dup.mkdir()
    content = (
        "version: 1\nsource_tool: velociraptor\nartifact: Same.Artifact\n"
        "family: executions\nfields:\n  exe_path: {path: A}\n"
    )
    (dup / "one.yaml").write_text(content)
    (dup / "two.yaml").write_text(content)
    with pytest.raises(ValueError, match="duplicate"):
        load_mappings(tmp_path)


def test_lossless_mappings_are_fully_projected(mappings):
    """Lossless invariant: every referenced source path is a bare top-level
    key (fully consumed scalar/structure) - the row is then re-derivable
    from the mapped columns + extra, so raw may stay NULL. Mappings that
    reference nested paths (EventData.Image, Times[0]) must stay lossy."""
    for artifact, mapping in mappings.items():
        for spec in mapping.fields:
            if spec.path and ("." in spec.path or "[" in spec.path):
                assert not mapping.lossless, (
                    f"{artifact}: nested path {spec.path!r} with lossless=true "
                    "would drop data - declare lossless=false (raw kept)"
                )


def test_lossy_mappings_keep_nested_paths(mappings):
    assert mappings["Windows.EventLogs.EvtxHunter"].lossless is False
    assert mappings["Windows.System.Prefetch"].lossless is False


def test_unreferenced_keys_go_to_extra_at_parse_time(mappings):
    """The parser captures every non-referenced top-level key in ``extra``
    (nothing dropped, data-model principle 1) - mapping level: referenced
    paths are known; parse level test asserts the extra payload."""
    mapping = mappings["Windows.Sys.Amcache"]
    assert mapping.referenced_paths == {"Path", "Name", "Sha256", "FileKeyLastWriteTimestamp", "Signer"}

    from oreoa.parse_velociraptor import _extra

    source = {
        "Path": "C:\\Windows\\Temp\\iqvw64e.sys",
        "Name": "iqvw64e.sys",
        "Sha256": "1f0a",
        "Size": 4096,
        "FileKeyLastWriteTimestamp": "2026-08-30T02:28:05Z",
        "Signer": "Intel Corporation",
    }
    extra = json.loads(_extra(source, mapping.referenced_paths))
    assert extra == {"Size": 4096}
