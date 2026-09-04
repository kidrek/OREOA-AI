"""Generate the internal DFIQ objects (knowledge/custom/dfiq/, Q0xxx range).

Content authority: ``dfiq_mapping.md`` (structure) + ``hunts_catalog_seed.yaml``
(hunt titles/descriptions). Every emitted field is derived by the rules below -
no content is invented ad hoc (SPEC amendment A6, AGENTS.md session contract):

- **Questions** (Q0001..Q0047): one per internal DFIQ id referenced by the
  mapping table. ``display_name`` = title of the primary hunt (first mapping
  row referencing the question, table order). ``description`` = primary hunt
  id + its seed description. ``parent_ids`` = internal facets (F0xxx) of the
  answering hunts' mapping rows; when a question has no internal facet in any
  of its rows, the official facets of those rows are used (all of them -
  DFIQ allows multiple parents). ``tags`` = ["oreoa-internal", "<area>"].
- **Facets** (F0001..F0006): internal facets referenced by the mapping table.
  ``display_name`` comes from the FACET_NAMES table below (ATT&CK-aligned,
  derived from the covered hunts' titles); ``description`` lists the covered
  hunt areas. ``parent_ids`` = [S0001].
- **Scenario** (S0001): display_name is authoritative from SPEC A6 ("Host
  Compromise Assessment"); description restates its scope.
- **Approaches**: NOT emitted at work-order step 1.5 (A6: full set with
  mcp-knowledge at step 3); the directory ships empty. Question -> hunt
  navigation stays derivable from the seed (hunts carry ``dfiq:`` lists).

Rerunning is idempotent (stable output). The generated files are committed
and updated by PR only; regeneration requires seed/mapping changes.

Usage: python3 scripts/gen_internal_dfiq.py [--check]
  --check  verify the tree is up to date (no writes), exit 1 on drift.
"""

from __future__ import annotations

import argparse
import re
import sys
import uuid as uuid_module
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
SEED_PATH = ROOT / "hunts_catalog_seed.yaml"
MAPPING_PATH = ROOT / "dfiq_mapping.md"
OUT_DIR = ROOT / "knowledge" / "custom" / "dfiq"

# Format v1.1.0 (google/dfiq data at DFIQ_COMMIT): name + uuid + explicit
# internal flag; dfiq_version 1.1.0 like the official data at the pin.
DFIQ_VERSION = "1.1.0"
DFIQ_UUID_NAMESPACE = uuid_module.UUID("f167d3a5-8f0e-5f4a-9b3c-6c2d1e0a9d77")
SCENARIO_ID = "S0001"
SCENARIO_NAME = "Host Compromise Assessment"
SCENARIO_DESCRIPTION = (
    "Internal OREOA-AI scenario: groups the internal questions of the hunt "
    "catalogue (Q0xxx) under six internal facets. Structure is authoritative "
    "from dfiq_mapping.md; question wording derives from the answering hunts."
)

# Internal facet display names - derived from the hunt titles they cover
# (F0001 initial-access hunts, F0002 execution hunts, F0003 privilege and
# account hunts, F0004 credential dumping / credential store hunts, F0005
# discovery hunts, F0006 command-and-control hunts). Data, not prose.
FACET_NAMES = {
    "F0001": "Initial Access",
    "F0002": "Execution",
    "F0003": "Privilege and Accounts",
    "F0004": "Credential Access",
    "F0005": "Discovery",
    "F0006": "Command and Control",
}

INTERNAL_FACET_IDS = frozenset(FACET_NAMES)

ROW_RE = re.compile(r"^\|\s*(H-[A-Z][A-Z0-9]-\d{3})\s*\|\s*([^|]*)\|\s*([^|]*)\|")


def parse_mapping() -> list[dict]:
    """Mapping table rows: [{hunt, questions, facets}], table order."""
    rows = []
    for line in MAPPING_PATH.read_text(encoding="utf-8").splitlines():
        match = ROW_RE.match(line)
        if not match:
            continue
        hunt, dfiq_cell, facet_cell = match.groups()
        def _ids(cell: str) -> list[str]:
            return [
                token.strip()
                for token in cell.split(",")
                if token.strip() not in ("", "-", "—")
            ]

        questions = _ids(dfiq_cell)
        facets = _ids(facet_cell)
        rows.append({"hunt": hunt, "questions": questions, "facets": facets})
    if not rows:
        raise SystemExit("error: no mapping rows parsed from dfiq_mapping.md")
    return rows


def check_against_seed(rows: list[dict], seed_hunts: dict[str, dict]) -> None:
    """The seed dfiq lists and the mapping table must agree exactly."""
    for row in rows:
        hunt = seed_hunts.get(row["hunt"])
        if hunt is None:
            raise SystemExit(f"error: {row['hunt']} in mapping but not in seed")
        if sorted(hunt.get("dfiq") or []) != sorted(row["questions"]):
            raise SystemExit(
                f"error: {row['hunt']} dfiq mismatch: seed "
                f"{sorted(hunt.get('dfiq') or [])} vs mapping {sorted(row['questions'])}"
            )
    seeded = {h for h, meta in seed_hunts.items() if meta.get("dfiq")}
    mapped = {row["hunt"] for row in rows}
    if seeded - mapped:
        raise SystemExit(f"error: hunts with dfiq missing from mapping: {sorted(seeded - mapped)}")


def question_parents(rows: list[dict]) -> dict[str, list[str]]:
    """Rule A: internal facets of the answering rows, else the official ones."""
    q_rows: dict[str, list[dict]] = {}
    for row in rows:
        for question in row["questions"]:
            if question.startswith("Q0"):
                q_rows.setdefault(question, []).append(row)
    parents: dict[str, list[str]] = {}
    for question, hit_rows in q_rows.items():
        internal = sorted({f for r in hit_rows for f in r["facets"] if f in INTERNAL_FACET_IDS})
        official = sorted({f for r in hit_rows for f in r["facets"] if f not in INTERNAL_FACET_IDS})
        parents[question] = internal or official
        if not parents[question]:
            raise SystemExit(f"error: no facet candidates for {question}")
    return parents


def question_hunts(rows: list[dict]) -> dict[str, list[str]]:
    """Answering hunts per internal question, in mapping-table order."""
    hunts: dict[str, list[str]] = {}
    for row in rows:
        for question in row["questions"]:
            if question.startswith("Q0"):
                hunts.setdefault(question, []).append(row["hunt"])
    return hunts


def area_of(hunt_id: str) -> str:
    return hunt_id.split("-")[1]


def yaml_header(kind: str, derived_from: str) -> str:
    return (
        f"# Internal DFIQ {kind} - generated by scripts/gen_internal_dfiq.py,\n"
        f"# derived from {derived_from}. Do not edit by hand: update the seed\n"
        f"# or the mapping, then regenerate (PR only, SPEC amendment A6).\n"
    )


def stable_uuid(component_id: str) -> str:
    """Deterministic uuid (uuid5 over the id) - reproducible, no randomness."""
    return str(uuid_module.uuid5(DFIQ_UUID_NAMESPACE, component_id))


def emit_component(kind: str, component_id: str, name: str, description: str,
                   parent_ids: list[str], tags: list[str], derived_from: str) -> str:
    body: dict = {
        "name": name,
        "type": kind,
        "description": description,
        "uuid": stable_uuid(component_id),
        "id": component_id,
        "dfiq_version": DFIQ_VERSION,
        "internal": True,
    }
    if tags:
        body["tags"] = tags
    if kind != "scenario":
        body["parent_ids"] = parent_ids
    return yaml_header(kind, derived_from) + "---\n" + yaml.safe_dump(
        body, sort_keys=False, allow_unicode=True, width=100
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="verify, do not write")
    args = parser.parse_args()

    seed = yaml.safe_load(SEED_PATH.read_text(encoding="utf-8"))
    seed_hunts = {h["id"]: h for h in seed["hunts"]}
    rows = parse_mapping()
    check_against_seed(rows, seed_hunts)

    parents = question_parents(rows)
    hunts_by_q = question_hunts(rows)

    files: dict[str, str] = {}

    # Scenario
    files[f"scenarios/{SCENARIO_ID}.yaml"] = emit_component(
        "scenario", SCENARIO_ID, SCENARIO_NAME, SCENARIO_DESCRIPTION, [], ["oreoa-internal"],
        "SPEC.md amendment A6 + dfiq_mapping.md",
    )

    # Facets: questions grouped by their internal parents
    facet_questions: dict[str, list[str]] = {}
    for qid, q_parents in parents.items():
        for facet in q_parents:
            if facet in INTERNAL_FACET_IDS:
                facet_questions.setdefault(facet, []).append(qid)
    for facet_id in sorted(facet_questions):
        qids = sorted(facet_questions[facet_id])
        areas = sorted({area_of(h) for q in qids for h in hunts_by_q[q]})
        files[f"facets/{facet_id}.yaml"] = emit_component(
            "facet",
            facet_id,
            FACET_NAMES[facet_id],
            (
                f"Internal facet grouping the OREOA-AI questions for "
                f"hunt areas {', '.join(areas)} ({len(qids)} internal questions)."
            ),
            [SCENARIO_ID],
            ["oreoa-internal"],
            f"dfiq_mapping.md + hunts_catalog_seed.yaml ({len(qids)} questions)",
        )

    # Questions
    for qid in sorted(parents):
        hid = hunts_by_q[qid][0]
        hunt = seed_hunts[hid]
        description = hunt.get("description") or hunt["title"]
        tags = ["oreoa-internal", f"area:{area_of(hid)}"]
        files[f"questions/{qid}.yaml"] = emit_component(
            "question",
            qid,
            hunt["title"],
            f"Internal question derived from hunt {hid}: {description}",
            parents[qid],
            tags,
            f"hunt {hid}",
        )

    if args.check:
        drift = []
        for rel, content in sorted(files.items()):
            path = OUT_DIR / rel
            if not path.is_file() or path.read_text(encoding="utf-8") != content:
                drift.append(rel)
        present = sorted(str(p.relative_to(OUT_DIR)) for p in OUT_DIR.rglob("*.yaml"))
        for rel in present:
            if rel not in files:
                drift.append(rel + " (unexpected)")
        if drift:
            print("drift detected:", *drift, sep="\n  ", file=sys.stderr)
            return 1
        print(f"knowledge/custom/dfiq/ up to date ({len(files)} objects)")
        return 0

    (OUT_DIR / "scenarios").mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "facets").mkdir(exist_ok=True)
    (OUT_DIR / "questions").mkdir(exist_ok=True)
    (OUT_DIR / "approaches").mkdir(exist_ok=True)
    keep = OUT_DIR / "approaches" / ".gitkeep"
    if not keep.exists():
        keep.touch()
    for rel, content in sorted(files.items()):
        (OUT_DIR / rel).write_text(content, encoding="utf-8")

    readme = OUT_DIR / "README.md"
    readme.write_text(
        "# Internal DFIQ objects (Q0xxx range)\n\n"
        "Generated by `scripts/gen_internal_dfiq.py` - do not edit by hand.\n"
        f"Content: scenario `{SCENARIO_ID}` ({SCENARIO_NAME}), "
        f"{len(facet_questions)} internal facets "
        f"({', '.join(sorted(facet_questions))}), {len(parents)} internal questions "
        "(Q0001..Q%04d), approaches directory empty at work-order step 1.5\n"
        "(A6: full set with mcp-knowledge at step 3; question-to-hunt navigation\n"
        "stays derivable from the seed `dfiq:` lists).\n\n"
        "Format v1.1.0 (google/dfiq data at DFIQ_COMMIT): name + uuid + explicit\n"
        "internal flag; uuid = uuid5(DFIQ_UUID_NAMESPACE, id), deterministic.\n\n"
        "Derivation rules (journalized 2026-09-04): name = primary hunt title;\n"
        "parent_ids = internal facets of the answering rows, else the official\n"
        "facets of those rows; facet names are ATT&CK-aligned, derived from the\n"
        "covered hunts' titles (FACET_NAMES in the generator).\n" % len(parents),
        encoding="utf-8",
    )
    print(f"generated {len(files)} objects under knowledge/custom/dfiq/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
