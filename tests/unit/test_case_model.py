"""T1: case.yaml Pydantic models (templates/case/case.yaml is the authority)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from oreoa.case_model import CaseFile, load_case  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
WORKED = ROOT / "templates" / "case" / "case.yaml"


def test_worked_template_validates():
    cf = load_case(WORKED)
    assert cf.schema_version == 2
    assert cf.case.id == "2026-09-INC-042"
    assert cf.case.type == "incident"
    assert cf.machines[0].criticity == "medium"
    assert cf.hypotheses[0].confidence == "medium"
    assert cf.findings[0].review == "accept"
    assert cf.gaps[0].status == "requested"
    assert cf.sessions[0].models.analyst == "qwen2.5-32b-instruct"


def test_invalid_confidence_rejected(tmp_path: Path):
    text = WORKED.read_text(encoding="utf-8").replace("confidence: medium", "confidence: certain")
    p = tmp_path / "case.yaml"
    p.write_text(text, encoding="utf-8")
    with pytest.raises(Exception):
        load_case(p)


def test_invalid_type_rejected(tmp_path: Path):
    text = WORKED.read_text(encoding="utf-8").replace("type: incident", "type: exercice_avance")
    p = tmp_path / "case.yaml"
    p.write_text(text, encoding="utf-8")
    with pytest.raises(Exception):
        load_case(p)


def test_findings_ids_are_enforced():
    data = {
        "schema_version": 2,
        "case": {"id": "2026-09-INC-001"},
        "findings": [{"id": "X1", "description": "bad prefix"}],
    }
    with pytest.raises(Exception):
        CaseFile.model_validate(data)


def test_empty_case_validates():
    cf = CaseFile.model_validate({"schema_version": 2, "case": {"id": "CASE-1"}})
    assert cf.hypotheses == []
    assert cf.context.timezone == "Europe/Paris"
