"""T1: NOTICE coverage of the pinned knowledge sources (SPEC amendment A5).

The NOTICE is the licence surface of the platform: every source recorded in
knowledge/snapshot.json must have a NOTICE entry with its recorded licence
(custom upstream licences only require the pointer), the Elastic License 2.0
redistribution check must be stated, and the Volatility VSL v1.0 section
must be present. A new pinned source without a NOTICE entry fails CI.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _notice() -> str:
    return (ROOT / "NOTICE").read_text(encoding="utf-8")


def _snapshot() -> dict:
    return json.loads((ROOT / "knowledge" / "snapshot.json").read_text(encoding="utf-8"))


def test_notice_covers_every_snapshot_source() -> None:
    notice = _notice()
    sources = _snapshot()["sources"]
    assert sources, "knowledge/snapshot.json records no sources"
    for source in sources:
        assert source["name"] in notice, (
            f"NOTICE has no entry for pinned source {source['name']!r} (A5)"
        )
        licence = source["licence"]
        if "see LICENSE" in licence:
            continue  # custom upstream licence: NOTICE points to the upstream file
        assert licence.split(" (")[0] in notice, (
            f"NOTICE does not state licence {licence!r} for {source['name']!r} (A5)"
        )


def test_notice_states_elastic_redistribution_check() -> None:
    notice = _notice()
    assert "Elastic License 2.0" in notice
    assert "not shipped in any image" in notice, (
        "SPEC A5: the Elastic License 2.0 redistribution check must be stated"
    )


def test_notice_keeps_vsl_section_and_repo_licence() -> None:
    notice = _notice()
    assert "Volatility Software License v1.0" in notice
    assert "AGPL-3.0" in notice
    assert "v2" in notice, "NOTICE must be regenerated for the v2 stack (A5)"


def test_notice_does_not_claim_knowledge_is_baked() -> None:
    notice = _notice()
    assert "never baked" in notice, (
        "A6 model: knowledge sources are workstation-fetched, never baked - "
        "the NOTICE must say so"
    )
