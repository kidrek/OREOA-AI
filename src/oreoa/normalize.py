"""Deterministic normalization primitives (normalized_data_model.md).

- ``record_id``: sha256 of ``ev_id|artifact|source_ref`` (UTF-8) - re-ingesting
  the same evidence yields the same ids, so ingest is idempotent (principle 2).
- ``path_norm``: forward slashes, lowercase on windows/macos, case preserved
  on linux; the drive letter is kept; no information is normalized away
  (principle 6).
- ``build_summary``: deterministic one-line summary, at most 160 chars
  (cross-cutting rule; the format itself comes from the mapping).
- ``raw_policy_for``: storage-tier rule (SPEC storage tiers) - ``lossless``
  mappings carry ``raw_policy='omitted_lossless'`` with ``raw`` NULL in
  Parquet; lossy mappings keep the original record verbatim
  (``raw_policy='kept'``).

Timestamps are UTC naive (``datetime`` without tzinfo) at microsecond
precision; unknown is NULL, never epoch 0 (principle 3).
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone

from oreoa.vocab import validate_closed

RECORD_ID_SEPARATOR = "|"
SUMMARY_MAX_CHARS = 160
SUMMARY_TRUNCATION_SUFFIX = "..."

RAW_POLICY_KEPT = "kept"
RAW_POLICY_OMITTED_LOSSLESS = "omitted_lossless"


def record_id(ev_id: str, artifact: str, source_ref: str) -> str:
    material = f"{ev_id}{RECORD_ID_SEPARATOR}{artifact}{RECORD_ID_SEPARATOR}{source_ref}"
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def path_norm(path: str, os: str) -> str:
    from oreoa.vocab import OS

    validate_closed("os", os, OS)
    normalized = path.replace("\\", "/")
    if os in ("windows", "macos"):
        normalized = normalized.lower()
    return normalized


def build_summary(tag: str, text: str, detail: str = "") -> str:
    """Deterministic summary line ``[tag] text (detail)`` capped at 160 chars.

    Over-budget algorithm, applied in order:
    1. drop the detail (`` (detail)``) and return if the line fits;
    2. hard-cut ``text`` so ``[tag] <text...>`` fits exactly, the cut marked
       by ``...``.

    Identical inputs always produce identical output.
    """
    line = f"[{tag}] {text}"
    if detail:
        line += f" ({detail})"
    if len(line) <= SUMMARY_MAX_CHARS:
        return line
    without_detail = f"[{tag}] {text}"
    if len(without_detail) <= SUMMARY_MAX_CHARS:
        return without_detail
    fixed_len = len(f"[{tag}] ") + len(SUMMARY_TRUNCATION_SUFFIX)
    budget = SUMMARY_MAX_CHARS - fixed_len
    return f"[{tag}] {text[:budget]}{SUMMARY_TRUNCATION_SUFFIX}"


def raw_policy_for(lossless: bool) -> str:
    """Mapping-level ``lossless`` flag -> row-level ``raw_policy`` value.

    ``lossless: true`` means the source is fully projected into typed columns
    + ``extra``: ``raw`` stays NULL in Parquet and the row is re-derivable
    from ``source_ref + parser_version + mapping_version``. Only mappings with
    a passing round-trip test may be flagged lossless (SPEC storage tiers).
    """
    return RAW_POLICY_OMITTED_LOSSLESS if lossless else RAW_POLICY_KEPT


def utc_now() -> datetime:
    """Naive UTC now (storage convention: TIMESTAMP columns hold UTC)."""
    return datetime.now(timezone.utc).replace(tzinfo=None, microsecond=0)
