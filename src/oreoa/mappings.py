"""Mapping loader - "mappings as data" (normalized_data_model.md principle 8).

``mappings/<tool>/<artifact>.yaml`` declares how a parser output maps onto
the normalized families: source-field -> target-column paths, transforms,
summary template, ``lossless`` flag and optional per-row projections (a log
row is projected into semantic families with ``derived_from`` linking back -
cross-cutting rule of the data model). Adding a source = adding a YAML, not
code.

Field specification (per target column):

- ``path``: dotted source path with numeric indexes (``EventData.Image``,
  ``Times[-1]``); missing resolves to ``default`` then NULL.
- ``type``: ``str|int|float|bool|timestamp|list`` (timestamps are ISO-8601,
  Z or offset, normalized to naive UTC - data-model principle 3).
- ``const``: fixed value (mutually exclusive with ``path``).
- ``transform``: ``basename|path_norm|user_name|service_key|tail_after_backslash``
  (``path_norm`` needs the row ``os``, applied by the parser).

Validation is strict (dfiq_loader precedent): a mapping that targets an
unknown family/column or uses an unknown transform raises at load time -
never a silent skip.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from oreoa.normalize import path_norm

MAPPING_VERSION = 1
TRANSFORMS: tuple[str, ...] = ("basename", "path_norm", "user_name", "service_key", "tail_after_backslash")
FIELD_TYPES: tuple[str, ...] = ("str", "int", "float", "bool", "timestamp", "list", "json")


class SafeDict(dict):
    def __missing__(self, key: str) -> str:
        return ""


def mappings_root() -> Path:
    """Mapping directory: OREOA_MAPPINGS_DIR, else /oreoa/mappings (image),
    else ./mappings (repo checkout)."""
    override = os.environ.get("OREOA_MAPPINGS_DIR", "")
    if override:
        path = Path(override).resolve()
        if not path.is_dir():
            raise FileNotFoundError(f"OREOA_MAPPINGS_DIR {override!r} is not a directory")
        return path
    image_dir = Path("/oreoa/mappings")
    if image_dir.is_dir():
        return image_dir
    repo_dir = Path.cwd() / "mappings"
    if repo_dir.is_dir():
        return repo_dir
    raise FileNotFoundError(
        "mappings directory not found (set OREOA_MAPPINGS_DIR, or run from the repo root)"
    )


def _resolve_path(source: dict[str, Any], path: str) -> Any:
    current: Any = source
    for segment in path.split("."):
        if current is None:
            return None
        name, _, index = segment.partition("[")
        if not isinstance(current, dict) or name not in current:
            return None
        current = current[name]
        while index:
            close = index.index("]")
            raw = index[:close]
            index = index[close + 1 :].lstrip("[")
            if not isinstance(current, list):
                return None
            if raw == "-1" or raw == "":
                if not current:
                    return None
                current = current[-1]
            else:
                position = int(raw)
                if abs(position) >= len(current):
                    return None
                current = current[position]
    return current


def _to_timestamp(value: Any) -> datetime | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc).replace(tzinfo=None, microsecond=0)
    text = str(value).strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None:
        raise ValueError(f"timestamp without timezone: {value!r}")
    return parsed.astimezone(timezone.utc).replace(tzinfo=None, microsecond=0)


def _cast(value: Any, field_type: str) -> Any:
    if value is None or value == "":
        return None
    if field_type == "str":
        return str(value)
    if field_type == "int":
        return int(value)
    if field_type == "float":
        return float(value)
    if field_type == "bool":
        if isinstance(value, bool):
            return value
        return str(value).lower() in ("1", "true", "yes")
    if field_type == "timestamp":
        return _to_timestamp(value)
    if field_type == "list":
        if isinstance(value, list):
            return [str(item) for item in value]
        return [str(value)]
    if field_type == "json":
        if isinstance(value, (dict, list)):
            return json.dumps(value, sort_keys=True, ensure_ascii=False)
        return str(value)
    raise ValueError(f"unknown field type {field_type!r}")


class FieldSpec:
    __slots__ = ("target", "path", "field_type", "const", "default", "transform")

    def __init__(self, target: str, spec: dict[str, Any]) -> None:
        if not isinstance(spec, dict):
            raise ValueError(f"field {target!r}: spec must be a mapping")
        self.target = target
        self.path = spec.get("path", "")
        self.const = spec.get("const")
        self.default = spec.get("default")
        self.transform = spec.get("transform", "")
        self.field_type = spec.get("type", "str")
        if self.transform and self.transform not in TRANSFORMS:
            raise ValueError(f"field {target!r}: unknown transform {self.transform!r}")
        if self.field_type not in FIELD_TYPES:
            raise ValueError(f"field {target!r}: unknown type {self.field_type!r}")
        if not self.path and self.const is None:
            raise ValueError(f"field {target!r}: needs 'path' or 'const'")
        if self.path and self.const is not None:
            raise ValueError(f"field {target!r}: 'path' and 'const' are mutually exclusive")

    def resolve(self, source: dict[str, Any], row_os: str) -> Any:
        value = self.const if self.const is not None else _resolve_path(source, self.path)
        if value is None:
            value = self.default
        value = _cast(value, self.field_type)
        if value is None or not self.transform:
            return value
        if self.transform == "basename":
            return str(value).replace("/", "\\").rsplit("\\", 1)[-1]
        if self.transform == "path_norm":
            return path_norm(str(value), row_os)
        if self.transform == "user_name":
            return str(value).rsplit("\\", 1)[-1]
        if self.transform == "service_key":
            return "HKLM\\SYSTEM\\CurrentControlSet\\Services\\" + str(value)
        if self.transform == "tail_after_backslash":
            return str(value).replace("/", "\\").rsplit("\\", 1)[-1]
        raise ValueError(f"unhandled transform {self.transform!r}")


class Projection:
    __slots__ = ("when", "family", "fields", "consts", "summary_tag", "summary_template")

    def __init__(self, payload: dict[str, Any], index: int) -> None:
        from oreoa.vocab import FAMILIES

        self.when: dict[str, Any] = payload.get("when") or {}
        if not self.when:
            raise ValueError(f"projection #{index}: 'when' is required")
        self.family = payload.get("family", "")
        if self.family not in FAMILIES:
            raise ValueError(f"projection #{index}: unknown family {self.family!r}")
        self.fields = [
            FieldSpec(target, spec) for target, spec in (payload.get("fields") or {}).items()
        ]
        if not self.fields:
            raise ValueError(f"projection #{index}: no fields")
        self.consts: dict[str, Any] = payload.get("consts") or {}
        self.summary_tag = payload.get("summary_tag", self.family)
        self.summary_template = payload.get("summary_template", "")

    def matches(self, source: dict[str, Any]) -> bool:
        for path, expected in self.when.items():
            actual = _resolve_path(source, path)
            if str(actual) != str(expected):
                return False
        return True


class Mapping:
    """One ``mappings/<tool>/<artifact>.yaml`` file."""

    __slots__ = (
        "path", "source_tool", "artifact", "forensic_artifact", "family",
        "lossless", "summary_tag", "summary_template", "fields", "consts",
        "projections", "version",
    )

    def __init__(self, payload: dict[str, Any], path: Path) -> None:
        from oreoa.db import CORE_COLUMNS, FAMILY_COLUMNS
        from oreoa.vocab import FAMILIES

        if not isinstance(payload, dict):
            raise ValueError(f"{path}: mapping must be a YAML mapping")
        self.path = path
        self.version = int(payload.get("version", 1))
        if self.version != 1:
            raise ValueError(f"{path}: unsupported mapping version {self.version}")
        self.source_tool = payload.get("source_tool", "")
        self.artifact = payload.get("artifact", "")
        self.forensic_artifact = payload.get("forensic_artifact", self.artifact)
        self.family = payload.get("family", "")
        if self.family not in FAMILIES:
            raise ValueError(f"{path}: unknown family {self.family!r}")
        self.lossless = bool(payload.get("lossless", False))
        self.summary_tag = payload.get("summary_tag", self.family)
        self.summary_template = payload.get("summary_template", "")

        known = {name for name, _ in CORE_COLUMNS} | {name for name, _ in FAMILY_COLUMNS[self.family]}
        self.fields: list[FieldSpec] = []
        for target, spec in (payload.get("fields") or {}).items():
            if target not in known:
                raise ValueError(f"{path}: field {target!r} is not a column of {self.family!r}")
            self.fields.append(FieldSpec(target, spec))
        self.consts: dict[str, Any] = payload.get("consts") or {}
        for const in self.consts:
            if const not in known:
                raise ValueError(f"{path}: const {const!r} is not a column of {self.family!r}")
        self.projections = [
            Projection(item, index)
            for index, item in enumerate(payload.get("projections") or [])
        ]
        if not self.fields and not self.consts:
            raise ValueError(f"{path}: no fields")

    @property
    def referenced_paths(self) -> set[str]:
        """Top-level source keys referenced by fields/projections/when."""
        keys: set[str] = set()
        for spec in self.fields:
            if spec.path:
                keys.add(spec.path.split(".")[0].split("[")[0])
        for projection in self.projections:
            for spec in projection.fields:
                if spec.path:
                    keys.add(spec.path.split(".")[0].split("[")[0])
            for path in projection.when:
                keys.add(path.split(".")[0].split("[")[0])
        return keys

    def build_row(self, source: dict[str, Any], row_os: str) -> dict[str, Any]:
        row: dict[str, Any] = {}
        for spec in self.fields:
            row[spec.target] = spec.resolve(source, row_os)
        for target, value in self.consts.items():
            row[target] = value
        return row

    def render_summary(self, row: dict[str, Any]) -> str:
        from oreoa.normalize import build_summary

        if not self.summary_template:
            return ""
        text = self.summary_template.format_map(SafeDict(row))
        return build_summary(self.summary_tag, text)


def load_mapping(path: Path) -> Mapping:
    payload = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    return Mapping(payload, Path(path))


def load_mappings(root: Path | None = None) -> dict[str, Mapping]:
    """Load every mapping of ``mappings/<tool>/<artifact>.yaml`` - keyed by
    artifact id (the parser lookup key). Unknown tool directories are
    ignored only if empty; a malformed file is a hard error."""
    root = Path(root) if root is not None else mappings_root()
    mappings: dict[str, Mapping] = {}
    for tool_dir in sorted(root.iterdir()):
        if not tool_dir.is_dir():
            continue
        for file in sorted(tool_dir.glob("*.yaml")):
            mapping = load_mapping(file)
            if mapping.artifact in mappings:
                raise ValueError(f"duplicate mapping artifact {mapping.artifact!r} ({file})")
            mappings[mapping.artifact] = mapping
    return mappings


def utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None, microsecond=0)
