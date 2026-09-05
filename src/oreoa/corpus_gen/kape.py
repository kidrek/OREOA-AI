"""KAPE-style archive generator (step-2 quick-parser source, S1.6).

Emulates a KAPE collection containing **module outputs** (CSVs written by the
KAPE parsing modules) rather than raw collected binaries. Deliberate S1.6
scope (journalized): raw EVTX / registry hives / .pf binaries are NOT shipped
- no fast-lane consumer exists before plaso lands, and writing valid binary
formats is deferred to the deep-lane sub-step. The fast-lane signal travels in
the Velociraptor JSONL (``velociraptor.py``).

Archive layout (deterministic - sorted entries, fixed timestamps):

- ``_kape.cli``         module invocation list (text)
- ``README.txt``        deferral notice (raw formats land at the deep-lane
  sub-step; FR text - analyst-facing)
- ``Module_Output/MFT/MFT.csv``       from ``file`` events (+ derived
  directories); SI/FN timestamp sets drive H-AF-003 (timestomping)
- ``Module_Output/USN/USN.csv``       from ``fs_journal`` events
- ``Module_Output/Amcache/Amcache.csv`` from amcache ``execution`` events

CSV columns are documented per builder and consumed by the step-2 quick
parsers via ``mappings/kape/*.yaml`` (mappings land with those parsers).
"""

from __future__ import annotations

import csv
import io
import zipfile
from pathlib import Path

from oreoa.corpus_gen.scenario import Execution, FileArtifact, FsJournal, Scenario

KAPE_MODULES = "!MFTParser,!USNParser,!AmcacheParser"

MFT_COLUMNS: tuple[str, ...] = (
    "RecordNumber",
    "FileName",
    "ParentPath",
    "IsDirectory",
    "FileSize",
    "Attributes",
    "SI_Created",
    "SI_Modified",
    "SI_Accessed",
    "SI_MFT_Changed",
    "FN_Created",
    "FN_Modified",
    "FN_Accessed",
    "FN_MFT_Changed",
)
USN_COLUMNS: tuple[str, ...] = (
    "USN",
    "Timestamp",
    "FileName",
    "ParentPath",
    "Reason",
)
AMCACHE_COLUMNS: tuple[str, ...] = (
    "KeyPath",
    "Name",
    "Path",
    "Sha256",
    "Size",
    "LastWriteTimestamp",
    "Signer",
)

NT_RECORD_BASE = 6  # records 0-5 are reserved ($MFT..$Extend)


def iso(ts) -> str:
    from oreoa.corpus_gen.velociraptor import iso as _iso

    return _iso(ts) or ""


def _split_path(path: str) -> tuple[str, str]:
    """Return (parent_path, name) for a windows path."""
    normalized = path.replace("/", "\\").rstrip("\\")
    if "\\" not in normalized:
        return "", normalized
    parent, name = normalized.rsplit("\\", 1)
    return parent, name


def mft_rows(scenario: Scenario) -> list[dict[str, str]]:
    """Build MFT.csv rows: derived directories first, then files (sorted).

    Directories are derived from the parent paths of every file so the tree
    is complete. Record numbers are assigned in deterministic sorted order.
    """
    files = [
        event
        for event in scenario.expand_events()
        if isinstance(event, FileArtifact)
    ]
    directories: set[str] = set()
    for event in files:
        parent, name = _split_path(event.path)
        while name:
            directories.add(parent or "C:\\")
            parent, name = _split_path(parent)

    rows: list[dict[str, str]] = []
    record = NT_RECORD_BASE

    for directory in sorted(directories):
        parent, name = _split_path(directory.rstrip("\\"))
        rows.append(
            {
                "RecordNumber": str(record),
                "FileName": name or directory,
                "ParentPath": parent,
                "IsDirectory": "1",
                "FileSize": "0",
                "Attributes": "Directory",
                "SI_Created": iso(scenario.window_start),
                "SI_Modified": iso(scenario.window_start),
                "SI_Accessed": iso(scenario.window_start),
                "SI_MFT_Changed": iso(scenario.window_start),
                "FN_Created": iso(scenario.window_start),
                "FN_Modified": iso(scenario.window_start),
                "FN_Accessed": iso(scenario.window_start),
                "FN_MFT_Changed": iso(scenario.window_start),
            }
        )
        record += 1

    for event in sorted(files, key=lambda e: e.path.replace("/", "\\").lower()):
        parent, name = _split_path(event.path)
        si_created = event.si_created or event.ts_created
        si_modified = event.si_modified or event.ts_modified
        rows.append(
            {
                "RecordNumber": str(record),
                "FileName": name,
                "ParentPath": parent,
                "IsDirectory": "0",
                "FileSize": str(event.size or len(event.content.encode("utf-8"))),
                "Attributes": "Archive",
                "SI_Created": iso(si_created),
                "SI_Modified": iso(si_modified),
                "SI_Accessed": iso(si_modified or si_created),
                "SI_MFT_Changed": iso(event.ts_modified or si_created),
                # $FILE_NAME keeps the *real* times - the timestomping skew
                # lives in the SI set (H-AF-003).
                "FN_Created": iso(event.ts_created),
                "FN_Modified": iso(event.ts_modified),
                "FN_Accessed": iso(event.ts_modified or event.ts_created),
                "FN_MFT_Changed": iso(event.ts_modified or event.ts_created),
            }
        )
        record += 1
    return rows


def usn_rows(scenario: Scenario) -> list[dict[str, str]]:
    rows = []
    usn = 1000
    for event in scenario.expand_events():
        if isinstance(event, FsJournal):
            parent, name = _split_path(event.path)
            rows.append(
                {
                    "USN": str(usn),
                    "Timestamp": iso(event.ts_dt),
                    "FileName": name,
                    "ParentPath": parent,
                    "Reason": event.reason or event.op,
                }
            )
            usn += 1
    return rows


def amcache_rows(scenario: Scenario) -> list[dict[str, str]]:
    rows = []
    for event in scenario.expand_events():
        if isinstance(event, Execution) and event.source == "amcache":
            parent, name = _split_path(event.exe_path)
            rows.append(
                {
                    "KeyPath": f"File\\{parent}",
                    "Name": name,
                    "Path": event.exe_path,
                    "Sha256": event.hash_sha256,
                    "Size": "0",
                    "LastWriteTimestamp": iso(event.ts_last or event.ts_first),
                    "Signer": event.signer,
                }
            )
    return rows


def _csv_bytes(columns: tuple[str, ...], rows: list[dict[str, str]]) -> bytes:
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=list(columns), lineterminator="\r\n")
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    return buffer.getvalue().encode("utf-8")


def build_archive(scenario: Scenario, out_path: Path) -> None:
    """Write the deterministic KAPE-style zip (module outputs only)."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    stamp = scenario.window_start.timetuple()[:6]
    readme = (
        "OREOA-AI T0 corpus - KAPE collection v0 (S1.6)\n"
        "\n"
        "Portee S1.6 : sorties de modules uniquement (CSV). Les binaires bruts\n"
        "(EVTX, ruches de registre, .pf) sont reportes au sub-step deep lane -\n"
        "aucun consommateur fast lane avant plaso ; le signal fast voyage dans\n"
        "l'archive Velociraptor. Decision journalisee S1.6.\n"
    )
    files: dict[str, bytes] = {
        "_kape.cli": (KAPE_MODULES + "\n").encode("utf-8"),
        "README.txt": readme.encode("utf-8"),
        "Module_Output/MFT/MFT.csv": _csv_bytes(MFT_COLUMNS, mft_rows(scenario)),
        "Module_Output/USN/USN.csv": _csv_bytes(USN_COLUMNS, usn_rows(scenario)),
        "Module_Output/Amcache/Amcache.csv": _csv_bytes(AMCACHE_COLUMNS, amcache_rows(scenario)),
    }
    with zipfile.ZipFile(out_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for name in sorted(files):
            info = zipfile.ZipInfo(filename=name, date_time=stamp)
            info.external_attr = 0o644 << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            zf.writestr(info, files[name])
