"""T1: DFIQ loader (official snapshot + internal Q0xxx, is_internal, OS)."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from oreoa import dfiq_loader  # noqa: E402

# Format v1.1.0 (google/dfiq data at DFIQ_COMMIT): name + uuid + internal.
OFFICIAL_TREE = {
    "upstream/dfiq/dfiq/data/scenarios/S1001.yaml": """\
name: Ransomware and Extortion Initial Access
type: scenario
description: Official scenario fixture.
uuid: 1f0a9c4e-1111-4a1b-8c2d-000000000001
id: S1001
dfiq_version: 1.1.0
tags: []
""",
    "upstream/dfiq/dfiq/data/facets/F1001.yaml": """\
name: How did the ransomware first run or get executed?
type: facet
description: Official facet fixture.
uuid: 1f0a9c4e-1111-4a1b-8c2d-000000000002
id: F1001
dfiq_version: 1.1.0
tags: []
parent_ids:
  - S1001
""",
    "upstream/dfiq/dfiq/data/questions/Q1001.yaml": """\
name: What files were downloaded using a web browser?
type: question
description: Official question fixture.
uuid: 1f0a9c4e-1111-4a1b-8c2d-000000000003
id: Q1001
dfiq_version: 1.1.0
tags: []
parent_ids:
  - F1001
approaches:
  - name: Detect browser downloads via change journal records
    description: Look for USN records created by browser processes.
""",
}

INTERNAL_TREE = {
    "custom/dfiq/scenarios/S0001.yaml": """\
name: Host Compromise Assessment
type: scenario
description: Internal scenario fixture.
uuid: 2f0a9c4e-2222-4a1b-8c2d-000000000001
id: S0001
dfiq_version: 1.1.0
internal: true
tags:
  - oreoa-internal
""",
    "custom/dfiq/facets/F0001.yaml": """\
name: Initial Access
type: facet
description: Internal facet fixture.
uuid: 2f0a9c4e-2222-4a1b-8c2d-000000000002
id: F0001
dfiq_version: 1.1.0
internal: true
tags:
  - oreoa-internal
parent_ids:
  - S0001
""",
    "custom/dfiq/questions/Q0001.yaml": """\
name: Office document opened followed by suspicious child process
type: question
description: Internal question fixture.
uuid: 2f0a9c4e-2222-4a1b-8c2d-000000000003
id: Q0001
dfiq_version: 1.1.0
internal: true
tags:
  - oreoa-internal
  - area:IA
parent_ids:
  - F0001
""",
    "custom/dfiq/questions/Q0007.yaml": """\
name: Execution from user-writable or temporary locations
type: question
description: Internal question fixture.
uuid: 2f0a9c4e-2222-4a1b-8c2d-000000000004
id: Q0007
dfiq_version: 1.1.0
internal: true
tags:
  - oreoa-internal
  - area:EX
parent_ids:
  - F0001
""",
    "custom/dfiq/approaches/.gitkeep": "",
}

SEED = """\
version: 0.3
hunts:
- id: H-IA-001
  title: Office document opened followed by suspicious child process
  tables: [user_activity, executions, log_events]
  os: [windows, macos]
  dfiq: [Q0001, Q1001]
- id: H-EX-001
  title: Execution from user-writable or temporary locations
  tables: [executions]
  os: [windows]
  dfiq: [Q0007]
- id: H-TL-001
  title: Timeline helper
  tables: [events]
  os: [windows]
"""


@pytest.fixture()
def knowledge_tree(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    root = tmp_path / "knowledge"
    for rel, content in OFFICIAL_TREE.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    for rel, content in INTERNAL_TREE.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    seed = tmp_path / "hunts_catalog_seed.yaml"
    seed.write_text(SEED, encoding="utf-8")
    monkeypatch.setenv("OREOA_KNOWLEDGE", str(root))
    monkeypatch.setenv("OREOA_HUNTS_CATALOG", str(seed))
    dfiq_loader.INDEX_CACHE.clear()
    return root


def test_internal_and_official_loaded(knowledge_tree: Path):
    index = dfiq_loader.get_index(knowledge_tree)
    assert index.official_available and index.internal_available
    internal = index.list("question", internal=True)
    official = index.list("question", internal=False)
    assert [q["id"] for q in internal] == ["Q0001", "Q0007"]
    assert [q["id"] for q in official] == ["Q1001"]
    assert all(q["is_internal"] for q in internal)
    assert not any(q["is_internal"] for q in official)


def test_internal_flag_id_convention_fallback(knowledge_tree: Path):
    """Q1001 carries no explicit internal flag: the id convention decides."""
    index = dfiq_loader.get_index(knowledge_tree)
    assert index.get("Q0001")["is_internal"] is True
    assert index.get("Q1001")["is_internal"] is False
    assert index.get("F0001")["is_internal"] is True
    assert index.get("S1001")["is_internal"] is False


def test_os_derivation_from_seed(knowledge_tree: Path):
    index = dfiq_loader.get_index(knowledge_tree)
    assert index.component_os("Q0001") == ["macos", "windows"]
    assert index.component_os("Q0007") == ["windows"]
    assert index.list("question", os_filter="linux") == []
    assert [q["id"] for q in index.list("question", os_filter="windows", internal=True)] == ["Q0001", "Q0007"]


def test_get_parents_children_hunts_approaches(knowledge_tree: Path):
    index = dfiq_loader.get_index(knowledge_tree)
    detail = index.get("Q0007")
    assert detail["source"] == "internal"
    assert [p["id"] for p in detail["parents"]] == ["F0001"]
    assert [h["id"] for h in detail["hunts"]] == ["H-EX-001"]
    facet = index.get("F0001")
    assert {c["id"] for c in facet["children"]} == {"Q0001", "Q0007"}
    official = index.get("Q1001")
    assert official["approaches"][0]["name"].startswith("Detect browser downloads")


def test_unknown_id_and_bad_os(knowledge_tree: Path):
    index = dfiq_loader.get_index(knowledge_tree)
    with pytest.raises(KeyError):
        index.get("Q9999")
    with pytest.raises(ValueError):
        index.list("question", os_filter="solaris")


def test_missing_upstream_degrades(knowledge_tree: Path, monkeypatch: pytest.MonkeyPatch):
    shutil.rmtree(knowledge_tree / "upstream")
    dfiq_loader.INDEX_CACHE.clear()
    index = dfiq_loader.get_index(knowledge_tree)
    assert index.official_available is False
    assert index.internal_available is True
    status = index.status()
    assert "update-knowledge" in status["official_snapshot"]["note"]
    assert [q["id"] for q in index.list("question", internal=True)] == ["Q0001", "Q0007"]


def test_malformed_file_is_a_hard_error(knowledge_tree: Path):
    """A schema-invalid file is never silently skipped (vocabulary
    discipline): missing required fields or a bad id pattern are errors."""
    cases = [
        # missing name/uuid/dfiq_version
        "type: question\nid: Q0002\nparent_ids: [F0001]\n",
        # bad id pattern
        "name: x\ntype: question\nuuid: 2f0a9c4e-2222-4a1b-8c2d-00000000abcd\n"
        "id: Q002\ndfiq_version: 1.1.0\nparent_ids: [F0001]\n",
        # question without parent
        "name: x\ntype: question\nuuid: 2f0a9c4e-2222-4a1b-8c2d-00000000aaaa\n"
        "id: Q0002\ndfiq_version: 1.1.0\ninternal: true\n",
        # question parent that is not a facet
        "name: x\ntype: question\nuuid: 2f0a9c4e-2222-4a1b-8c2d-00000000bbbb\n"
        "id: Q0002\ndfiq_version: 1.1.0\ninternal: true\nparent_ids: [S0001]\n",
    ]
    for content in cases:
        bad = knowledge_tree / "custom" / "dfiq" / "questions" / "Q0002.yaml"
        bad.write_text(content, encoding="utf-8")
        dfiq_loader.INDEX_CACHE.clear()
        with pytest.raises(ValueError):
            dfiq_loader.get_index(knowledge_tree)
        bad.unlink()
    dfiq_loader.INDEX_CACHE.clear()


def test_real_internal_tree_and_official_snapshot():
    """The authored knowledge/custom/dfiq/ tree and the fetched official
    snapshot both load (A6: same loader; official data at DFIQ_COMMIT)."""
    index = dfiq_loader.DFIQIndex(ROOT / "knowledge")
    assert index.internal_available is True
    questions = index.list("question", internal=True)
    assert len(questions) == 47
    assert all(q["id"].startswith("Q0") for q in questions)
    facets = index.list("facet", internal=True)
    assert [f["id"] for f in facets] == ["F0001", "F0002", "F0003", "F0004", "F0005", "F0006"]
    scenarios = index.list("scenario", internal=True)
    assert [s["id"] for s in scenarios] == ["S0001"]

    if index.official_available:
        official = index.list("question", internal=False)
        assert len(official) >= 90  # full google/dfiq catalogue at the pin
        detail = index.get("Q1014")
        assert detail["is_internal"] is False and detail["display_name"]

    # every internal question carries its hunts (approaches) from the seed
    assert [h["id"] for h in index.get("Q0001")["hunts"]] == ["H-IA-001"]

    # the generator is up to date (no drift between seed/mapping and the tree)
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "gen_internal_dfiq.py"), "--check"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_cross_tree_parent_resolution():
    """Internal question Q0046 sits under official facet F1025: the edge
    resolves through the merged view."""
    index = dfiq_loader.DFIQIndex(ROOT / "knowledge")
    detail = index.get("Q0046")
    assert detail["is_internal"] is True
    parents = {p["id"]: p for p in detail["parents"]}
    assert "F1025" in parents
    if index.official_available:
        assert parents["F1025"]["display_name"]
        # and the reverse edge exists on the official facet
        facet = index.get("F1025")
        assert "Q0046" in {c["id"] for c in facet["children"]}
