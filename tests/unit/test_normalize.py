"""T1: deterministic normalization primitives (record_id, path_norm, summary)."""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from oreoa import vocab  # noqa: E402
from oreoa.normalize import (  # noqa: E402
    RAW_POLICY_KEPT,
    RAW_POLICY_OMITTED_LOSSLESS,
    SUMMARY_MAX_CHARS,
    build_summary,
    path_norm,
    raw_policy_for,
    record_id,
    utc_now,
)
from oreoa.vocab import VocabularyError  # noqa: E402


def test_record_id_is_deterministic_and_hex():
    first = record_id("EV-001", "WindowsPrefetchFiles", "row=42")
    second = record_id("EV-001", "WindowsPrefetchFiles", "row=42")
    assert first == second
    assert len(first) == 64
    int(first, 16)


def test_record_id_changes_with_any_component():
    base = record_id("EV-001", "WindowsPrefetchFiles", "row=42")
    assert record_id("EV-002", "WindowsPrefetchFiles", "row=42") != base
    assert record_id("EV-001", "LinuxAuthLogs", "row=42") != base
    assert record_id("EV-001", "WindowsPrefetchFiles", "row=43") != base


def test_record_id_unambiguous_for_vocabulary_values():
    separator = "|"
    artifact = "WindowsPrefetchFiles"
    for ref in ("b|c", "plain", "x" * 200):
        material = f"EV-001{separator}{artifact}{separator}{ref}"
        assert record_id("EV-001", artifact, ref) == hashlib.sha256(
            material.encode("utf-8")
        ).hexdigest()


def test_path_norm_windows():
    assert (
        path_norm("C:\\Users\\j.dupont\\AppData\\Local\\Temp\\UPD.exe", "windows")
        == "c:/users/j.dupont/appdata/local/temp/upd.exe"
    )


def test_path_norm_linux_preserves_case():
    assert path_norm("/var/log/Auth.log", "linux") == "/var/log/Auth.log"


def test_path_norm_macos_lowercases():
    assert path_norm("/Users/JDupont/Downloads/Tool.DMG", "macos") == "/users/jdupont/downloads/tool.dmg"


def test_path_norm_keeps_unc_path_and_drive_letter():
    assert path_norm("\\\\SRV-01\\Share\\File.TXT", "windows") == "//srv-01/share/file.txt"
    assert path_norm("D:\\Data\\X", "windows").startswith("d:/")


def test_path_norm_rejects_unknown_os():
    with pytest.raises(VocabularyError):
        path_norm("/tmp/x", "haiku")


def test_summary_format_with_detail():
    line = build_summary("prefetch", "first run of C:\\Temp\\upd.exe", "run_count=3")
    assert line == "[prefetch] first run of C:\\Temp\\upd.exe (run_count=3)"


def test_summary_is_deterministic():
    args = ("prefetch", "first run of " + "A" * 200, "run_count=3")
    assert build_summary(*args) == build_summary(*args)


def test_summary_caps_at_160_chars():
    long_text = "x" * 500
    line = build_summary("executions", long_text, "detail")
    assert len(line) <= SUMMARY_MAX_CHARS
    assert line.endswith("...")
    assert line.startswith("[executions] ")


def test_summary_over_budget_drops_detail_before_cutting_text():
    text = "y" * 150
    line = build_summary("prefetch", text, "run_count=3")
    assert "(run_count=3)" not in line
    assert len(line) <= SUMMARY_MAX_CHARS


def test_summary_short_input_untouched():
    assert build_summary("hunt", "H-EX-001 matched 3 rows") == "[hunt] H-EX-001 matched 3 rows"


def test_raw_policy_mapping():
    assert raw_policy_for(True) == RAW_POLICY_OMITTED_LOSSLESS
    assert raw_policy_for(False) == RAW_POLICY_KEPT
    assert RAW_POLICY_KEPT in vocab.RAW_POLICY
    assert RAW_POLICY_OMITTED_LOSSLESS in vocab.RAW_POLICY


def test_utc_now_is_naive_utc_whole_seconds():
    now = utc_now()
    assert now.tzinfo is None
    assert now.microsecond == 0
