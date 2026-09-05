"""T1: closed vocabularies and external-knowledge validation API."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from oreoa import vocab  # noqa: E402
from oreoa.vocab import (  # noqa: E402
    VocabularyError,
    validate_artifact,
    validate_attack_id,
    validate_attack_ids,
    validate_closed,
    validate_dfiq_id,
    validate_dfiq_ids,
)

KNOWN_ARTIFACTS = {"WindowsPrefetchFiles", "LinuxAuthLogs", "WindowsRegistryAmcache"}
KNOWN_ATTACK = {"T1059.001", "T1059", "T1003", "T1003.002", "T1566.001"}
KNOWN_DFIQ = {"Q1001", "Q0001", "F1001", "F0001", "S0001", "S1001"}


def test_closed_vocabulary_rejects_unknown_value():
    with pytest.raises(VocabularyError):
        validate_closed("os", "haiku", vocab.OS)


def test_closed_vocabulary_accepts_member():
    assert validate_closed("os", "windows", vocab.OS) == "windows"


def test_vocabularies_have_no_duplicates():
    for name, values in vocab.VOCABULARIES.items():
        assert len(values) == len(set(values)), f"duplicate values in {name}"


def test_vocabularies_are_nonempty_string_tuples():
    for name, values in vocab.VOCABULARIES.items():
        assert values, f"empty vocabulary {name}"
        assert all(isinstance(v, str) and v for v in values), f"bad value in {name}"


def test_families_partition_materialized_and_view_families():
    from oreoa import db

    assert set(db.FAMILY_COLUMNS.keys()) == set(vocab.FAMILIES)
    assert set(db.MATERIALIZED_FAMILIES) | set(db.VIEW_FAMILIES) == set(vocab.FAMILIES)
    assert not set(db.MATERIALIZED_FAMILIES) & set(db.VIEW_FAMILIES)


def test_artifact_accepts_known_name():
    assert validate_artifact("WindowsPrefetchFiles", KNOWN_ARTIFACTS) == "WindowsPrefetchFiles"


def test_artifact_rejects_unknown_name():
    with pytest.raises(VocabularyError):
        validate_artifact("MadeUpArtifact", KNOWN_ARTIFACTS)


def test_artifact_custom_escape_hatch():
    assert validate_artifact("custom:eri_internal_logs", set()) == "custom:eri_internal_logs"


def test_artifact_custom_bad_name_rejected():
    for bad in ("custom:", "custom:has space", "custom:/abs"):
        with pytest.raises(VocabularyError):
            validate_artifact(bad, KNOWN_ARTIFACTS)


def test_attack_id_pattern_and_membership():
    assert validate_attack_id("T1059.001", KNOWN_ATTACK) == "T1059.001"
    assert validate_attack_id("T1003", KNOWN_ATTACK) == "T1003"
    with pytest.raises(VocabularyError):
        validate_attack_id("TECHNIQUE", KNOWN_ATTACK)
    with pytest.raises(VocabularyError):
        validate_attack_id("T9999", KNOWN_ATTACK)


def test_attack_id_without_known_set_checks_pattern_only():
    assert validate_attack_id("T1110.003") == "T1110.003"
    assert validate_attack_ids(["T1059", "T1003.002"]) == ("T1059", "T1003.002")


def test_dfiq_id_official_and_internal_ranges():
    assert validate_dfiq_id("Q1001", KNOWN_DFIQ) == "Q1001"
    assert validate_dfiq_id("Q0001", KNOWN_DFIQ) == "Q0001"
    assert validate_dfiq_id("S0001", KNOWN_DFIQ) == "S0001"
    with pytest.raises(VocabularyError):
        validate_dfiq_id("Q2001", KNOWN_DFIQ)
    with pytest.raises(VocabularyError):
        validate_dfiq_id("X1001", KNOWN_DFIQ)
    with pytest.raises(VocabularyError):
        validate_dfiq_ids(["Q1001", "Q9999"], KNOWN_DFIQ)
