"""Pydantic models for ``derived/manifest.json`` (SPEC case layout + line 98).

The manifest is the evidence registry: identity, hashes, kind, one status per
pipeline step, plus image-specific state (container format, encryption,
protector, unlock, VSS inventory) and memory-symbol status. Written only by
pipeline workers (amendment A1); read-only for everyone else.

Delta rules for /ingest (SPEC line 100): new -> process; unchanged -> skip or
rerun failed step; hash mismatch -> block + alert; missing -> flag. The
delta logic itself lands with /ingest (work-order step 2); these models are
its contract.
"""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from oreoa.vocab import (
    CONTAINER_FORMAT,
    ENCRYPTION,
    EV_ID_PATTERN,
    CASE_ID_PATTERN,
    EVIDENCE_KIND,
    PROTECTOR_TYPE,
    SHA256_PATTERN,
    STEP_STATUS,
    SYMBOL_STATUS,
    UNLOCK_STATUS,
    validate_closed,
)

ManifestSchemaVersion = Literal[1]


def _closed(name: str, values: tuple[str, ...]):
    def validator(v: str) -> str:
        return validate_closed(name, v, values)

    return validator


class EvidenceFile(BaseModel):
    path: str = Field(min_length=1)
    sha256: str = Field(pattern=SHA256_PATTERN)
    size_bytes: int | None = Field(default=None, ge=0)


class StepResult(BaseModel):
    status: str = "pending"
    error: str = ""
    started_at: datetime | None = None
    finished_at: datetime | None = None
    details: dict[str, Any] = Field(default_factory=dict)

    @field_validator("status")
    @classmethod
    def _status_closed(cls, v: str) -> str:
        return _closed("step_status", STEP_STATUS)(v)

    @model_validator(mode="after")
    def _finished_consistency(self) -> StepResult:
        if self.finished_at is not None and self.started_at is not None:
            if self.finished_at < self.started_at:
                raise ValueError("step finished_at precedes started_at")
        return self


class VssSnapshot(BaseModel):
    index: int = Field(ge=0)
    created_at: datetime | None = None
    size: int | None = Field(default=None, ge=0)


class Evidence(BaseModel):
    ev_id: str = Field(pattern=EV_ID_PATTERN)
    kind: str
    host: str = ""
    files: list[EvidenceFile] = Field(min_length=1)
    collected_at: datetime | None = None
    steps: dict[str, StepResult] = Field(default_factory=dict)
    container_format: str | None = None
    encryption: str = "none"
    protector: str | None = None
    unlock: str = "not_needed"
    vss: list[VssSnapshot] = Field(default_factory=list)
    symbols_status: str = "not_needed"
    symbols_file: str | None = None
    symbols_identifier: str | None = None

    @field_validator("kind")
    @classmethod
    def _kind_closed(cls, v: str) -> str:
        return _closed("evidence_kind", EVIDENCE_KIND)(v)

    @field_validator("container_format")
    @classmethod
    def _container_closed(cls, v: str | None) -> str | None:
        if v is None:
            return v
        return _closed("container_format", CONTAINER_FORMAT)(v)

    @field_validator("encryption")
    @classmethod
    def _encryption_closed(cls, v: str) -> str:
        return _closed("encryption", ENCRYPTION)(v)

    @field_validator("protector")
    @classmethod
    def _protector_closed(cls, v: str | None) -> str | None:
        if v is None:
            return v
        return _closed("protector_type", PROTECTOR_TYPE)(v)

    @field_validator("unlock")
    @classmethod
    def _unlock_closed(cls, v: str) -> str:
        return _closed("unlock_status", UNLOCK_STATUS)(v)

    @field_validator("symbols_status")
    @classmethod
    def _symbols_closed(cls, v: str) -> str:
        return _closed("symbol_status", SYMBOL_STATUS)(v)

    @model_validator(mode="after")
    def _image_state_consistency(self) -> Evidence:
        if self.kind == "disk_image" and self.container_format is None:
            raise ValueError("disk_image evidence requires container_format")
        if self.encryption == "none":
            if self.protector is not None:
                raise ValueError("protector set but encryption is none")
            if self.unlock != "not_needed":
                raise ValueError(f"unlock={self.unlock!r} but encryption is none")
        return self

    @model_validator(mode="after")
    def _symbols_consistency(self) -> Evidence:
        if self.symbols_status == "present" and not self.symbols_file:
            raise ValueError("symbols_status=present requires symbols_file")
        if self.symbols_status == "missing" and not self.symbols_identifier:
            raise ValueError(
                "symbols_status=missing requires symbols_identifier (exact kernel identifier)"
            )
        return self

    @property
    def sha256(self) -> str:
        if len(self.files) != 1:
            raise ValueError(
                f"{self.ev_id}: single-file hash undefined for {len(self.files)} files"
            )
        return self.files[0].sha256


class Manifest(BaseModel):
    schema_version: ManifestSchemaVersion = 1
    case_id: str = Field(pattern=CASE_ID_PATTERN)
    evidence: list[Evidence] = Field(default_factory=list)
    updated_at: datetime | None = None

    def get_evidence(self, ev_id: str) -> Evidence:
        for entry in self.evidence:
            if entry.ev_id == ev_id:
                return entry
        raise KeyError(f"unknown evidence {ev_id!r} in manifest")


def load_manifest(path: Path) -> Manifest:
    return Manifest.model_validate_json(Path(path).read_text(encoding="utf-8"))


def save_manifest(path: Path, manifest: Manifest) -> None:
    """Atomic write (tmp + os.replace): every step rewrites manifest.json."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(manifest.model_dump_json(indent=2), encoding="utf-8")
    os.replace(tmp, path)


def dumps_manifest(manifest: Manifest) -> str:
    return manifest.model_dump_json(indent=2)


def parse_manifest(payload: str | bytes) -> Manifest:
    return Manifest.model_validate_json(payload)
