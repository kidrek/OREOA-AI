"""Velociraptor offline-collector archive generator (fast-lane source, S1.6).

Emulates the shape of a Velociraptor offline collector zip (``results/*.json``
JSONL + ``uploads/`` + client metadata). The row shapes below are the corpus
contract consumed by ``mappings/velociraptor/*.yaml``; they follow Velociraptor
conventions and are verified against a real collector archive when real
exercise collections land (work-order step 2 - journalized S1.6 arbitration).

Row shapes per ``results/<artifact>.json`` (one JSON object per line):

- ``Windows.EventLogs.EvtxHunter``:
  {EventTime, Channel, Provider, EventID, Level, Computer, EventRecordID,
   EventData{...}}
- ``Windows.System.Prefetch``:
  {PrefetchPath, SourceFilename, RunCount, Times[...], FilesLoaded[...],
   PrefetchHash}
- ``Windows.Sys.Amcache``:
  {Path, Name, Sha256, Size, FileKeyLastWriteTimestamp, Signer}
- ``Windows.Registry.Run``:
  {Hive, KeyPath, ValueName, Value, LastWriteTimestamp}
- ``Windows.Sys.Services``:
  {Name, DisplayName, PathName, StartMode, State, Account, ProcessId}
- ``Windows.System.TaskScheduler``:
  {TaskPath, Name, Action, Trigger, Author, Enabled}
- ``Windows.Registry.AllValues``:
  {Hive, KeyPath, ValueName, ValueType, ValueData, LastWriteTimestamp}
- ``Windows.Registry.RecentDocs``:
  {Hive, KeyPath, ValueName, ValueData, LastWriteTimestamp}
- ``Windows.Applications.Chrome.History``:
  {Profile, EntryType, VisitTime, URL, Title, VisitCount, TargetPath,
   TotalBytes, State}
- ``Windows.Applications.Chrome.Extensions``:
  {Profile, Name, ID, Path, Permissions, Version, InstallTime}

Archive layout (deterministic - sorted entries, fixed timestamps):

- ``client_info.json`` {hostname, fqdn, os, os_version, build, arch, ips}
- ``server_info.json``
- ``results/<artifact>.json`` (JSONL)
- ``uploads/<windows path under C:/>`` file bodies from ``file`` events
- trap fixtures (SPEC T0): a zip-slip entry name, a compressible bomb, a
  tamper pair (file + expected hash that mismatches) - all declared in
  ``_OREOA_TRAPS.json``; the S1.6 parser only reads ``results/`` and refuses
  to extract uploads (the ``extract`` step, work-order step 2, owns them).

Timestamps render as ``...Z`` ISO-8601 UTC, microsecond precision.
"""

from __future__ import annotations

import hashlib
import json
import zipfile
from datetime import datetime
from pathlib import Path, PurePosixPath
from typing import Any

from oreoa.corpus_gen.scenario import (
    Browser,
    Execution,
    FileArtifact,
    LogEvent,
    Persistence,
    RegistryValue,
    Scenario,
    UserActivity,
)

VR_VERSION = "0.73.3 (oreoa synthetic corpus)"

ZIP_SLIP_ENTRY = "uploads/../../../../oreoa_zipslip_probe.txt"
BOMB_ENTRY = "uploads/C:/Users/j.dupont/AppData/Local/Temp/deep_zero.bin"
BOMB_SIZE_BYTES = 32 * 1024 * 1024
TAMPER_ENTRY = "uploads/C:/Users/j.dupont/Documents/hash_mismatch.bin"
TRAPS_ENTRY = "_OREOA_TRAPS.json"


def iso(ts: datetime | None) -> str | None:
    if ts is None:
        return None
    return ts.strftime("%Y-%m-%dT%H:%M:%S.%f") + "Z"


def _filetime_hash(scenario: Scenario, seed: str) -> str:
    """Stable synthetic hash derived from the scenario name + seed."""
    material = f"{scenario.name}|{seed}".encode("utf-8")
    return hashlib.sha256(material).hexdigest()


def _ts(event) -> datetime:
    return event.ts_dt


class _ResultFiles:
    """Deterministic per-artifact row buffers + EventRecordID counters."""

    def __init__(self) -> None:
        self.rows: dict[str, list[dict[str, Any]]] = {}
        self._record_ids: dict[str, int] = {}

    def next_record_id(self, channel: str) -> int:
        current = self._record_ids.get(channel, 1000) + 1
        self._record_ids[channel] = current
        return current

    def add(self, artifact: str, row: dict[str, Any]) -> None:
        self.rows.setdefault(artifact, []).append(row)

    def items(self) -> list[tuple[str, list[dict[str, Any]]]]:
        return sorted(self.rows.items())


def build_results(scenario: Scenario) -> _ResultFiles:
    """Map scenario events onto the results JSONL rows (order = event order)."""
    results = _ResultFiles()
    computer = scenario.host.fqdn or scenario.host.hostname

    for event in scenario.expand_events():
        match event:
            case LogEvent():
                results.add(
                    "Windows.EventLogs.EvtxHunter",
                    {
                        "EventTime": iso(_ts(event)),
                        "Channel": event.channel,
                        "Provider": event.provider,
                        "EventID": int(event.event_id),
                        "Level": event.level,
                        "Computer": event.computer or computer,
                        "EventRecordID": results.next_record_id(event.channel),
                        "EventData": event.fields,
                    },
                )
            case Execution():
                if event.source == "prefetch":
                    results.add(
                        "Windows.System.Prefetch",
                        {
                            "PrefetchPath": f"C:\\Windows\\Prefetch\\{_prefetch_name(event.exe_path)}",
                            "SourceFilename": event.exe_path,
                            "RunCount": event.run_count,
                            "Times": [iso(event.ts_first or _ts(event)), iso(event.ts_last or event.ts_first or _ts(event))],
                            "FilesLoaded": event.loaded_files,
                            "PrefetchHash": _filetime_hash(scenario, event.exe_path),
                        },
                    )
                elif event.source == "amcache":
                    results.add(
                        "Windows.Sys.Amcache",
                        {
                            "Path": event.exe_path,
                            "Name": event.exe_path.rsplit("\\", 1)[-1],
                            "Sha256": event.hash_sha256 or _filetime_hash(scenario, "amcache|" + event.exe_path),
                            "Size": 0,
                            "FileKeyLastWriteTimestamp": iso(event.ts_last or _ts(event)),
                            "Signer": event.signer,
                        },
                    )
                else:
                    # userassist: no consumer at S1.6 (no planted hunt); emit
                    # nothing rather than a fake shape - journalized S1.6.
                    pass
            case Persistence():
                if event.mechanism == "run_key":
                    results.add(
                        "Windows.Registry.Run",
                        {
                            "Hive": "NTUSER",
                            "KeyPath": "Software\\Microsoft\\Windows\\CurrentVersion\\Run",
                            "ValueName": event.name,
                            "Value": f"{event.target_path} {event.args}".strip(),
                            "LastWriteTimestamp": iso(event.ts_modified or event.ts_created or _ts(event)),
                        },
                    )
                elif event.mechanism == "service":
                    results.add(
                        "Windows.Sys.Services",
                        {
                            "Name": event.name,
                            "DisplayName": event.name,
                            "PathName": f"{event.target_path} {event.args}".strip(),
                            "StartMode": event.trigger or "auto",
                            "State": "running" if event.enabled else "stopped",
                            "Account": event.run_as or "LocalSystem",
                            "ProcessId": 0,
                        },
                    )
                else:  # scheduled_task
                    results.add(
                        "Windows.System.TaskScheduler",
                        {
                            "TaskPath": event.location or "\\",
                            "Name": event.name,
                            "Action": f"{event.target_path} {event.args}".strip(),
                            "Trigger": event.trigger or "logon",
                            "Author": event.run_as or "CORP\\jdupont",
                            "Enabled": event.enabled,
                        },
                    )
            case RegistryValue():
                results.add(
                    "Windows.Registry.AllValues",
                    {
                        "Hive": event.hive,
                        "KeyPath": event.key_path,
                        "ValueName": event.value_name,
                        "ValueType": event.value_type,
                        "ValueData": event.value_data,
                        "LastWriteTimestamp": iso(_ts(event)),
                    },
                )
            case Browser():
                if event.entry_type in ("visit", "download"):
                    results.add(
                        "Windows.Applications.Chrome.History",
                        {
                            "Profile": event.profile,
                            "EntryType": event.entry_type,
                            "VisitTime": iso(_ts(event)),
                            "URL": event.url,
                            "Domain": event.domain,
                            "Title": event.title,
                            "VisitCount": 1,
                            "TargetPath": event.target_path,
                            "TotalBytes": event.size or 0,
                            "State": "complete",
                        },
                    )
                else:  # extension (url = permissions, domain = extension id)
                    results.add(
                        "Windows.Applications.Chrome.Extensions",
                        {
                            "Profile": event.profile,
                            "Name": event.title,
                            "ID": event.domain,
                            "Path": event.target_path,
                            "Permissions": event.url,
                            "Version": "1.0",
                            "InstallTime": iso(_ts(event)),
                        },
                    )
            case UserActivity():
                results.add(
                    "Windows.Registry.RecentDocs",
                    {
                        "Hive": "NTUSER",
                        "KeyPath": f"Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\RecentDocs\\{event.activity_type}",
                        "ValueName": event.target_path,
                        "ValueData": event.source_app,
                        "LastWriteTimestamp": iso(_ts(event)),
                    },
                )
            case FileArtifact():
                pass  # uploads are handled in build_archive
            case _:
                pass
    return results


def _prefetch_name(exe_path: str) -> str:
    base = exe_path.rsplit("\\", 1)[-1].upper()
    stem = base.rsplit(".", 1)[0]
    return f"{stem}.EXE-{_prefetch_hash(exe_path)}.pf"


def _prefetch_hash(exe_path: str) -> str:
    return hashlib.sha1(exe_path.encode("utf-8")).hexdigest()[:8].upper()


def file_body(event: FileArtifact, scenario: Scenario) -> bytes:
    """Deterministic file body from a ``file`` event."""
    if event.size is not None and event.size > len(event.content.encode("utf-8")):
        pad = (event.size - len(event.content.encode("utf-8"))) * b"\x00"
        return event.content.encode("utf-8") + pad
    return event.content.encode("utf-8")


def uploads(scenario: Scenario) -> list[tuple[str, bytes]]:
    """Velociraptor uploads entries from ``file`` events (sorted, deterministic).

    Windows paths are stored under ``uploads/C:/...`` (Velociraptor collector
    convention for uploads coming from the client file system).
    """
    entries: list[tuple[str, bytes]] = []
    for event in scenario.expand_events():
        if isinstance(event, FileArtifact):
            windows_path = event.path.replace("/", "\\")
            entries.append(("uploads/C:" + windows_path, file_body(event, scenario)))
    return sorted(entries)


def build_client_info(scenario: Scenario) -> dict[str, Any]:
    host = scenario.host
    return {
        "hostname": host.hostname,
        "fqdn": host.fqdn or host.hostname,
        "os": host.os,
        "os_version": host.os_version,
        "build": host.build,
        "arch": host.arch,
        "ips": host.ips,
        "velociraptor_version": VR_VERSION,
    }


def build_archive(scenario: Scenario, out_path: Path) -> dict[str, Any]:
    """Write the deterministic offline-collector zip; returns trap metadata."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    results = build_results(scenario)
    stamp = scenario.window_start.timetuple()[:6]
    upload_entries = uploads(scenario)
    bomb = b"\x00" * BOMB_SIZE_BYTES
    tamper = b"oreoa tamper fixture: the manifest hash of this file must NOT match\n"
    tamper_sha256 = hashlib.sha256(tamper).hexdigest()
    declared_tamper = _filetime_hash(scenario, "hash-mismatch")

    # The tamper fixture declares a WRONG expected sha256 (a scenario-derived
    # value): the pipeline hash step (registered by /ingest, work-order step 2)
    # must report the mismatch instead of silently ingesting.
    traps = {
        "zip_slip_entry": ZIP_SLIP_ENTRY,
        "bomb_entry": BOMB_ENTRY,
        "bomb_size_bytes": BOMB_SIZE_BYTES,
        "tamper_entry": TAMPER_ENTRY,
        "tamper_declared_sha256": declared_tamper,
        "tamper_actual_sha256": tamper_sha256,
        "hallucination_record_id": scenario.traps.hallucination_record_id,
        "prompt_injection": [trap.model_dump() for trap in scenario.traps.prompt_injection],
    }

    files: dict[str, bytes] = {
        "client_info.json": json.dumps(build_client_info(scenario), indent=2, sort_keys=True).encode("utf-8") + b"\n",
        "server_info.json": json.dumps({"version": VR_VERSION}, indent=2, sort_keys=True).encode("utf-8") + b"\n",
        TRAPS_ENTRY: json.dumps(traps, indent=2, sort_keys=True).encode("utf-8") + b"\n",
    }
    for artifact, rows in results.items():
        lines = "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows)
        files[f"results/{artifact}.json"] = lines.encode("utf-8")
    for name, body in upload_entries:
        files[name] = body
    files[BOMB_ENTRY] = bomb
    files[TAMPER_ENTRY] = tamper
    files[ZIP_SLIP_ENTRY] = b"oreoa zip-slip probe (must never be extracted)\n"

    with zipfile.ZipFile(out_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for name in sorted(files):
            info = zipfile.ZipInfo(filename=name, date_time=stamp)
            info.external_attr = 0o644 << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            zf.writestr(info, files[name])
    return traps
