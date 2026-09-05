"""Fast-lane parser: Velociraptor offline-collector archive -> Parquet.

S1.6 first parser set (work-order step 1.6): reads ``results/*.json`` JSONL
from the offline-collector zip, maps rows through ``mappings/velociraptor/``
into the normalized families and writes ``derived/<EV-id>/parquet/<family>.parquet``
+ idempotent DuckDB load (materialized families; tier views refreshed).

Guarantees:

- deterministic ``record_id`` = sha256(ev_id | forensic_artifact | source_ref),
  source_ref = ``line:<n>[:<projection family>]`` (1-based line number);
- idempotent: re-parsing the same evidence replaces its rows (delete-then-
  insert by ev_id) and rewrites the same Parquet content;
- raw handling per mapping ``lossless`` flag (``raw_policy_for``);
- the LLM never sees this layer (SPEC): output is Parquet + DuckDB only;
- upload entries are NEVER extracted here: the parser refuses entry names
  with ``..`` segments (zip-slip defence, SPEC T5) and only reads the
  whitelisted result/layout entries; the ``extract`` step (work-order step 2)
  owns uploads with the noexec scratch rules.

Kinds other than ``archive_velociraptor`` are skipped by the worker (their
parsers land at steps 2/4) - explicit ``SkipStep``, never a silent success.
"""

from __future__ import annotations

import json
import zipfile
from pathlib import Path
from typing import Any

from oreoa import db
from oreoa.mappings import Mapping, load_mappings, utc_now

PARSER_VERSION = "1.0.0"
_ALLOWED_ENTRY_PREFIXES = ("client_info.json", "server_info.json", "_OREOA_TRAPS.json", "results/")


class SkipStep(Exception):
    """A step that does not apply to this evidence (explicit, journaled)."""


def _validate_entry_name(name: str) -> None:
    if ".." in name.split("/"):
        raise ValueError(f"zip-slip entry refused: {name!r}")


def _row_os(client_info: dict[str, Any]) -> str:
    from oreoa.vocab import OS, validate_closed

    candidate = str(client_info.get("os", "unknown"))
    return candidate if candidate in OS else validate_closed("os", "unknown", OS)


def _extra(source: dict[str, Any], referenced: set[str]) -> str:
    leftover = {key: value for key, value in source.items() if key not in referenced}
    return json.dumps(leftover, sort_keys=True, ensure_ascii=False)


def parse_archive(
    archive_path: Path,
    case_id: str,
    ev_id: str,
    host: str,
    case_dir: Path,
    mappings: dict[str, Mapping] | None = None,
) -> dict[str, Any]:
    """Parse one Velociraptor archive into the case (Parquet + DuckDB).

    Returns a summary dict (row counts per family, unmapped artifacts,
    warnings) stored in the manifest step details (A1: workers only writers).
    """
    mappings = mappings if mappings is not None else load_mappings()
    case_dir = Path(case_dir)
    warnings: list[str] = []
    unmapped: list[str] = []
    family_counts: dict[str, int] = {}
    rows_by_family: dict[str, list[dict[str, Any]]] = {}
    client_info: dict[str, Any] = {}
    ingested_at = utc_now()

    with zipfile.ZipFile(archive_path) as zf:
        names = zf.namelist()
        for name in names:
            if name.startswith("uploads/"):
                # Never read here: the extract step (work-order step 2) owns
                # uploads and enforces the zip-slip/bomb defences (T5). The
                # corpus plants a zip-slip entry name on purpose - it must
                # not prevent the fast lane from parsing results.
                continue
            _validate_entry_name(name)
            if not name.startswith(_ALLOWED_ENTRY_PREFIXES) or name.endswith("/"):
                warnings.append(f"ignored entry {name!r}")
        for name in names:
            if name == "client_info.json":
                client_info = json.loads(zf.read(name).decode("utf-8"))
                break

        expected_host = str(client_info.get("hostname", ""))
        if expected_host and expected_host != host:
            warnings.append(f"host mismatch: manifest={host!r} client_info={expected_host!r}")
        row_os = _row_os(client_info)

        for artifact_file in sorted(name for name in names if name.startswith("results/") and name.endswith(".json")):
            artifact = artifact_file.removeprefix("results/").removesuffix(".json")
            mapping = mappings.get(artifact)
            if mapping is None:
                unmapped.append(artifact)
                continue
            payload = zf.read(artifact_file).decode("utf-8")
            for line_number, line in enumerate(payload.splitlines(), start=1):
                line = line.strip()
                if not line:
                    continue
                source = json.loads(line)
                _emit(mapping, source, {
                    "case_id": case_id,
                    "ev_id": ev_id,
                    "host": host,
                    "os": row_os,
                    "source_path": artifact_file,
                    "source_ref": f"line:{line_number}",
                    "ingested_at": ingested_at,
                }, rows_by_family)

    counts = {family: len(rows) for family, rows in rows_by_family.items()}
    _write_rows(case_dir, ev_id, rows_by_family)
    return {
        "parser": f"velociraptor/{PARSER_VERSION}",
        "rows": sum(counts.values()),
        "families": counts,
        "unmapped_artifacts": unmapped,
        "warnings": warnings,
    }


def _emit(
    mapping: Mapping,
    source: dict[str, Any],
    ctx: dict[str, Any],
    rows_by_family: dict[str, list[dict[str, Any]]],
) -> None:
    from oreoa.normalize import raw_policy_for

    def base_row(record_ref: str) -> dict[str, Any]:
        row = {
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
            "parser_version": PARSER_VERSION,
            "mapping_version": str(mapping.version),
            "ingested_at": ctx["ingested_at"],
            "tags": [],
        }
        return row

    from oreoa.normalize import record_id as compute_record_id

    row = base_row(ctx["source_ref"])
    row.update(mapping.build_row(source, ctx["os"]))
    row["record_id"] = compute_record_id(ctx["ev_id"], mapping.forensic_artifact, ctx["source_ref"])
    row["extra"] = _extra(source, mapping.referenced_paths)
    row["raw"] = None if mapping.lossless else json.dumps(source, sort_keys=True, ensure_ascii=False)
    row["raw_policy"] = raw_policy_for(mapping.lossless)
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
        projected["record_id"] = compute_record_id(ctx["ev_id"], mapping.forensic_artifact, ref)
        projected["extra"] = _extra(source, mapping.referenced_paths)
        projected["raw"] = None if mapping.lossless else json.dumps(source, sort_keys=True, ensure_ascii=False)
        projected["raw_policy"] = raw_policy_for(mapping.lossless)
        projected["summary"] = _render_projection_summary(projection, projected)
        rows_by_family.setdefault(projection.family, []).append(projected)


def _render_projection_summary(projection, row: dict[str, Any]) -> str:
    from oreoa.mappings import SafeDict
    from oreoa.normalize import build_summary

    if not projection.summary_template:
        return ""
    return build_summary(projection.summary_tag, projection.summary_template.format_map(SafeDict(row)))


def _write_rows(case_dir: Path, ev_id: str, rows_by_family: dict[str, list[dict[str, Any]]]) -> None:
    for family, rows in sorted(rows_by_family.items()):
        db.write_parquet(case_dir, ev_id, family, rows)
    con = db.connect(case_dir)
    try:
        for family, _rows in sorted(rows_by_family.items()):
            if family in db.MATERIALIZED_FAMILIES:
                db.load_evidence_family(con, case_dir, ev_id, family)
        db.ensure_views(con, case_dir)
    finally:
        con.close()
