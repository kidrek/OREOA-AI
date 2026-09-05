"""T1-lite: versions.env integrity (format, digest pins, knowledge shas)."""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from helpers import ROOT, load_versions_env  # noqa: E402

LINES = (ROOT / "versions.env").read_text().splitlines()

KNOWLEDGE_COMMIT_KEYS = [
    "DFIQ_COMMIT", "FORENSIC_ARTIFACTS_COMMIT", "SIGMA_COMMIT",
    "HAYABUSA_RULES_COMMIT", "CHAINSAW_RULES_COMMIT", "YARA_ELASTIC_COMMIT",
    "SIGNATURE_BASE_COMMIT", "LOLBAS_COMMIT", "GTFOBINS_COMMIT",
    "LOOBINS_COMMIT", "HIJACKLIBS_COMMIT", "LOLDRIVERS_COMMIT",
    "LOLRMM_COMMIT",
]

# Binary tool pins deliberately empty until their work-order step
# (capa/floss/die = deep lane, step 4; unified logs = step 4; symbols on
# demand). Hayabusa/chainsaw/zircolite resolved at S2.0 - see
# test_release_binary_pins_resolved.
DEFERRED_KEYS = [
    "CAPA_VERSION", "CAPA_SHA256",
    "FLOSS_VERSION", "FLOSS_SHA256",
    "DIE_VERSION", "DIE_SHA256",
    "UNIFIEDLOGS_TAG", "VOL_SYMBOLS_WINDOWS_SHA256", "VOL_SYMBOLS_MAC_SHA256",
    "VOL_SYMBOLS_LINUX_SHA256",
]

# Release binaries pinned at S2.0 (work-order step 2, build order
# docker_build_spec 11.2): version + pin-time sha256, verified at build.
RELEASE_BINARY_KEYS = [
    "HAYABUSA_VERSION", "HAYABUSA_SHA256",
    "CHAINSAW_VERSION", "CHAINSAW_SHA256",
    "ZIRCOLITE_VERSION", "ZIRCOLITE_SHA256",
]


def test_lines_are_key_value():
    for line in LINES:
        if not line or line.startswith("#"):
            continue
        assert re.fullmatch(r"[A-Z0-9_]+=\S*", line), f"malformed line: {line!r}"


def test_python_image_is_digest_pinned():
    value = load_versions_env()["PYTHON_IMAGE"]
    assert re.fullmatch(r"python:[\w.-]+@sha256:[0-9a-f]{64}", value), value


def test_knowledge_pins_are_full_sha():
    for key in KNOWLEDGE_COMMIT_KEYS:
        assert re.fullmatch(r"[0-9a-f]{40}", load_versions_env()[key]), key


def test_attack_version_is_pinned_tag():
    assert re.fullmatch(r"v\d+\.\d+", load_versions_env()["ATTACK_VERSION"])


def test_deferred_pins_are_empty():
    for key in DEFERRED_KEYS:
        value = load_versions_env().get(key, "")
        assert value == "" or not value.startswith("#"), key


def test_release_binary_pins_resolved():
    versions = load_versions_env()
    for key in RELEASE_BINARY_KEYS:
        assert versions.get(key), f"{key} must be pinned (S2.0)"
    for key in RELEASE_BINARY_KEYS:
        if key.endswith("_SHA256"):
            assert re.fullmatch(r"[0-9a-f]{64}", versions[key]), key


def test_clamd_client_pin_present():
    assert load_versions_env().get("PYCLAMD_VERSION"), "PYCLAMD_VERSION must be pinned"


def test_core_tool_pins_present():
    versions = load_versions_env()
    for key in (
        "DISSECT_VERSION", "PLASO_VERSION", "VOLATILITY3_VERSION",
        "DUCKDB_VERSION", "PYARROW_VERSION", "RQ_VERSION",
        "OPENCODE_VERSION", "TINYPROXY_VERSION", "REDIS_IMAGE",
    ):
        assert versions[key], f"{key} must be pinned"
