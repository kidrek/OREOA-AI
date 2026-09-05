"""Corpus build orchestration (``make corpus``).

For every scenario (sorted by name):

- ``out/<scenario>/<scenario>.velociraptor.zip`` (fast-lane evidence)
- ``out/<scenario>/<scenario>.kape.zip``         (step-2 quick-parser source)
- ``out/<scenario>/<scenario>.disk.img``         (raw NTFS v0, one-shot
  container + MFT patcher; skipped with ``--no-image``)

Then writes ``corpus/corpus_manifest.json`` (committed): scenario file
sha256s + artifact sha256s. The T1 drift test fails when a scenario changes
without a rebuild - SPEC T0 "tests fail if the hash drifts without a
scenario change".
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from oreoa.corpus_gen import kape, ntfs, velociraptor
from oreoa.corpus_gen.scenario import FileArtifact, Scenario, load_scenarios

MANIFEST_FILENAME = "corpus_manifest.json"
MANIFEST_SCHEMA_VERSION = 1


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def serial_for(scenario: Scenario) -> int:
    """Deterministic volume serial derived from the scenario name."""
    return int.from_bytes(hashlib.sha256(scenario.name.encode()).digest()[:8], "big") & 0xFFFFFFFFFFFF


def build_scenario(
    scenario: Scenario,
    corpus_dir: Path,
    build_image: bool = True,
    ntfs_image: str = "oreoa/corpus-ntfs:dev",
) -> dict[str, Any]:
    """Build every artifact for one scenario; returns manifest entries."""
    scenario_name = scenario.name
    out_dir = corpus_dir / "out" / scenario_name
    out_dir.mkdir(parents=True, exist_ok=True)
    artifacts: list[dict[str, Any]] = []

    vr_path = out_dir / f"{scenario_name}.velociraptor.zip"
    velociraptor.build_archive(scenario, vr_path)
    artifacts.append(
        {
            "scenario": scenario_name,
            "kind": "archive_velociraptor",
            "file": str(vr_path.relative_to(corpus_dir)),
            "sha256": sha256_file(vr_path),
            "size_bytes": vr_path.stat().st_size,
        }
    )

    kape_path = out_dir / f"{scenario_name}.kape.zip"
    kape.build_archive(scenario, kape_path)
    artifacts.append(
        {
            "scenario": scenario_name,
            "kind": "archive_kape",
            "file": str(kape_path.relative_to(corpus_dir)),
            "sha256": sha256_file(kape_path),
            "size_bytes": kape_path.stat().st_size,
        }
    )

    if build_image:
        image_path = out_dir / f"{scenario_name}.disk.img"
        plan = ntfs.build_plan(scenario)
        if plan:
            ntfs.write_staging(out_dir, plan)
            ntfs.run_container(ntfs_image, out_dir, out_name=image_path.name)
            ntfs.clean_staging(out_dir)
            # Deterministic volume serial + timestamps; timestomping planted.
            entries: dict[str, dict[str, int]] = {}
            for event in scenario.expand_events():
                if isinstance(event, FileArtifact) and event.on_image:
                    name = event.path.replace("/", "\\").rsplit("\\", 1)[-1]
                    fn = ntfs.datetime_to_filetime(event.ts_created or scenario.window_start)
                    si = ntfs.datetime_to_filetime(event.si_created or event.ts_created or scenario.window_start)
                    entries[name.lower()] = {"si": si, "fn": fn}
            ntfs.patch_image(
                image_path,
                entries,
                scenario.window_start,
                serial_for(scenario),
                horizon_time=scenario.window_end,
            )
            artifacts.append(
                {
                    "scenario": scenario_name,
                    "kind": "disk_image",
                    "file": str(image_path.relative_to(corpus_dir)),
                    "sha256": sha256_file(image_path),
                    "size_bytes": image_path.stat().st_size,
                }
            )

    return {"scenario": scenario_name, "artifacts": artifacts}


def build_corpus(
    corpus_dir: Path,
    build_image: bool = True,
    ntfs_image: str = "oreoa/corpus-ntfs:dev",
) -> Path:
    """Build every scenario + the committed manifest; returns the manifest path."""
    corpus_dir = Path(corpus_dir)
    scenarios_dir = corpus_dir / "scenarios"
    scenarios = load_scenarios(scenarios_dir)
    if not scenarios:
        raise FileNotFoundError(f"no scenario in {scenarios_dir}")

    manifest_artifacts: list[dict[str, Any]] = []
    scenario_hashes: dict[str, str] = {}
    for scenario in scenarios:
        result = build_scenario(scenario, corpus_dir, build_image=build_image, ntfs_image=ntfs_image)
        manifest_artifacts.extend(result["artifacts"])
        scenario_hashes[scenario.name] = sha256_file(scenarios_dir / f"{scenario.name}.yaml")

    manifest = {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "scenarios_sha256": scenario_hashes,
        "artifacts": manifest_artifacts,
    }
    manifest_path = corpus_dir / MANIFEST_FILENAME
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest_path


def load_manifest(corpus_dir: Path) -> dict[str, Any]:
    return json.loads((Path(corpus_dir) / MANIFEST_FILENAME).read_text(encoding="utf-8"))
