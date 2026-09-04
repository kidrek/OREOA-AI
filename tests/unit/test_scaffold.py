"""T1: /case scaffold - empty skeletons derived from the templates."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from oreoa.case_model import load_case  # noqa: E402
from oreoa.scaffold import scaffold_case  # noqa: E402


def test_scaffold_incident(tmp_path: Path):
    case_dir = scaffold_case(tmp_path, "2026-09-INC-100", "incident", name="Test", analyst="a.b")
    assert (case_dir / "evidence").is_dir()
    assert (case_dir / "derived").is_dir()
    assert (case_dir / "reports").is_dir()
    assert (case_dir / "state" / "keys").is_dir()
    assert (case_dir / "case.yaml").is_file()
    assert (case_dir / "journal.md").is_file()
    assert not (case_dir / "answers.yaml").exists()

    cf = load_case(case_dir / "case.yaml")
    assert cf.case.id == "2026-09-INC-100"
    assert cf.case.type == "incident"
    assert cf.hypotheses == [] and cf.findings == []

    journal = (case_dir / "journal.md").read_text(encoding="utf-8")
    assert "Etat courant" in journal
    assert "[ingest]" in journal and "[analyst]" in journal
    assert "2026-09-INC-100" in journal


def test_scaffold_exercice_gets_answers(tmp_path: Path):
    case_dir = scaffold_case(tmp_path, "2026-09-EXE-001", "exercice")
    assert (case_dir / "answers.yaml").is_file()
    content = (case_dir / "answers.yaml").read_text(encoding="utf-8")
    assert "score" in content  # A2 reminder in the header


def test_scaffold_refuses_existing(tmp_path: Path):
    scaffold_case(tmp_path, "C-1", "incident")
    with pytest.raises(FileExistsError):
        scaffold_case(tmp_path, "C-1", "incident")


def test_scaffold_permissions(tmp_path: Path):
    import stat

    case_dir = scaffold_case(tmp_path, "C-2", "incident")
    mode = case_dir.stat().st_mode
    assert mode & stat.S_IRWXO == 0, "case dir must not be world-accessible"
    case_file = case_dir / "case.yaml"
    assert case_file.stat().st_mode & stat.S_IWUSR, "owner (analyst) writes case.yaml by hand"
    assert case_file.stat().st_mode & stat.S_IWGRP, "container group (OREOA_HOST_GID) writes via mcp-case"
    assert case_file.stat().st_mode & stat.S_IRWXO == 0, "case.yaml not world-accessible"
    keys = case_dir / "state" / "keys"
    assert keys.stat().st_mode & stat.S_IRWXO == 0
    assert keys.stat().st_mode & stat.S_IWGRP == 0, "keys dir is not group-writable"
