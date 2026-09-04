"""Pydantic payloads for Redis/RQ pipeline jobs (SPEC pipeline + lines 111/168).

Job payloads crossing the Redis boundary are validated models; an
unvalidatable payload is rejected at enqueue time. Mutating payloads carry
``confirmed_by_analyst=true`` exactly like ``case.yaml`` mutations (A1).

Key material never travels through jobs: the ``unlock`` worker reads
``state/keys/<EV-id>.yaml`` (mode 0600, mounted ro into workers only); the
value is absent from the payload, the journal, reports, exports and every
MCP result (SPEC line 111).
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from oreoa.vocab import EV_ID_PATTERN, KEY_TYPE, validate_closed

QueueName = Literal["fast", "deep", "fetch"]

JobType = Literal[
    "hash",
    "detect",
    "inventory",
    "extract",
    "parse",
    "sigma",
    "yara",
    "clamav",
    "events",
    "hunts",
    "rank_signals",
    "dissect",
    "plaso",
    "volatility",
    "binary_triage",
    "vss",
    "unlock",
    "fetch_symbol",
]

KNOWN_KERNEL_PDBS: frozenset[str] = frozenset({"ntkrnlmp.pdb", "ntkrpamp.pdb"})


class FetchSymbolPayload(BaseModel):
    """Optional symbol-fetch profile (Windows only; SPEC knowledge sources).

    The only data leaving the host is the kernel GUID. ``pdbconv`` converts
    the PDB to an ISF on the fetcher; the analyst confirmation gate is
    mandatory and the payload is refused without it.
    """

    pdb_name: str
    guid: str = Field(pattern=r"^[0-9A-F]{32}[0-9]+$")
    confirmed_by_analyst: bool

    @field_validator("pdb_name")
    @classmethod
    def _known_pdb(cls, v: str) -> str:
        if v not in KNOWN_KERNEL_PDBS:
            raise ValueError(f"pdb_name {v!r} outside known kernel PDBs (extend via PR)")
        return v

    @model_validator(mode="after")
    def _confirmation_required(self) -> FetchSymbolPayload:
        if not self.confirmed_by_analyst:
            raise ValueError("fetch_symbol requires confirmed_by_analyst=true (A1 mutation gate)")
        return self


class UnlockPayload(BaseModel):
    """Re-enqueue the unlock step after ``/key add`` (SPEC line 111).

    Deliberately carries no key material: the worker reads
    ``state/keys/<EV-id>.yaml``. Success is a manifest status; the key value
    is never echoed back.
    """

    ev_id: str = Field(pattern=EV_ID_PATTERN)


def safe_case_relative_path(path: str) -> str:
    """Validate a path relative to the evidence root (zip-slip guard).

    Rejects absolute paths, drive letters, ``..`` components and NUL bytes.
    Backslashes are kept as found (archive members are recorded verbatim).
    """
    if not path:
        raise ValueError("empty path")
    if "\x00" in path:
        raise ValueError(f"path {path!r} contains NUL")
    if path.startswith("/") or path.startswith("\\"):
        raise ValueError(f"path {path!r} is absolute")
    drive, _, _rest = path.partition(":")
    if _rest and len(drive) == 1 and drive.isalpha():
        raise ValueError(f"path {path!r} contains a drive letter")
    if any(part == ".." for part in path.replace("\\", "/").split("/")):
        raise ValueError(f"path {path!r} escapes the evidence root")
    return path


class ExtractPayload(BaseModel):
    """Targeted extraction request (pack artifact names or explicit paths).

    Paths are relative to the evidence root; anything resolving outside the
    mounted case is refused (T3 contract).
    """

    ev_id: str = Field(pattern=EV_ID_PATTERN)
    artifacts: list[str] = Field(default_factory=list)
    paths: list[str] = Field(default_factory=list)

    @field_validator("paths")
    @classmethod
    def _paths_safe(cls, v: list[str]) -> list[str]:
        return [safe_case_relative_path(p) for p in v]

    @model_validator(mode="after")
    def _something_requested(self) -> ExtractPayload:
        if not self.artifacts and not self.paths:
            raise ValueError("extract payload requires artifacts or paths")
        return self


class AddKeyPayload(BaseModel):
    """``/key add <EV-id> <type> <value|path>`` command-layer payload.

    The command layer persists the material to ``state/keys/<EV-id>.yaml``
    (0600) and enqueues :class:`UnlockPayload`; the value itself never
    reaches Redis or any MCP container.
    """

    ev_id: str = Field(pattern=EV_ID_PATTERN)
    key_type: str

    @field_validator("key_type")
    @classmethod
    def _key_type_closed(cls, v: str) -> str:
        return validate_closed("key_type", v, KEY_TYPE)


class JobEnvelope(BaseModel):
    """Generic RQ envelope; typed payloads validated per ``job_type``."""

    job_type: JobType
    queue: QueueName
    ev_id: str | None = Field(default=None, pattern=EV_ID_PATTERN)
    payload: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _typed_payload(self) -> JobEnvelope:
        if self.job_type == "fetch_symbol":
            FetchSymbolPayload.model_validate(self.payload)
        elif self.job_type == "unlock":
            UnlockPayload.model_validate(self.payload)
        elif self.job_type == "extract":
            ExtractPayload.model_validate(self.payload)
        return self


TYPED_PAYLOADS: dict[str, type[BaseModel]] = {
    "fetch_symbol": FetchSymbolPayload,
    "unlock": UnlockPayload,
    "extract": ExtractPayload,
}


def validate_payload(job_type: str, payload: dict[str, Any]) -> BaseModel | dict[str, Any]:
    """Validate a payload for ``job_type``; typed models for known types.

    Pipeline step payloads (hash, detect, parse, ...) get their schemas with
    their implementing steps (work-order step 2+); they pass through
    unvalidated here.
    """
    model = TYPED_PAYLOADS.get(job_type)
    if model is None:
        return payload
    return model.model_validate(payload)
