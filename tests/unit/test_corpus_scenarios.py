"""T1: T0 corpus scenarios (work-order step 1.6).

Covers: scenario validation, hunt coverage against the seed catalogue
(every Windows-applicable detection hunt is either an expected fast
detection or declared on a later lane with a note), clean-host constraints,
repeat expansion determinism, trap declarations.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from oreoa.corpus_gen.scenario import load_scenarios, load_scenario  # noqa: E402

CORPUS = ROOT / "corpus"
SCENARIOS_DIR = CORPUS / "scenarios"


@pytest.fixture(scope="module")
def scenarios():
    loaded = load_scenarios(SCENARIOS_DIR)
    assert loaded, "no scenario found"
    return {s.name: s for s in loaded}


@pytest.fixture(scope="module")
def seed_hunts():
    payload = yaml.safe_load((ROOT / "hunts_catalog_seed.yaml").read_text())
    return {hunt["id"]: hunt for hunt in payload["hunts"]}


def test_scenarios_load_and_are_windows(scenarios):
    assert "win-workstation-01" in scenarios
    assert "clean-host-01" in scenarios
    for scenario in scenarios.values():
        assert scenario.host.os == "windows"


def test_committed_manifest_scenario_hashes_match():
    """SPEC T0: tests fail if the hash drifts without a scenario change."""
    import hashlib
    import json

    manifest = json.loads((CORPUS / "corpus_manifest.json").read_text())
    for name, committed in manifest["scenarios_sha256"].items():
        actual = hashlib.sha256((SCENARIOS_DIR / f"{name}.yaml").read_bytes()).hexdigest()
        assert actual == committed, (
            f"scenario {name} changed but corpus/corpus_manifest.json was not "
            "rebuilt (run: make corpus)"
        )


def test_committed_manifest_artifacts_exist_and_match():
    """Full check when the corpus is built locally (out/ is gitignored)."""
    import json

    manifest = json.loads((CORPUS / "corpus_manifest.json").read_text())
    for artifact in manifest["artifacts"]:
        path = CORPUS / artifact["file"]
        if not path.is_file():
            pytest.skip(f"corpus not built locally (missing {path}); run: make corpus")
        import hashlib

        assert hashlib.sha256(path.read_bytes()).hexdigest() == artifact["sha256"]


def test_clean_host_has_no_traps_no_detections(scenarios):
    clean = scenarios["clean-host-01"]
    assert clean.kind == "clean"
    assert clean.expected_detections == []
    assert not clean.traps.prompt_injection
    assert not clean.traps.hallucination_record_id


def test_expected_detections_reference_seed_hunts(scenarios, seed_hunts):
    for scenario in scenarios.values():
        for expected in scenario.expected_detections:
            assert expected.hunt in seed_hunts, f"{scenario.name}: unknown hunt {expected.hunt}"
            assert expected.note, f"{scenario.name}: {expected.hunt} needs a note"


def test_windows_hunt_coverage(scenarios, seed_hunts):
    """Every Windows-applicable detection hunt is covered exactly once.

    Timeline helpers (level informational) are excluded by design; hunts on
    step2/deep lanes are declared with their reason.
    """
    expected: dict[str, int] = {}
    for scenario in scenarios.values():
        for detection in scenario.expected_detections:
            expected[detection.hunt] = expected.get(detection.hunt, 0) + 1

    def os_list(hunt):
        value = hunt["os"]
        if isinstance(value, list):
            return value
        if value == "all":
            return ["windows", "linux", "macos", "android"]
        return [value]

    windows_hunts = [
        hunt_id
        for hunt_id, hunt in seed_hunts.items()
        if "windows" in os_list(hunt) and hunt.get("level") != "informational"
    ]
    assert windows_hunts, "seed catalogue unexpectedly empty for windows"
    missing = [hunt_id for hunt_id in windows_hunts if expected.get(hunt_id, 0) != 1]
    assert not missing, f"hunts not covered exactly once by scenarios: {missing}"
    extra = [hunt_id for hunt_id in expected if hunt_id not in windows_hunts]
    assert not extra, f"expected detections outside windows detection hunts: {extra}"


def test_fast_lanes_covered_by_planted_events(scenarios):
    """Each fast expected detection must have a note (planted content proof);
    deep/step2 lanes must state their dependency."""
    for scenario in scenarios.values():
        for detection in scenario.expected_detections:
            if detection.lane == "fast":
                assert detection.note
            else:
                assert detection.note, f"{detection.hunt} ({detection.lane}) needs its reason"


def test_trap_declarations(scenarios):
    compromised = scenarios["win-workstation-01"]
    assert len(compromised.traps.hallucination_record_id) == 64
    where = {trap.where for trap in compromised.traps.prompt_injection}
    # SPEC T0: injection planted in file names, command lines, log messages,
    # registry values and browser titles
    assert any("file name" in w for w in where)
    assert any("command line" in w for w in where)
    assert any("log message" in w for w in where)
    assert any("registry" in w for w in where)
    assert any("browser" in w for w in where)


def test_repeat_expansion_deterministic(scenarios):
    compromised = scenarios["win-workstation-01"]
    first = compromised.expand_events()
    second = compromised.expand_events()
    assert len(first) == len(second) > 100
    assert [e.model_dump() for e in first] == [e.model_dump() for e in second]
    # 350 share accesses (H-DC-003) + 450 deletes (H-AF-002) + 40 beacons
    channels = [e.fields.get("ShareName") for e in first if getattr(e, "event_id", None) == 5145]
    assert len(channels) == 350 and all(channels)


def test_scenario_rejects_unknown_event_type():
    import tempfile

    payload = {
        "version": 1,
        "name": "bad-scenario",
        "kind": "compromised",
        "host": {"hostname": "X", "os": "windows"},
        "window": {"start": "2026-08-30T01:30:00Z", "end": "2026-08-30T03:30:00Z"},
        "events": [{"type": "unknown_type", "ts": "2026-08-30T02:00:00Z"}],
    }
    with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False) as handle:
        import yaml

        yaml.safe_dump(payload, handle)
        path = Path(handle.name)
    with pytest.raises(Exception):
        load_scenario(path)
    path.unlink(missing_ok=True)
