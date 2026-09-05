"""Fast-lane parser: KAPE module-output archive -> Parquet.

S2.1 (work-order step 2): reads ``Module_Output/*.csv`` module outputs from
a KAPE collection zip and maps the rows through ``mappings/kape/`` into the
normalized families - same contract as the S1.6 Velociraptor parser
(shared ``oreoa.parse_common`` + ``db.write_parsed_rows``):

- deterministic ``record_id`` = sha256(ev_id | forensic_artifact | source_ref),
  ``source_ref`` = ``csv:<entry>:<data row index>`` (1-based, header excluded;
  counts parsed data rows, so a quoted field containing a newline stays
  deterministic);
- idempotent: re-parsing the same evidence replaces its rows;
- ``lossless: true`` mappings (MFT/USN/Amcache, SPEC storage tiers): every
  source column is projected, ``raw`` stays NULL, round-trip tested;
- the archive is consumed in place: nothing is extracted (the ``extract``
  step owns extraction); only the whitelisted entries are read, entry names
  with ``..`` segments are refused (zip-slip defence, T5);
- the LLM never sees this layer (SPEC): output is Parquet + DuckDB only.

Row OS is ``windows``: KAPE collections are Windows-only by construction
(S2.1 arbitration, journalized; revisited when the ``detect`` step stores
the OS in the manifest). ``FullPath`` = ``ParentPath\\FileName`` is composed
parser-side before mapping (S2.1 arbitration) so the mapping stays pure data;
the source columns remain individually re-derivable (round-trip tests).
"""

from __future__ import annotations

import csv
import io
import zipfile
from pathlib import Path
from typing import Any

from oreoa import db
from oreoa.mappings import Mapping, load_mappings, utc_now
from oreoa.parse_common import emit_row, validate_entry_name

PARSER_VERSION = "1.0.0"
_ROW_OS = "windows"

_ALLOWED_ENTRY_PREFIXES = ("_kape.cli", "README.txt", "Module_Output/")

# Module-output CSV -> mapping artifact id (lookup key in ``mappings/kape/``).
CSV_ARTIFACTS: dict[str, str] = {
    "Module_Output/MFT/MFT.csv": "kape.MFT",
    "Module_Output/USN/USN.csv": "kape.USN",
    "Module_Output/Amcache/Amcache.csv": "kape.Amcache",
}

# Entries whose rows get the parser-side FullPath composition.
_PARENT_FIELDS = frozenset({"Module_Output/MFT/MFT.csv", "Module_Output/USN/USN.csv"})


def _compose_full_path(source: dict[str, Any]) -> None:
    """Add ``FullPath`` (``ParentPath`` + ``FileName``) to the row dict."""
    parent = str(source.get("ParentPath") or "").rstrip("\\")
    name = str(source.get("FileName") or "")
    source["FullPath"] = f"{parent}\\{name}" if parent else name


def parse_archive(
    archive_path: Path,
    case_id: str,
    ev_id: str,
    host: str,
    case_dir: Path,
    mappings: dict[str, Mapping] | None = None,
) -> dict[str, Any]:
    """Parse one KAPE module-output archive into the case (Parquet + DuckDB).

    Returns a summary dict (row counts per family, unmapped CSVs, warnings)
    stored in the manifest step details (A1: workers only writers).
    """
    mappings = mappings if mappings is not None else load_mappings()
    case_dir = Path(case_dir)
    warnings: list[str] = []
    unmapped: list[str] = []
    rows_by_family: dict[str, list[dict[str, Any]]] = {}
    ingested_at = utc_now()

    with zipfile.ZipFile(archive_path) as zf:
        names = zf.namelist()
        for name in names:
            if name.endswith("/"):
                continue
            validate_entry_name(name)
            if not name.startswith(_ALLOWED_ENTRY_PREFIXES):
                warnings.append(f"ignored entry {name!r}")
            elif name.startswith("Module_Output/") and name.endswith(".csv") and name not in CSV_ARTIFACTS:
                warnings.append(f"no parser mapping for CSV entry {name!r}")

        for entry, artifact in sorted(CSV_ARTIFACTS.items()):
            if entry not in names:
                continue
            mapping = mappings.get(artifact)
            if mapping is None:
                unmapped.append(entry)
                continue
            payload = zf.read(entry).decode("utf-8")
            rows = list(csv.DictReader(io.StringIO(payload, newline="")))
            for index, source in enumerate(rows, start=1):
                if None in source:
                    warnings.append(f"{entry}: row {index} has unexpected extra columns")
                if entry in _PARENT_FIELDS:
                    _compose_full_path(source)
                emit_row(mapping, source, {
                    "case_id": case_id,
                    "ev_id": ev_id,
                    "host": host,
                    "os": _ROW_OS,
                    "source_path": entry,
                    "source_ref": f"csv:{entry}:{index}",
                    "parser_version": PARSER_VERSION,
                    "ingested_at": ingested_at,
                }, rows_by_family)

    counts = {family: len(rows) for family, rows in rows_by_family.items()}
    db.write_parsed_rows(case_dir, ev_id, rows_by_family)
    return {
        "parser": f"kape/{PARSER_VERSION}",
        "rows": sum(counts.values()),
        "families": counts,
        "unmapped_artifacts": unmapped,
        "warnings": warnings,
    }
