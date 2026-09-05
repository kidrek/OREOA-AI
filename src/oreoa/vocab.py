"""Closed vocabularies of the normalized data model (normalized_data_model.md).

Controlled vocabularies are closed lists (data-model principle 7): a value
outside a vocabulary is an error, never a silent mapping; anything else goes
to ``extra`` and the ingest reports it as an unmapped value so the vocabulary
can be extended deliberately (PR).

External knowledge vocabularies (forensic_artifacts, attack, dfiq) are DATA:
the accepted sets are injected by the caller. The knowledge snapshot lands via
``make update-knowledge`` (work-order step 1.5); until then, tests and call
sites pass explicit sets (fixtures). This module provides the validation API,
the id patterns and the closed column vocabularies.

Column vocabulary tuples are consumed by ``oreoa.db`` to build the matching
DuckDB ENUM types; the two stay aligned (tests/unit/test_db.py enforces it).
"""

from __future__ import annotations

import re
from collections.abc import Iterable

EV_ID_PATTERN = r"^EV-\d{3,}$"
CASE_ID_PATTERN = r"^[0-9]{4}-[0-9]{2}-(?:INC|EXE)-[0-9]{3,}$|^[A-Za-z0-9._-]{3,64}$"
HUNT_ID_PATTERN = r"^H-[A-Z]{2}-\d{3}$"
CUSTOM_ARTIFACT_PATTERN = r"^custom:[A-Za-z0-9][A-Za-z0-9._-]*$"
ATTACK_ID_PATTERN = r"^T\d{4}(?:\.\d{3})?$"
DFIQ_ID_PATTERN = r"^[QFS][01]\d{3}$"
SHA256_PATTERN = r"^[0-9a-f]{64}$"
GUID_PATTERN = r"^[0-9A-F]{32}[0-9]+$"

FAMILIES: tuple[str, ...] = (
    "fs_entries",
    "fs_journal",
    "log_events",
    "executions",
    "processes",
    "persistence",
    "accounts",
    "auth_events",
    "browser",
    "user_activity",
    "network",
    "installed_software",
    "registry",
    "config_entries",
    "files_of_interest",
    "detections",
    "iocs",
)

OS: tuple[str, ...] = ("windows", "linux", "macos", "android", "ios", "unknown")
USER_ID_TYPE: tuple[str, ...] = ("sid", "uid", "guid", "email", "unknown")
SOURCE_TOOL: tuple[str, ...] = (
    "velociraptor",
    "plaso",
    "dissect",
    "hayabusa",
    "zircolite",
    "volatility3",
    "hindsight",
    "manual",
)
TS_DESC: tuple[str, ...] = (
    "created",
    "modified",
    "accessed",
    "metadata_changed",
    "executed",
    "first_run",
    "last_run",
    "logged",
    "visited",
    "downloaded",
    "logon",
    "logoff",
    "installed",
    "deleted",
    "renamed",
    "connected",
    "written",
    "other",
)
FS_JOURNAL_OP: tuple[str, ...] = (
    "create",
    "delete",
    "rename_old",
    "rename_new",
    "modify",
    "truncate",
    "attr_change",
    "security_change",
    "hardlink",
    "other",
)
LOG_LEVEL: tuple[str, ...] = ("critical", "error", "warning", "info", "verbose", "unknown")
EXECUTION_EVIDENCE_TYPE: tuple[str, ...] = (
    "prefetch",
    "amcache",
    "shimcache",
    "bam",
    "userassist",
    "srum",
    "shell_history",
    "quarantine",
    "process_creation_log",
    "audit",
    "other",
)
PERSISTENCE_MECHANISM: tuple[str, ...] = (
    "run_key",
    "service",
    "scheduled_task",
    "wmi_subscription",
    "winlogon",
    "ifeo",
    "startup_folder",
    "cron",
    "systemd_unit",
    "systemd_timer",
    "rc_script",
    "launch_agent",
    "launch_daemon",
    "login_item",
    "kext",
    "driver",
    "browser_extension",
    "shell_profile",
    "other",
)
AUTH_EVENT_TYPE: tuple[str, ...] = (
    "logon_success",
    "logon_failure",
    "logoff",
    "explicit_credentials",
    "privilege_assigned",
    "ticket_request",
    "ticket_granted",
    "password_change",
    "sudo",
    "su",
    "lock",
    "unlock",
    "other",
)
AUTH_OUTCOME: tuple[str, ...] = ("success", "failure", "unknown")
BROWSER: tuple[str, ...] = ("chrome", "edge", "brave", "firefox", "safari", "opera", "other")
BROWSER_ENTRY_TYPE: tuple[str, ...] = (
    "visit",
    "download",
    "cookie",
    "extension",
    "bookmark",
    "search",
    "form",
    "cache",
    "session",
)
USER_ACTIVITY_TYPE: tuple[str, ...] = (
    "lnk",
    "jumplist",
    "shellbag",
    "mru",
    "recent_docs",
    "office_mru",
    "search_query",
    "rdp_cache",
    "spotlight",
    "recent_items",
    "editor_history",
    "other",
)
NETWORK_ENTRY_TYPE: tuple[str, ...] = (
    "connection",
    "listening",
    "dns_cache",
    "hosts_entry",
    "arp",
    "wifi_profile",
    "interface",
    "vpn_profile",
    "firewall_rule",
    "flow",
    "other",
)
SOFTWARE_SOURCE: tuple[str, ...] = (
    "uninstall_key",
    "msi",
    "dpkg",
    "rpm",
    "brew",
    "app_bundle",
    "store",
    "driver",
)
REGISTRY_HIVE: tuple[str, ...] = (
    "SYSTEM",
    "SOFTWARE",
    "SAM",
    "SECURITY",
    "NTUSER",
    "UsrClass",
    "Amcache",
    "other",
)
DETECTION_ENGINE: tuple[str, ...] = ("sigma", "hunt", "yara", "ioc", "analyst", "agent")
DETECTION_LEVEL: tuple[str, ...] = ("informational", "low", "medium", "high", "critical")
DETECTION_STATUS: tuple[str, ...] = ("new", "reviewed", "lead", "finding", "false_positive")
IOC_TYPE: tuple[str, ...] = (
    "ip",
    "domain",
    "url",
    "md5",
    "sha1",
    "sha256",
    "email",
    "filename",
    "path",
    "registry_key",
    "mutex",
    "user_agent",
    "account",
    "other",
)
CONFIDENCE: tuple[str, ...] = ("low", "medium", "high")
CRITICITY: tuple[str, ...] = ("low", "medium", "high")
ENTITY_TYPE: tuple[str, ...] = (
    "host",
    "user",
    "file",
    "hash",
    "ip",
    "domain",
    "url",
    "process",
    "account",
    "key",
)
RELATION: tuple[str, ...] = (
    "executed",
    "created",
    "deleted",
    "connected_to",
    "logged_on",
    "persisted_via",
    "downloaded",
    "spawned",
    "modified",
)
RAW_POLICY: tuple[str, ...] = ("kept", "omitted_lossless")

EVIDENCE_KIND: tuple[str, ...] = (
    "archive_velociraptor",
    "archive_kape",
    "disk_image",
    "memory_image",
    "directory",
)
CONTAINER_FORMAT: tuple[str, ...] = ("raw", "e01", "vmdk", "vhdx", "qcow2", "split")
ENCRYPTION: tuple[str, ...] = ("none", "bitlocker", "luks1", "luks2", "filevault", "unknown")
PROTECTOR_TYPE: tuple[str, ...] = ("password", "recovery_key", "tpm_only", "clear_key", "keyfile")
UNLOCK_STATUS: tuple[str, ...] = ("not_needed", "key_required", "unlocked", "failed")
KEY_TYPE: tuple[str, ...] = ("password", "recovery_key", "bek", "keyfile", "clear")
SYMBOL_STATUS: tuple[str, ...] = ("not_needed", "present", "missing")
STEP_STATUS: tuple[str, ...] = ("pending", "running", "ok", "failed", "skipped")

VOCABULARIES: dict[str, tuple[str, ...]] = {
    name: values
    for name, values in list(globals().items())
    if isinstance(values, tuple) and name.isupper() and name not in ("VOCABULARIES",)
}


class VocabularyError(ValueError):
    """A value is outside a closed vocabulary (data-model principle 7)."""


def validate_closed(name: str, value: str, values: tuple[str, ...] | frozenset[str]) -> str:
    if value not in values:
        raise VocabularyError(f"{value!r} outside closed vocabulary {name}")
    return value


def validate_artifact(name: str, known: Iterable[str] = ()) -> str:
    """ForensicArtifacts vocabulary; ``custom:<name>`` is the internal escape hatch.

    ``known`` is the injected ForensicArtifacts name set (knowledge snapshot at
    step 1.5, fixtures until then). An empty ``known`` only validates the
    ``custom:`` form and rejects everything else as unknown.
    """
    if name.startswith("custom:"):
        if not re.fullmatch(CUSTOM_ARTIFACT_PATTERN, name):
            raise VocabularyError(f"{name!r} is not a valid custom artifact name")
        return name
    if name not in frozenset(known):
        raise VocabularyError(
            f"artifact {name!r} outside forensic_artifacts vocabulary "
            "(use custom:<name> with a definition in knowledge/custom/artifacts/)"
        )
    return name


def validate_attack_id(technique_id: str, known: Iterable[str] = ()) -> str:
    if not re.fullmatch(ATTACK_ID_PATTERN, technique_id):
        raise VocabularyError(f"{technique_id!r} is not a valid ATT&CK technique id")
    known_set = frozenset(known)
    if known_set and technique_id not in known_set:
        raise VocabularyError(f"{technique_id!r} outside attack vocabulary")
    return technique_id


def validate_dfiq_id(dfiq_id: str, known: Iterable[str] = ()) -> str:
    if not re.fullmatch(DFIQ_ID_PATTERN, dfiq_id):
        raise VocabularyError(f"{dfiq_id!r} is not a valid DFIQ id (Q/F/S x 0=internal, 1=official)")
    known_set = frozenset(known)
    if known_set and dfiq_id not in known_set:
        raise VocabularyError(f"{dfiq_id!r} outside dfiq vocabulary (official + internal range)")
    return dfiq_id


def validate_attack_ids(technique_ids: Iterable[str], known: Iterable[str] = ()) -> tuple[str, ...]:
    return tuple(validate_attack_id(t, known) for t in technique_ids)


def validate_dfiq_ids(dfiq_ids: Iterable[str], known: Iterable[str] = ()) -> tuple[str, ...]:
    return tuple(validate_dfiq_id(q, known) for q in dfiq_ids)
