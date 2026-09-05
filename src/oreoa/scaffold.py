"""Empty case skeleton generation for /case new.

Derives empty skeletons from the same structures as templates/case/ (worked
example kept untouched). case.yaml is serialized from the Pydantic models
(source of truth); journal.md mirrors the worked template's rules and
sections, emptied. answers.yaml is created for EXERCICE cases only (A2:
score-layer file, never mounted into MCP containers).
"""

from __future__ import annotations

import os
import stat
from pathlib import Path

import yaml

from .case_model import Case, CaseFile, CaseType

JOURNAL_RULES = """<!--
Regles :
- Le bloc "Etat courant" est le SEUL reecrit par l'agent (a la fin de chaque session).
  C'est ce qu'il relit en priorite a /analyse ; il doit tenir en une dizaine de lignes.
- Tout le reste est en ajout seul (append-only), horodate en UTC, par session.
- Une entree = un fait, une piste, une action ou une decision. Jamais de prose libre.
- Une piste ne devient un constat (finding dans case.yaml) que sur validation de l'analyste.
- Chaque affirmation technique pointe vers une preuve : id d'evidence, artefact, record_id ou timestamp.
- Chaque entree porte le role qui l'a ecrite : [ingest] [triage] [analyst] [reviewer] [reporter] [human].
- Les sections "Triage" et "Revue" sont ecrites par leurs roles respectifs, jamais par l'analyst.
-->"""

JOURNAL_TEMPLATE = """# Journal — {case_id}

{rules}

## Etat courant
_Mis a jour : {updated} — initialisation_

- **Ou on en est** : dossier cree, aucune preuve ingeree.
- **Hypotheses ouvertes** : aucune.
- **Collectes manquantes** : a completer apres /ingest.
- **Prochaines etapes** : deposer les preuves dans evidence/, lancer /ingest.
- **Points d'attention** : aucun.
---

## Session S1 — {date} — {analyst}
_Modele : {model} — Dossier : {kind}_

"""


def _dump_case(cf: CaseFile) -> str:
    data = cf.model_dump(mode="json", exclude_none=True)
    return yaml.safe_dump(
        data, sort_keys=False, allow_unicode=True, default_flow_style=False
    )


def build_case_yaml(case_id: str, case_type: CaseType, name: str, analyst: str) -> str:
    cf = CaseFile(
        schema_version=2,
        case=Case(id=case_id, name=name, type=case_type, status="open", analysts=[analyst] if analyst else []),
    )
    header = (
        "# case.yaml - etat declaratif du dossier (schema 2).\n"
        "# Modifie par la plateforme uniquement via la porte de confirmation\n"
        "# (confirmed_by_analyst), editable a la main par l'analyste.\n"
    )
    return header + _dump_case(cf)


def build_journal(case_id: str, case_type: CaseType, analyst: str, model: str) -> str:
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc)
    return JOURNAL_TEMPLATE.format(
        case_id=case_id,
        rules=JOURNAL_RULES,
        updated=now.isoformat(timespec="seconds").replace("+00:00", "Z"),
        date=now.date().isoformat(),
        analyst=analyst or "anonyme",
        model=model or "non configure",
        kind="EXERCICE" if case_type == "exercice" else "INCIDENT",
    )


def scaffold_case(
    cases_root: Path,
    case_id: str,
    case_type: CaseType,
    name: str = "",
    analyst: str = "",
    model: str = "",
) -> Path:
    """Create cases/<id>/ with the empty skeleton. Refuses an existing case."""
    case_dir = cases_root / case_id
    if case_dir.exists():
        raise FileExistsError(f"case already exists: {case_dir}")

    (case_dir / "evidence").mkdir(parents=True)
    (case_dir / "derived").mkdir()
    (case_dir / "reports").mkdir()
    (case_dir / "state" / "keys").mkdir(parents=True)

    (case_dir / "case.yaml").write_text(
        build_case_yaml(case_id, case_type, name, analyst), encoding="utf-8"
    )
    (case_dir / "journal.md").write_text(
        build_journal(case_id, case_type, analyst, model), encoding="utf-8"
    )
    if case_type == "exercice":
        (case_dir / "answers.yaml").write_text(
            "# answers.yaml - verite terrain EXERCICE, lue par /score uniquement (A2).\n",
            encoding="utf-8",
        )

    _set_case_perms(case_dir)
    return case_dir


def _set_case_perms(case_dir: Path) -> None:
    """Shared host/container group model: directories 770, files 660.

    The container user is `10001:<OREOA_HOST_GID>` (compose user field) and
    the analyst owns the files on the host with the same primary group, so
    group rw gives both sides access; others get nothing. state/keys is 750
    with key files 640 (read-only for workers, written by the oreoa CLI only).
    """
    for root, dirs, files in os.walk(case_dir):
        for d in dirs:
            path = Path(root) / d
            path.chmod(stat.S_IRWXU | stat.S_IRWXG)
        for f in files:
            path = Path(root) / f
            path.chmod(stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IWGRP)
    case_dir.chmod(stat.S_IRWXU | stat.S_IRWXG)
    keys = case_dir / "state" / "keys"
    keys.chmod(stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP)
