"""T1: evaluation/thresholds.yaml loader (SPEC amendment A3).

Thresholds are data, not constants: the file must carry the four SPEC/A3
acceptance thresholds with positive values, and the loader must reject any
deviation (missing key, non-positive value, wrong document type). Raw
measurement reports live under evaluation/measurements/; the ``measured``
block of the file is updated by re-baseline PRs only.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from oreoa.thresholds import REQUIRED_THRESHOLDS, default_path, load_thresholds


def test_repo_thresholds_load() -> None:
    thresholds = load_thresholds()
    assert thresholds.schema_version == 1
    for name in REQUIRED_THRESHOLDS:
        assert name in thresholds.thresholds
        assert thresholds.thresholds[name] > 0
    # SPEC A3 acceptance values ship as the initial baseline
    assert thresholds.thresholds["triage_brief_archive_s"] == 600
    assert thresholds.thresholds["triage_brief_e01_100gb_s"] == 1200
    assert thresholds.thresholds["analyse_resume_s"] == 2
    assert thresholds.thresholds["duckdb_3host_bytes"] == 1024**3


def test_measured_block_is_a_rebaseline_reference() -> None:
    thresholds = load_thresholds()
    if not thresholds.measured:
        pytest.skip("no measured block committed yet")
    for key in ("measured_at", "git_sha", "method"):
        assert key in thresholds.measured, f"measured.{key} missing (A3 re-baseline PR)"


def test_default_path_exists() -> None:
    assert default_path().is_file()


def _write(tmp_path, payload: str):
    path = tmp_path / "thresholds.yaml"
    path.write_text(payload, encoding="utf-8")
    return path


BASE = """\
schema_version: 1
thresholds:
  triage_brief_archive_s: 600
  triage_brief_e01_100gb_s: 1200
  analyse_resume_s: 2
  duckdb_3host_bytes: 1073741824
"""


def test_minimal_valid_file(tmp_path) -> None:
    thresholds = load_thresholds(_write(tmp_path, BASE))
    assert thresholds.thresholds["analyse_resume_s"] == 2.0


def test_missing_required_threshold_rejected(tmp_path) -> None:
    payload = BASE.replace("  analyse_resume_s: 2\n", "")
    with pytest.raises(ValueError, match="missing required thresholds"):
        load_thresholds(_write(tmp_path, payload))


def test_non_positive_threshold_rejected(tmp_path) -> None:
    payload = BASE.replace("analyse_resume_s: 2", "analyse_resume_s: 0")
    with pytest.raises(ValueError, match="must be > 0"):
        load_thresholds(_write(tmp_path, payload))


def test_negative_threshold_rejected(tmp_path) -> None:
    payload = BASE.replace("triage_brief_archive_s: 600", "triage_brief_archive_s: -1")
    with pytest.raises(ValueError, match="must be > 0"):
        load_thresholds(_write(tmp_path, payload))


def test_non_mapping_document_rejected(tmp_path) -> None:
    with pytest.raises(ValueError, match="expected a YAML mapping"):
        load_thresholds(_write(tmp_path, "- just\n- a\n- list\n"))


def test_additive_thresholds_allowed(tmp_path) -> None:
    payload = BASE + "  custom_new_gate_s: 30\n"
    thresholds = load_thresholds(_write(tmp_path, payload))
    assert thresholds.thresholds["custom_new_gate_s"] == 30


def test_yaml_string_value_rejected(tmp_path) -> None:
    payload = BASE.replace("analyse_resume_s: 2", "analyse_resume_s: two")
    with pytest.raises(Exception):
        load_thresholds(_write(tmp_path, payload))
