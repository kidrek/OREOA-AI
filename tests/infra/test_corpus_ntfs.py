"""T5: raw NTFS image generation (work-order step 1.6, docker-gated).

Requires: docker + the one-shot image ``oreoa/corpus-ntfs`` (``make
corpus-image``). Covers: image validity (NTFS boot sector), timestomping
plant (H-AF-003 SI/FN skew), deterministic volume serial and byte-level
build determinism (double build -> identical sha256, SPEC T0).
"""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tests"))

from helpers import image_exists  # noqa: E402

from oreoa.corpus_gen import ntfs  # noqa: E402
from oreoa.corpus_gen.builder import serial_for  # noqa: E402
from oreoa.corpus_gen.scenario import FileArtifact, load_scenario  # noqa: E402

NTFS_IMAGE = "oreoa/corpus-ntfs:dev"

docker_ready = pytest.mark.skipif(
    not image_exists(NTFS_IMAGE),
    reason="oreoa/corpus-ntfs image missing (run: make corpus-image)",
)


def _entries(scenario):
    entries = {}
    for event in scenario.expand_events():
        if isinstance(event, FileArtifact) and event.on_image:
            name = event.path.replace("/", "\\").rsplit("\\", 1)[-1]
            entries[name.lower()] = {
                "si": ntfs.datetime_to_filetime(event.si_created or event.ts_created or scenario.window_start),
                "fn": ntfs.datetime_to_filetime(event.ts_created or scenario.window_start),
            }
    return entries


@pytest.fixture(scope="module")
def scenario():
    return load_scenario(ROOT / "corpus" / "scenarios" / "win-workstation-01.yaml")


@pytest.fixture(scope="module")
def built_image(scenario):
    # Work under .scratch/ (workspace fs): the session tmp dirs and the
    # docker daemon have delayed cross-visibility, the workspace does not.
    out = ROOT / ".scratch" / "corpus_ntfs_test"
    out.mkdir(parents=True, exist_ok=True)
    image = out / "win-workstation-01.disk.img"
    image.unlink(missing_ok=True)
    plan = ntfs.build_plan(scenario)
    ntfs.write_staging(out, plan)
    ntfs.run_container(NTFS_IMAGE, out, out_name=image.name)
    ntfs.clean_staging(out)
    ntfs.patch_image(
        image,
        _entries(scenario),
        scenario.window_start,
        serial_for(scenario),
        horizon_time=scenario.window_end,
    )
    return image


@docker_ready
def test_image_is_valid_ntfs(built_image):
    head = built_image.read_bytes()[:16]
    assert head[3:11] == b"NTFS    "
    assert built_image.stat().st_size == 64 * 1024 * 1024


@docker_ready
def test_timestomping_planted(built_image):
    """H-AF-003: upd.exe $STANDARD_INFORMATION forged to 2019 while
    $FILE_NAME keeps the real 2026 creation time."""
    entries = ntfs.read_entries(built_image, ["upd.exe"])
    si_created = ntfs.filetime_to_datetime(entries["upd.exe"][0])
    fn_created = ntfs.filetime_to_datetime(entries["upd.exe"][4])
    assert si_created.year == 2019
    assert (fn_created.year, fn_created.month, fn_created.day) == (2026, 8, 30)


@docker_ready
def test_volume_serial_deterministic(built_image, scenario):
    expected = serial_for(scenario)
    assert ntfs.boot_serial(built_image) == expected


@docker_ready
def test_double_build_identical(scenario):
    """SPEC T0: the corpus is rebuilt by make corpus and hashed; the hash
    must not drift without a scenario change."""
    entries = _entries(scenario)
    serial = serial_for(scenario)
    plan = ntfs.build_plan(scenario)
    hashes = set()
    for tag in ("one", "two"):
        out = ROOT / ".scratch" / f"corpus_ntfs_test_{tag}"
        out.mkdir(parents=True, exist_ok=True)
        image = out / "win-workstation-01.disk.img"
        image.unlink(missing_ok=True)
        ntfs.write_staging(out, plan)
        ntfs.run_container(NTFS_IMAGE, out, out_name=image.name)
        ntfs.clean_staging(out)
        ntfs.patch_image(image, entries, scenario.window_start, serial, horizon_time=scenario.window_end)
        hashes.add(hashlib.sha256(image.read_bytes()).hexdigest())
    assert len(hashes) == 1
