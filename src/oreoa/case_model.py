"""Pydantic models for case.yaml (schema_version 2) and answers.yaml.

Authority: templates/case/case.yaml (worked example) + SPEC.md case layout.
Written only by mcp-case through the confirmation gate (A1); the analyst may
edit by hand. /case scaffolds derive empty skeletons from these models.
"""

from __future__ import annotations

import pathlib
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

Path = pathlib.Path

SchemaVersion = Literal[2]
CaseType = Literal["incident", "exercice"]
CaseStatus = Literal["open", "closed"]
Criticity = Literal["low", "medium", "high"]
HypothesisStatus = Literal["open", "confirmed", "refuted"]
Confidence = Literal["low", "medium", "high"]
ReviewVerdict = Literal["accept", "challenge", "reject"]
GapStatus = Literal["requested", "received", "dropped"]

ALLOWED_ENUMS = {
    "case.type": CaseType,
    "case.status": CaseStatus,
    "criticity": Criticity,
    "hypotheses.status": HypothesisStatus,
    "confidence": Confidence,
    "review": ReviewVerdict,
    "gaps.status": GapStatus,
}


class Case(BaseModel):
    id: str = Field(pattern=r"^[0-9]{4}-[0-9]{2}-(?:INC|EXE)-[0-9]{3,}$|^[A-Za-z0-9._-]{3,64}$")
    name: str = ""
    type: CaseType = "incident"
    status: CaseStatus = "open"
    created: datetime | None = None
    analysts: list[str] = Field(default_factory=list)
    summary: str = ""


class Window(BaseModel):
    start: datetime | None = None
    end: datetime | None = None


class Context(BaseModel):
    organisation: str = ""
    perimetre: str = ""
    timezone: str = "Europe/Paris"
    window: Window = Field(default_factory=Window)
    trigger: str = ""
    known_indicators: list[str] = Field(default_factory=list)


class Machine(BaseModel):
    hostname: str
    role: str = ""
    os: str = ""
    ips: list[str] = Field(default_factory=list)
    users: list[str] = Field(default_factory=list)
    criticity: Criticity = "medium"
    evidence_ids: list[str] = Field(default_factory=list)
    notes: str = ""


class StopCriteria(BaseModel):
    confirm: str = ""
    refute: str = ""


class Hypothesis(BaseModel):
    id: str = Field(pattern=r"^H[0-9]+$")
    statement: str
    status: HypothesisStatus = "open"
    confidence: Confidence = "low"
    attck: list[str] = Field(default_factory=list)
    dfiq_questions: list[str] = Field(default_factory=list)
    supported_by: list[str] = Field(default_factory=list)
    contradicted_by: list[str] = Field(default_factory=list)
    stop_criteria: StopCriteria = Field(default_factory=StopCriteria)
    next_actions: list[str] = Field(default_factory=list)
    opened: datetime | None = None
    closed: datetime | None = None


class Finding(BaseModel):
    id: str = Field(pattern=r"^F[0-9]+$")
    host: str = ""
    timestamp: datetime | None = None
    description: str
    attck: list[str] = Field(default_factory=list)
    evidence_ref: str = ""
    record_ids: list[str] = Field(default_factory=list)
    from_lead: str = ""
    review: ReviewVerdict = "accept"
    validated_by: str = ""
    validated_on: datetime | None = None


class Gap(BaseModel):
    host: str = ""
    artifact: str
    reason: str = ""
    dfiq_question: str = ""
    status: GapStatus = "requested"
    requested_on: datetime | None = None


class ModelsUsed(BaseModel):
    analyst: str = ""
    triage: str = ""
    reviewer: str = ""


class KnowledgeSnapshot(BaseModel):
    """Versions of the knowledge bases copied from knowledge/snapshot.json."""

    dfiq: str = ""
    forensic_artifacts: str = ""
    sigma: str = ""
    attack: str = ""
    yara: str = ""
    scoring: str = ""


class Session(BaseModel):
    id: str = Field(pattern=r"^S[0-9]+$")
    started: datetime | None = None
    analyst: str = ""
    runtime: str = ""
    llm_endpoint: str = ""
    models: ModelsUsed = Field(default_factory=ModelsUsed)
    knowledge_snapshot: KnowledgeSnapshot = Field(default_factory=KnowledgeSnapshot)
    commands: list[str] = Field(default_factory=list)


class CaseFile(BaseModel):
    """Root of case.yaml."""

    schema_version: SchemaVersion = 2
    case: Case
    context: Context = Field(default_factory=Context)
    machines: list[Machine] = Field(default_factory=list)
    hypotheses: list[Hypothesis] = Field(default_factory=list)
    findings: list[Finding] = Field(default_factory=list)
    gaps: list[Gap] = Field(default_factory=list)
    sessions: list[Session] = Field(default_factory=list)

    @field_validator("case")
    @classmethod
    def _id_matches(cls, v: Case) -> Case:
        if not v.id:
            raise ValueError("case.id is required")
        return v


def load_case(path: Path) -> CaseFile:
    import yaml

    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return CaseFile.model_validate(data)
