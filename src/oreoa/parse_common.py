"""Shared fast-lane parser helpers (S2.1).

The quick parsers (S1.6 Velociraptor JSONL, S2.1 KAPE module CSVs) emit rows
through one contract:

- deterministic ``record_id`` = sha256(ev_id | forensic_artifact | source_ref)
  (normalized_data_model.md principle 2);
- every non-referenced top-level source key is captured in ``extra`` (nothing
  dropped);
- ``raw`` per mapping ``lossless`` flag (``raw_policy_for``);
- ``summary`` rendered from the mapping template;
- per-row projections into semantic families with ``derived_from``-style
  ``source_ref`` suffix (cross-cutting rule of the data model).

Row persistence goes through :func:`oreoa.db.write_parsed_rows` (one Parquet
per family + idempotent DuckDB load of the materialized families + views).
The LLM never sees this layer (SPEC): output is Parquet + DuckDB only.
"""

from __future__ import annotations

import json
from typing import Any

from oreoa.mappings import Mapping, SafeDict
from oreoa.normalize import build_summary, raw_policy_for, record_id


def validate_entry_name(name: str) -> None:
    """Refuse archive entry names with ``..`` segments (zip-slip, T5)."""
    if ".." in name.split("/"):
        raise ValueError(f"zip-slip entry refused: {name!r}")


def extra_json(source: dict[str, Any], referenced: set[str]) -> str:
    """Leftover source keys not referenced by the mapping, verbatim JSON."""
    leftover = {key: value for key, value in source.items() if key not in referenced}
    return json.dumps(leftover, sort_keys=True, ensure_ascii=False)


def render_projection_summary(projection, row: dict[str, Any]) -> str:
    if not projection.summary_template:
        return ""
    return build_summary(projection.summary_tag, projection.summary_template.format_map(SafeDict(row)))


def emit_row(
    mapping: Mapping,
    source: dict[str, Any],
    ctx: dict[str, Any],
    rows_by_family: dict[str, list[dict[str, Any]]],
) -> None:
    """Map one source record into ``rows_by_family`` (base row + projections)."""
    from oreoa.normalize import raw_policy_for as _raw_policy_for

    def base_row(record_ref: str) -> dict[str, Any]:
        return {
            "record_id": "",  # set below (needs artifact + source_ref)
            "case_id": ctx["case_id"],
            "ev_id": ctx["ev_id"],
            "host": ctx["host"],
            "os": ctx["os"],
            "artifact": mapping.forensic_artifact,
            "family": mapping.family,
            "user_name": None,
            "user_id": None,
            "user_id_type": None,
            "source_tool": mapping.source_tool,
            "source_path": ctx["source_path"],
            "source_ref": record_ref,
            "parser_version": ctx["parser_version"],
            "mapping_version": str(mapping.version),
            "ingested_at": ctx["ingested_at"],
            "tags": [],
        }

    row = base_row(ctx["source_ref"])
    row.update(mapping.build_row(source, ctx["os"]))
    row["record_id"] = record_id(ctx["ev_id"], mapping.forensic_artifact, ctx["source_ref"])
    row["extra"] = extra_json(source, mapping.referenced_paths)
    row["raw"] = None if mapping.lossless else json.dumps(source, sort_keys=True, ensure_ascii=False)
    row["raw_policy"] = _raw_policy_for(mapping.lossless)
    row["summary"] = mapping.render_summary(row)
    rows_by_family.setdefault(mapping.family, []).append(row)

    for projection in mapping.projections:
        if not projection.matches(source):
            continue
        ref = f"{ctx['source_ref']}:{projection.family}"
        projected = base_row(ref)
        projected["family"] = projection.family
        for spec in projection.fields:
            projected[spec.target] = spec.resolve(source, ctx["os"])
        for target, value in projection.consts.items():
            projected[target] = value
        projected["record_id"] = record_id(ctx["ev_id"], mapping.forensic_artifact, ref)
        projected["extra"] = extra_json(source, mapping.referenced_paths)
        projected["raw"] = None if mapping.lossless else json.dumps(source, sort_keys=True, ensure_ascii=False)
        projected["raw_policy"] = _raw_policy_for(mapping.lossless)
        projected["summary"] = render_projection_summary(projection, projected)
        rows_by_family.setdefault(projection.family, []).append(projected)
