"""Performance thresholds as data (SPEC amendment A3).

Acceptance thresholds (triage brief < 10 min on a typical archive, < 20 min
on a 100 GB E01, ``/analyse`` resume < 2 s, ``case.duckdb`` < 1 GB for a
3-host case) live in ``evaluation/thresholds.yaml`` - never in code. T2
records measured values against them; a missed threshold blocks a PR unless
a re-baseline PR documents the measurement and the architect accepts the new
value (raw measurement reports under ``evaluation/measurements/``).

This module is the single loader for that file: work-order step 2 wires it
into the T2 performance gates; step 1.7 ships it with the measurement spike
(``scripts/measure_thresholds.py``) so the thresholds are calibrated as data
before step 2 depends on them.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, Field, field_validator

#: Threshold names the SPEC/A3 acceptance criteria depend on. New names are
#: additive (PR); these four must always be present.
REQUIRED_THRESHOLDS: frozenset[str] = frozenset(
    {
        "triage_brief_archive_s",
        "triage_brief_e01_100gb_s",
        "analyse_resume_s",
        "duckdb_3host_bytes",
    }
)


def default_path() -> Path:
    """Locate ``evaluation/thresholds.yaml``.

    ``OREOA_THRESHOLDS`` overrides (container mounts decide at step 2);
    otherwise the repo root relative to this module (host checkout, tests).
    """
    override = os.environ.get("OREOA_THRESHOLDS", "")
    if override:
        return Path(override)
    return Path(__file__).resolve().parents[2] / "evaluation" / "thresholds.yaml"


class Thresholds(BaseModel):
    """Parsed ``evaluation/thresholds.yaml`` (A3 - thresholds are data).

    ``thresholds``: name -> positive number, unit in the name suffix
    (``_s`` seconds, ``_bytes`` bytes). ``measured``: last re-baseline
    reference (date, git sha, values) copied from the measurement report by
    the re-baseline PR. ``rebaseline_rules``: the A3 governance lines.
    """

    schema_version: Literal[1]
    thresholds: dict[str, float] = Field(min_length=1)
    measured: dict[str, Any] = Field(default_factory=dict)
    rebaseline_rules: list[str] = Field(default_factory=list)

    @field_validator("thresholds")
    @classmethod
    def _positive_and_required(cls, v: dict[str, float]) -> dict[str, float]:
        missing = REQUIRED_THRESHOLDS - v.keys()
        if missing:
            raise ValueError(f"missing required thresholds: {sorted(missing)}")
        for name, value in v.items():
            if value <= 0:
                raise ValueError(f"threshold {name!r} must be > 0 (got {value})")
        return v


def load_thresholds(path: Path | None = None) -> Thresholds:
    """Load and validate the thresholds file (raises on any deviation)."""
    p = Path(path) if path is not None else default_path()
    data = yaml.safe_load(p.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{p}: expected a YAML mapping at the document root")
    return Thresholds.model_validate(data)
