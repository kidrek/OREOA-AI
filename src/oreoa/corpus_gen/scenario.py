"""Declarative scenario model (SPEC T0: "host, users, timeline of planted
events, expected detections").

A scenario is the single source of truth for every generator: the same
typed events drive the Velociraptor JSONL, the KAPE module CSVs and the NTFS
image. ``repeat`` expands one event into N deterministic rows ({i} is
substituted in string fields, ``ts`` advances by ``interval_seconds``).

Event types (closed list, S1.6 Windows scope):

- ``log_event``      raw EVTX row (Security/System/Sysmon) - lands in the
  Velociraptor results JSONL; the mapping layer projects EIDs into semantic
  families (executions/auth_events/accounts/persistence/network/fs_journal).
- ``execution``      prefetch / amcache / userassist row
- ``persistence``    run_key / service / scheduled_task row
- ``registry_value`` generic registry value row (IFEO, fodhelper, ...)
- ``browser``        history visit / download / extension row
- ``user_activity``  RecentDocs / LNK row
- ``file``           uploaded file body (Velociraptor uploads/ + KAPE
  Collected/ + MFT.csv row); ``on_image`` places it on the NTFS image;
  ``si_created``/``si_modified`` forge the $STANDARD_INFORMATION set
  (timestomping, H-AF-003)
- ``fs_journal``     USN journal row (USN.csv)

Traps are declared in ``traps``: the hallucination record id (an id that
looks valid but does not exist) and the locations of the prompt-injection
strings (the strings themselves are planted inline in the events above).
``expected_detections`` references hunts from ``hunts_catalog_seed.yaml``
with the lane that must satisfy them (``fast`` = S1.6 Velociraptor JSONL,
``step2`` = quick parsers (MFT/USN CSVs), ``deep`` = deep lane).

Languages: scenario files are code-adjacent data - English.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, Field, field_validator, model_validator

from oreoa.vocab import validate_closed

SCENARIO_VERSION = 1

EVENT_TYPES: tuple[str, ...] = (
    "log_event",
    "execution",
    "persistence",
    "registry_value",
    "browser",
    "user_activity",
    "file",
    "fs_journal",
)
EXECUTION_SOURCES: tuple[str, ...] = ("prefetch", "amcache", "userassist")
PERSISTENCE_MECHANISMS: tuple[str, ...] = ("run_key", "service", "scheduled_task")
BROWSER_ENTRY_TYPES: tuple[str, ...] = ("visit", "download", "extension")
USER_ACTIVITY_TYPES: tuple[str, ...] = ("recent_docs", "office_mru", "lnk", "rdp_cache")
FS_JOURNAL_OPS: tuple[str, ...] = ("create", "delete", "rename_old", "rename_new", "modify")
DETECTION_LANES: tuple[str, ...] = ("fast", "step2", "deep")
SCENARIO_KINDS: tuple[str, ...] = ("compromised", "clean")


def _parse_ts(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc).replace(tzinfo=None, microsecond=0)
    text = str(value).strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None:
        raise ValueError(f"scenario timestamps must be UTC-aware (Z), got {value!r}")
    return parsed.astimezone(timezone.utc).replace(tzinfo=None, microsecond=0)


class HostInfo(BaseModel):
    hostname: str = Field(min_length=1)
    fqdn: str = ""
    os: str = "windows"
    os_version: str = ""
    build: str = ""
    arch: str = "amd64"
    domain: str = ""
    tz: str = "Europe/Paris"
    clock_skew_seconds: int = 0
    ips: list[str] = Field(default_factory=list)

    @field_validator("os")
    @classmethod
    def _os_windows(cls, v: str) -> str:
        # S1.6 builds Windows scenarios only; Linux/macOS land at step 4.
        if v != "windows":
            raise ValueError(
                f"S1.6 corpus builds Windows scenarios only (got os={v!r}); "
                "Linux/macOS scenarios land at work-order step 4"
            )
        return v


class User(BaseModel):
    user_name: str
    user_id: str = ""
    user_id_type: str = "sid"
    full_name: str = ""
    is_admin: bool = False
    home: str = ""


class Repeat(BaseModel):
    count: int = Field(ge=2)
    interval_seconds: int = Field(gt=0)


class _Event(BaseModel):
    type: str
    ts: Any
    repeat: Repeat | None = None

    @field_validator("type")
    @classmethod
    def _type_closed(cls, v: str) -> str:
        return validate_closed("event type", v, EVENT_TYPES)

    @field_validator("ts")
    @classmethod
    def _ts(cls, v: Any) -> datetime:
        return _parse_ts(v)

    @property
    def ts_dt(self) -> datetime:
        return self.ts  # type: ignore[return-value]


class LogEvent(_Event):
    type: Literal["log_event"] = "log_event"
    channel: str
    provider: str = ""
    event_id: int | str
    level: str = "info"
    computer: str = ""
    message: str = ""
    fields: dict[str, Any] = Field(default_factory=dict)


class Execution(_Event):
    type: Literal["execution"] = "execution"
    source: str
    exe_path: str
    args: str = ""
    cmdline: str = ""
    ts_first: Any = None
    ts_last: Any = None
    run_count: int = Field(default=1, ge=1)
    hash_sha256: str = ""
    signer: str = ""
    loaded_files: list[str] = Field(default_factory=list)
    parent_path: str = ""
    pid: int = 0
    ppid: int = 0
    user_name: str = ""

    @field_validator("source")
    @classmethod
    def _source_closed(cls, v: str) -> str:
        return validate_closed("execution source", v, EXECUTION_SOURCES)

    @field_validator("ts_first", "ts_last")
    @classmethod
    def _opt_ts(cls, v: Any) -> datetime | None:
        return _parse_ts(v) if v else None


class Persistence(_Event):
    type: Literal["persistence"] = "persistence"
    mechanism: str
    name: str
    location: str = ""
    target_path: str = ""
    args: str = ""
    trigger: str = ""
    run_as: str = ""
    enabled: bool = True
    ts_created: Any = None
    ts_modified: Any = None
    hash_sha256: str = ""
    signer: str = ""

    @field_validator("mechanism")
    @classmethod
    def _mech_closed(cls, v: str) -> str:
        return validate_closed("persistence mechanism", v, PERSISTENCE_MECHANISMS)

    @field_validator("ts_created", "ts_modified")
    @classmethod
    def _opt_ts(cls, v: Any) -> datetime | None:
        return _parse_ts(v) if v else None


class RegistryValue(_Event):
    type: Literal["registry_value"] = "registry_value"
    hive: str
    key_path: str
    value_name: str
    value_type: str = "REG_SZ"
    value_data: str = ""
    user_name: str = ""


class Browser(_Event):
    type: Literal["browser"] = "browser"
    entry_type: str
    browser: str = "chrome"
    profile: str = "Default"
    url: str = ""
    domain: str = ""
    title: str = ""
    target_path: str = ""
    size: int | None = None
    ts_end: Any = None
    user_name: str = ""

    @field_validator("entry_type")
    @classmethod
    def _entry_closed(cls, v: str) -> str:
        return validate_closed("browser entry type", v, BROWSER_ENTRY_TYPES)

    @field_validator("ts_end")
    @classmethod
    def _opt_ts(cls, v: Any) -> datetime | None:
        return _parse_ts(v) if v else None


class UserActivity(_Event):
    type: Literal["user_activity"] = "user_activity"
    activity_type: str
    target_path: str
    source_app: str = ""
    user_name: str = ""

    @field_validator("activity_type")
    @classmethod
    def _activity_closed(cls, v: str) -> str:
        return validate_closed("user activity type", v, USER_ACTIVITY_TYPES)


class FileArtifact(_Event):
    type: Literal["file"] = "file"
    path: str
    content: str = ""
    size: int | None = None
    on_image: bool = False
    ts_created: Any = None
    ts_modified: Any = None
    # Forged $STANDARD_INFORMATION set (timestomping, H-AF-003): when set,
    # the MFT patcher writes these into $SI while $FILE_NAME keeps the real
    # scenario times.
    si_created: Any = None
    si_modified: Any = None

    @field_validator("ts_created", "ts_modified", "si_created", "si_modified")
    @classmethod
    def _opt_ts(cls, v: Any) -> datetime | None:
        return _parse_ts(v) if v else None

    @model_validator(mode="after")
    def _timestomp_consistency(self) -> FileArtifact:
        if (self.si_created or self.si_modified) and not self.ts_created:
            raise ValueError(f"file {self.path!r}: si_created requires ts_created")
        return self


class FsJournal(_Event):
    type: Literal["fs_journal"] = "fs_journal"
    op: str
    path: str
    reason: str = ""

    @field_validator("op")
    @classmethod
    def _op_closed(cls, v: str) -> str:
        return validate_closed("fs_journal op", v, FS_JOURNAL_OPS)


Event = (
    LogEvent
    | Execution
    | Persistence
    | RegistryValue
    | Browser
    | UserActivity
    | FileArtifact
    | FsJournal
)


class Trap(BaseModel):
    where: str
    pattern: str = ""


class Traps(BaseModel):
    """Declared corpus traps (SPEC T0 planted content)."""

    # A record id that looks valid but does not exist (T4 hallucination test).
    hallucination_record_id: str = Field(default="", pattern=r"^[0-9a-f]{64}$")
    # Where the prompt-injection strings are planted (labels, for tests).
    prompt_injection: list[Trap] = Field(default_factory=list)


class ExpectedDetection(BaseModel):
    # Area codes include digits (C2) - lesson from S1.5 (journalized).
    hunt: str = Field(pattern=r"^H-[A-Z0-9]{2}-\d{3}$")
    lane: str
    note: str = ""

    @field_validator("lane")
    @classmethod
    def _lane_closed(cls, v: str) -> str:
        return validate_closed("detection lane", v, DETECTION_LANES)


class Scenario(BaseModel):
    version: int = SCENARIO_VERSION
    name: str = Field(pattern=r"^[a-z0-9][a-z0-9-]+$")
    kind: str
    host: HostInfo
    users: list[User] = Field(default_factory=list)
    window: dict[str, Any]
    events: list[Event] = Field(default_factory=list)
    traps: Traps = Field(default_factory=Traps)
    expected_detections: list[ExpectedDetection] = Field(default_factory=list)

    @field_validator("kind")
    @classmethod
    def _kind_closed(cls, v: str) -> str:
        return validate_closed("scenario kind", v, SCENARIO_KINDS)

    @model_validator(mode="after")
    def _window_shape(self) -> Scenario:
        if set(self.window) != {"start", "end"}:
            raise ValueError("window must have exactly start and end")
        start, end = _parse_ts(self.window["start"]), _parse_ts(self.window["end"])
        if end <= start:
            raise ValueError("window end must be after start")
        object.__setattr__(self, "window", {"start": start, "end": end})
        return self

    # Convenience accessors (window is normalized to datetimes above).
    @property
    def window_start(self) -> datetime:
        return self.window["start"]  # type: ignore[return-value]

    @property
    def window_end(self) -> datetime:
        return self.window["end"]  # type: ignore[return-value]

    @model_validator(mode="after")
    def _clean_host_has_no_detection(self) -> Scenario:
        if self.kind == "clean" and self.expected_detections:
            raise ValueError("clean scenarios must not expect detections")
        return self

    def expand_events(self) -> list[Event]:
        """Expand ``repeat`` blocks deterministically ({i} substitution).

        The expanded list replaces the original events; identical scenarios
        always expand to identical lists.
        """
        expanded: list[Event] = []
        for event in self.events:
            if event.repeat is None:
                expanded.append(event)
                continue
            interval = timedelta(seconds=event.repeat.interval_seconds)
            for i in range(event.repeat.count):
                delta = {
                    "type": event.type,
                    "ts": event.ts_dt + i * interval,
                    "repeat": None,
                }
                payload = event.model_dump(exclude={"ts", "repeat"})
                payload.pop("repeat", None)
                payload = {
                    key: (value.format(i=i) if isinstance(value, str) else value)
                    for key, value in payload.items()
                }
                payload.update(delta)
                expanded.append(type(event).model_validate(payload))
        return expanded


def load_scenario(path: Path) -> Scenario:
    """Load and validate one ``corpus/scenarios/<name>.yaml`` file."""
    payload = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"scenario {path} must be a YAML mapping")
    scenario = Scenario.model_validate(payload)
    if scenario.name != Path(path).stem:
        raise ValueError(f"scenario name {scenario.name!r} does not match file stem {Path(path).stem!r}")
    return scenario


def load_scenarios(directory: Path) -> list[Scenario]:
    """Load every scenario of a directory, sorted by name (deterministic)."""
    return [
        load_scenario(path)
        for path in sorted(Path(directory).glob("*.yaml"))
    ]
