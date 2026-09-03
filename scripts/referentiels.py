#!/usr/bin/env python3
"""referentiels.py - upstream referentials tooling (artifacts + DFIQ).

Runs INSIDE the container (via dt): reads /referentiels (baked at build) and
/referentiels-kit (kit-custom, mounted ro when present).

Usage:
  artifacts match <manifest.yaml>     match collections <-> definitions, update manifest
  artifacts expand <ArtifactName>     resolve an artifact -> resolved sources + kit tools
  artifacts index [file|-]            regenerate the generated catalogue section (markers)
  artifacts check                     integrity (MANIFEST.sha256) + parsing + traces
  dfiq arbre [S-id|-]                 tree scenario -> facets -> questions
  dfiq plan <Q-id|F-id|S-id>          answer plan: approaches + ForensicArtifact resolution
  dfiq index [file|-]                 regenerate the generated DFIQ catalogue section
  dfiq check                          integrity + parental consistency of the corpus
"""
import fnmatch
import hashlib
import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("Erreur : module pyyaml requis.")
    sys.exit(1)

try:
    from artifacts import reader as artifacts_reader
except ImportError:
    artifacts_reader = None

ARTIFACTS_DATA = Path("/referentiels/artifacts/data")
ARTIFACTS_MANIFEST = Path("/referentiels/artifacts/MANIFEST.sha256")
DFIQ_DATA = Path("/referentiels/dfiq/data")
DFIQ_MANIFEST = Path("/referentiels/dfiq/MANIFEST.sha256")
TRACES = Path("/referentiels/traces")
KIT_ARTIFACTS = Path("/referentiels-kit/artifacts")
KIT_DFIQ = Path("/referentiels-kit/dfiq")

VARIABLES = {
    "system_root": "C:\\Windows",
    "windows_dir": "C:\\Windows",
    "environ_systemroot": "C:\\Windows",
    "environ_systemdrive": "C:\\",
    "users.homedir": "C:\\Users\\<utilisateur> | /home/<utilisateur>",
    "users.localappdata": "C:\\Users\\<utilisateur>\\AppData\\Local",
    "users.localappdata_low": "C:\\Users\\<utilisateur>\\AppData\\LocalLow",
    "users.appdata": "C:\\Users\\<utilisateur>\\AppData\\Roaming",
    "users.temp": "C:\\Users\\<utilisateur>\\AppData\\Local\\Temp",
    "users.username": "<utilisateur>",
    "users.global_home": "/home",
    "mount_point": "<point_de_montage>",
}

OUTILS_PAR_TYPE = {
    "FILE": "super-timeline log2timeline (dt); extraction fls/icat (dt) on disk image",
    "PATH": "super-timeline log2timeline (dt); enumeration fls (dt) on disk image",
    "REGISTRY_KEY": "regipy parsing (in-image python); hive extracted via fls/icat (dt)",
    "WMI": "out of runtime scope - informational referential (WMI collection in guidance mode)",
}


# ---------------------------------------------------------------- chargement

def charger_artefacts():
    """Upstream + kit-custom definitions -> list of (artifact, origin)."""
    definitions = []
    if artifacts_reader is None:
        print("Error: artifacts library missing from the image.", file=sys.stderr)
        sys.exit(1)
    if ARTIFACTS_DATA.is_dir():
        for artefact in artifacts_reader.YamlArtifactsReader().ReadDirectory(str(ARTIFACTS_DATA)):
            definitions.append((artefact, "upstream"))
    if KIT_ARTIFACTS.is_dir():
        for fichier in sorted(KIT_ARTIFACTS.glob("*.yaml")):
            for artefact in artifacts_reader.YamlArtifactsReader().ReadFile(str(fichier)):
                definitions.append((artefact, "kit"))
    return definitions


def charger_dfiq():
    """Upstream + kit-custom DFIQ corpus -> (scenarios, facets, questions) by id."""
    corpus = {"scenario": {}, "facet": {}, "question": {}, "kit": set()}
    for fichier in sorted(DFIQ_DATA.rglob("*.yaml")):
        try:
            docs = [d for d in yaml.safe_load_all(fichier.read_text()) if d]
        except yaml.YAMLError as exc:
            print(f"Parsing error {fichier}: {exc}", file=sys.stderr)
            sys.exit(1)
        for doc in docs:
            if doc.get("id"):
                corpus[doc.get("type", "question")][doc["id"]] = doc
    if KIT_DFIQ.is_dir():
        for fichier in sorted(KIT_DFIQ.rglob("*.yaml")):
            for doc in yaml.safe_load_all(fichier.read_text()) or []:
                if doc and doc.get("id"):
                    corpus[doc.get("type", "question")][doc["id"]] = doc
                    corpus["kit"].add(doc["id"])
    return corpus


def lire_trace(nom):
    """Reads /referentiels/traces/<nom>.txt -> dict key: value."""
    chemin = TRACES / f"{nom}.txt"
    if not chemin.is_file():
        return None
    info = {}
    for ligne in chemin.read_text().splitlines():
        if ligne.startswith("#") or ":" not in ligne:
            continue
        cle, valeur = ligne.split(":", 1)
        info[cle.strip()] = valeur.strip()
    return info


# ------------------------------------------------------------------- matching

def bases_de_pattern(pattern: str):
    """Dernier composant concret d'un pattern (les wildcards purs de fin sont ignores).

    Ex. '%%system_root%%\\Temp\\*' -> 'Temp' ; '/var/log/auth.log*' -> 'auth.log*'.
    Un pattern integralement wildcard ne matche rien (retour None).
    """
    composants = [c for c in pattern.replace("\\", "/").split("/") if c]
    for composant in reversed(composants):
        if composant not in ("*", "**"):
            return composant
    return None


# Extensions specifiques : un pattern generique (*.evtx, *.pcap...) peut rattacher un
# fichier isole. Les extensions banales (.log, .json, .dat...) sont trop ambigues pour
# un rapprochement sans contexte d'arborescence : les patterns generiques les visant
# sont ignores (ils restent visibles via artefacts expand).
EXTENSIONS_SPECIFIQUES = {".evtx", ".pcap", ".pcapng", ".reg", ".e01", ".aff4"}


def base_matche(nom: str, base: str) -> bool:
    """Precision du rapprochement : base exacte ou prefixee -> match ; base generique
    (prefixe wildcard) -> match uniquement si l'extension est specifique."""
    if not base.startswith("*"):
        return fnmatch.fnmatch(nom, base.casefold())
    suffixe = Path(base).suffix.lower()
    return suffixe in EXTENSIONS_SPECIFIQUES and nom.endswith(suffixe)


def matcher_collection(nom_collection: str, definitions):
    """Match a collection (file/folder name) against FILE/PATH sources."""
    nom = nom_collection.casefold()
    correspondances = []
    for artefact, origine in definitions:
        for source in artefact.sources or []:
            if source.type_indicator not in ("FILE", "PATH"):
                continue
            for pattern in (source.AsDict() or {}).get("paths", []):
                base = bases_de_pattern(pattern)
                if base and base_matche(nom, base.casefold()):
                    correspondances.append((artefact.name, origine))
                    break
    return sorted(dict.fromkeys(correspondances))


def cmd_artifacts_match(chemin_manifest: str):
    manifest = Path(chemin_manifest)
    if not manifest.is_file():
        print(f"Error: manifest not found: {manifest}", file=sys.stderr)
        return 1
    donnees = yaml.safe_load(manifest.read_text())
    definitions = charger_artefacts()
    print(f"[artifacts match] {len(definitions)} definitions loaded "
          f"(upstream + kit), manifest: {manifest.name}")
    for collection in donnees.get("collections", []):
        trouve = matcher_collection(collection.get("name", ""), definitions)
        collection["artifacts"] = [nom for nom, _ in trouve]
        kit = [nom for nom, origine in trouve if origine == "kit"]
        detail = ", ".join(nom + (" [kit]" if origine == "kit" else "")
                           for nom, origine in trouve) or "-"
        print(f"  {collection.get('name','?')} -> {detail}")
        if kit:
            print(f"    (kit definitions used: {', '.join(kit)})")
    info_a, info_d = lire_trace("artifacts"), lire_trace("dfiq")
    donnees["referentials"] = {
        "artifacts": {
            "source": (info_a or {}).get("source", "unknown"),
            "version": (info_a or {}).get("release", "unknown"),
            "built_at": (info_a or {}).get("date_build", "unknown"),
        },
        "dfiq": {
            "source": (info_d or {}).get("source", "unknown"),
            "commit": (info_d or {}).get("commit", "unknown"),
            "built_at": (info_d or {}).get("date_build", "unknown"),
        },
    }
    manifest.write_text(yaml.safe_dump(donnees, sort_keys=False, allow_unicode=True))
    print("[artifacts match] manifest updated (artifacts field per collection + referentials)")
    return 0


# ------------------------------------------------------------------- expand

def resoudre_chemin(pattern: str):
    variables = sorted(set(re.findall(r"%%([^%]+)%%", pattern)))
    resolu = re.sub(r"%%([^%]+)%%",
                    lambda m: VARIABLES.get(m.group(1), f"<{m.group(1)}>"), pattern)
    return resolu, variables


def decrire_artefact(artefact, origine, verbose=True):
    lignes = [f"## {artefact.name} [{'kit' if origine == 'kit' else 'upstream'}]",
              f"OS: {', '.join(artefact.supported_os or ['all'])}"]
    doc = (artefact.description or "").strip().splitlines()
    if doc:
        lignes.append(f"Description: {doc[0]}")
    for source in artefact.sources or []:
        lignes.append(f"- source {source.type_indicator}")
        if source.type_indicator == "ARTIFACT_GROUP":
            for nom in (source.AsDict() or {}).get("names", []):
                lignes.append(f"  - member: {nom}")
            continue
        attributs = source.AsDict() or {}
        for pattern in attributs.get("paths", attributs.get("keys", [])):
            lignes.append(f"  - pattern: {pattern}")
            if verbose:
                resolu, variables = resoudre_chemin(pattern)
                suffixe = f" (variables: {', '.join(variables)})" if variables else ""
                lignes.append(f"    resolved: {resolu}{suffixe}")
        if verbose and OUTILS_PAR_TYPE.get(source.type_indicator):
            lignes.append(f"  kit tools: {OUTILS_PAR_TYPE[source.type_indicator]}")
    return "\n".join(lignes)


def cmd_artifacts_expand(nom: str):
    definitions = charger_artefacts()
    for artefact, origine in definitions:
        if artefact.name == nom:
            print(decrire_artefact(artefact, origine))
            return 0
    insensibles = [a.name for a, _ in definitions if a.name.casefold() == nom.casefold()]
    if insensibles:
        print(f"Artifact '{nom}' not found; exact spelling: {insensibles[0]}")
        return 1
    print(f"Artifact '{nom}' not found in the referential (upstream + kit). "
          "Use: artifacts index")
    return 1


# ------------------------------------------------------------------- index

def ecrire_genere(chemin: Path, marqueur: str, contenu: str, titre_defaut: str):
    """Writes the generated section between markers, preserving the rest of the file."""
    debut = f"<!-- genere:{marqueur}:debut -->"
    fin = f"<!-- genere:{marqueur}:fin -->"
    bloc = f"{debut}\n{contenu}\n{fin}\n"
    if chemin.is_file():
        texte = chemin.read_text()
        if debut in texte and fin in texte:
            avant = texte.split(debut, 1)[0]
            apres = texte.split(fin, 1)[1]
            chemin.write_text(avant + bloc + apres)
            return
    chemin.write_text(f"{titre_defaut}\n\n{bloc}")


def cmd_artifacts_index(sortie: str):
    definitions = charger_artefacts()
    lignes = [
        f"Index generated from the baked referential ({len(definitions)} definitions, "
        "upstream + kit) - do not edit this section.",
        "",
        "| Artifact | OS | Sources | Description |",
        "|----------|----|---------|-------------|",
    ]
    for artefact, origine in sorted(definitions, key=lambda a: a[0].name.casefold()):
        os_txt = ",".join(o.split()[0] for o in (artefact.supported_os or ["all"]))
        types = {}
        for source in artefact.sources or []:
            types[source.type_indicator] = types.get(source.type_indicator, 0) + 1
        src_txt = ", ".join(f"{n} {t}" for t, n in sorted(types.items())) or "-"
        doc = " ".join((artefact.description or "").split())
        doc = doc[:90] + ("..." if len(doc) > 90 else "")
        suffixe = " [kit]" if origine == "kit" else ""
        lignes.append(f"| `{artefact.name}`{suffixe} | {os_txt} | {src_txt} | {doc} |")
    contenu = "\n".join(lignes)
    if sortie == "-":
        print(contenu)
    else:
        ecrire_genere(Path(sortie), "artefacts", contenu,   # marqueur stable (compat fichiers existants)
                      "# ForensicArtifacts artifact referential\n\n"
                      "Kit mapping and usage: sections below and above. The upstream "
                      "referential is baked into the image at each build (versions: "
                      "case manifest, `referentials` field).")
        print(f"Artifacts index written: {sortie}")
    return 0


# ------------------------------------------------------------------- check

def verifier_manifest(manifest: Path, racine: Path):
    """Recomputes SHA256 of every MANIFEST.sha256 line."""
    if not manifest.is_file():
        return False, f"{manifest} absent"
    echecs = []
    for ligne in manifest.read_text().splitlines():
        if not ligne.strip():
            continue
        empreinte, relatif = ligne.split("  ", 1)
        fichier = racine / relatif
        if not fichier.is_file():
            echecs.append(f"manquant : {relatif}")
        elif hashlib.sha256(fichier.read_bytes()).hexdigest() != empreinte:
            echecs.append(f"empreinte : {relatif}")
    return (not echecs), "; ".join(echecs[:5]) or "integre"


def cmd_artifacts_check():
    problems = []
    n_fichiers = len(list(ARTIFACTS_DATA.rglob("*.yaml")))
    ok_manifest, detail = verifier_manifest(ARTIFACTS_MANIFEST, ARTIFACTS_MANIFEST.parent)
    if not ok_manifest:
        problems.append(f"MANIFEST integrity: {detail}")
    if n_fichiers < 10:
        problems.append(f"abnormally small corpus ({n_fichiers} files)")
    n_defs = len(charger_artefacts())
    for trace in ("artifacts", "dfiq"):
        if not (TRACES / f"{trace}.txt").is_file():
            problems.append(f"missing trace: /referentiels/traces/{trace}.txt")
    customs = len(list(KIT_ARTIFACTS.glob("*.yaml"))) if KIT_ARTIFACTS.is_dir() else 0
    for nom, info in ({"artifacts": lire_trace("artifacts"), "dfiq": lire_trace("dfiq")}).items():
        if info:
            version = info.get("release") or str(info.get("commit", ""))[:12]
            print(f"  referential {nom}: {version} (built {info.get('date_build')})")
    print(f"  corpus: {n_fichiers} files, {n_defs} definitions loaded, {customs} kit customs")
    if problems:
        print("[artifacts check] FAILED: " + " ; ".join(problems))
        return 1
    print("[artifacts check] OK")
    return 0


# -------------------------------------------------------------------- DFIQ

def enfants(corpus, type_parent, id_parent):
    return [doc for doc in corpus[{"scenario": "facet", "facet": "question"}[type_parent]].values()
            if id_parent in (doc.get("parent_ids") or [])]


def cmd_dfiq_arbre(id_scenario: str):
    corpus = charger_dfiq()
    cibles = ([corpus["scenario"][id_scenario]] if id_scenario != "-"
              else sorted(corpus["scenario"].values(), key=lambda d: d["id"]))
    if id_scenario != "-" and id_scenario not in corpus["scenario"]:
        print(f"Scenario '{id_scenario}' not found. Scenarios: "
              + ", ".join(sorted(corpus["scenario"])))
        return 1
    for scenario in cibles:
        tags = ", ".join(scenario.get("tags") or []) or "-"
        print(f"## {scenario['id']} - {scenario.get('name')} [{tags}]")
        if scenario.get("description"):
            print("   " + " ".join(scenario["description"].split())[:140])
        for facet in sorted(enfants(corpus, "scenario", scenario["id"]),
                            key=lambda d: d.get("id", "")):
            origine = " [kit]" if facet["id"] in corpus["kit"] else ""
            print(f"  ### {facet['id']}{origine} - {facet.get('name')}")
            for question in sorted(enfants(corpus, "facet", facet["id"]),
                                   key=lambda d: d.get("id", "")):
                origine_q = " [kit]" if question["id"] in corpus["kit"] else ""
                n_app = len(question.get("approaches") or [])
                print(f"    - {question['id']}{origine_q}: {question.get('name')} "
                      f"(approaches: {n_app})")
    return 0


def cmd_dfiq_plan(identifiant: str):
    corpus = charger_dfiq()
    tout = {**corpus["scenario"], **corpus["facet"], **corpus["question"]}
    if identifiant not in tout:
        print(f"Identifier '{identifiant}' not found (upstream + kit S/F/Q).")
        return 1
    doc = tout[identifiant]
    origine = " [kit]" if identifiant in corpus["kit"] else ""
    if doc["type"] == "scenario":
        cmd_dfiq_arbre(identifiant)
        print("\nUse: dfiq plan <Q-id> for the answer plan of a question.")
        return 0
    if doc["type"] == "facet":
        print(f"## {doc['id']}{origine} - {doc.get('name')}")
        for question in sorted(enfants(corpus, "facet", doc["id"]), key=lambda d: d.get("id", "")):
            print(f"  - {question['id']}: {question.get('name')} "
                  f"(approaches: {len(question.get('approaches') or [])})")
        print("\nUse: dfiq plan <Q-id> for the answer plan of a question.")
        return 0
    tags = ", ".join(doc.get("tags") or []) or "-"
    print(f"## {doc['id']}{origine} - {doc.get('name')} [{tags}]")
    if doc.get("description"):
        print("   " + " ".join(doc["description"].split()))
    approches = doc.get("approaches") or []
    if not approches:
        print("\nNo executable approach in the upstream corpus for this question.")
        print("Kit handling: go through the catalogue signals (catalogue/) and the "
              "analysis skills; document the gap; candidate for a kit-custom approach "
              "(referentiels-kit/dfiq/).")
        return 0
    definitions = {a.name: (a, o) for a, o in charger_artefacts()}
    for i, approche in enumerate(approches, 1):
        print(f"\n### Approach {i}: {approche.get('name')}")
        if approche.get("description"):
            print("   " + " ".join(approche["description"].split()))
        notes = approche.get("notes") or {}
        if notes.get("covered"):
            print("   covers: " + " ; ".join(" ".join(str(c).split()) for c in notes["covered"]))
        if notes.get("not_covered"):
            print("   does not cover: "
                  + " ; ".join(" ".join(str(c).split()) for c in notes["not_covered"]))
        for etape in approche.get("steps") or []:
            stage = etape.get("stage", "?")
            print(f"   - [{stage}] {etape.get('name')}")
            if etape.get("type") == "ForensicArtifact" and etape.get("value"):
                cible = definitions.get(etape["value"])
                if cible:
                    print(f"     -> artifact {etape['value']}:")
                    print("     " + decrire_artefact(cible[0], cible[1]).replace("\n", "\n     "))
                else:
                    print(f"     -> artifact {etape['value']} not found in the baked "
                          "referential (upstream versions evolve): look into artifacts index "
                          "or define a kit artifact.")
    return 0


def cmd_dfiq_index(sortie: str):
    corpus = charger_dfiq()
    n_app = sum(len(q.get("approaches") or []) for q in corpus["question"].values())
    lignes = [
        f"Index generated from the baked corpus ({len(corpus['scenario'])} scenarios, "
        f"{len(corpus['facet'])} facets, {len(corpus['question'])} questions, "
        f"{n_app} approaches) - do not edit this section.",
        "",
    ]
    for scenario in sorted(corpus["scenario"].values(), key=lambda d: d.get("id", "")):
        tags = ", ".join(scenario.get("tags") or []) or "-"
        origine = " [kit]" if scenario["id"] in corpus["kit"] else ""
        lignes.append(f"## {scenario['id']}{origine} - {scenario.get('name')} [{tags}]")
        facets = enfants(corpus, "scenario", scenario["id"])
        lignes.append(f"Facets: {len(facets)}; questions: "
                      f"{sum(len(enfants(corpus, 'facet', f['id'])) for f in facets)}")
        for facet in sorted(facets, key=lambda d: d.get("id", "")):
            origine_f = " [kit]" if facet["id"] in corpus["kit"] else ""
            lignes.append(f"### {facet['id']}{origine_f} - {facet.get('name')}")
            for question in sorted(enfants(corpus, "facet", facet["id"]),
                                   key=lambda d: d.get("id", "")):
                origine_q = " [kit]" if question["id"] in corpus["kit"] else ""
                n = len(question.get("approaches") or [])
                lignes.append(f"- {question['id']}{origine_q}: {question.get('name')} "
                              f"(approaches: {n})")
        lignes.append("")
    contenu = "\n".join(lignes)
    if sortie == "-":
        print(contenu)
    else:
        ecrire_genere(Path(sortie), "dfiq", contenu,
                      "# DFIQ referential (Digital Forensics Investigation Questions)\n\n"
                      "Kit mapping and usage: sections above and below. The upstream "
                      "corpus is baked into the image at each build.")
        print(f"DFIQ index written: {sortie}")
    return 0


def cmd_dfiq_check():
    problems = []
    ok_manifest, detail = verifier_manifest(DFIQ_MANIFEST, DFIQ_MANIFEST.parent)
    if not ok_manifest:
        problems.append(f"MANIFEST integrity: {detail}")
    corpus = charger_dfiq()
    if not (corpus["scenario"] and corpus["facet"] and corpus["question"]):
        problems.append("incomplete corpus (S/F/Q)")
    orphelins = [doc["id"] for doc in {**corpus["facet"], **corpus["question"]}.values()
                 for p in (doc.get("parent_ids") or []) if p not in corpus["scenario"]
                 and p not in corpus["facet"] and p not in corpus["question"]]
    if orphelins:
        problems.append(f"missing parents: {', '.join(sorted(set(orphelins))[:5])}")
    info = lire_trace("dfiq")
    if info:
        print(f"  referential dfiq: {str(info.get('commit', ''))[:12]} "
              f"(built {info.get('date_build')})")
    print(f"  corpus: S={len(corpus['scenario'])} F={len(corpus['facet'])} "
          f"Q={len(corpus['question'])}, kit={len(corpus['kit'])}")
    if problems:
        print("[dfiq check] FAILED: " + " ; ".join(problems))
        return 1
    print("[dfiq check] OK")
    return 0


# -------------------------------------------------------------------- main

def main():
    arguments = sys.argv[1:]
    if len(arguments) < 1:
        print(__doc__)
        return 2
    famille, action = arguments[0], arguments[1] if len(arguments) > 1 else ""
    reste = arguments[2:]
    if famille in ("artifacts", "artefacts"):
        if action == "match" and reste:
            return cmd_artifacts_match(reste[0])
        if action == "expand" and reste:
            return cmd_artifacts_expand(reste[0])
        if action == "index":
            return cmd_artifacts_index(reste[0] if reste else "-")
        if action == "check":
            return cmd_artifacts_check()
    if famille == "dfiq":
        if action in ("arbre", "tree"):
            return cmd_dfiq_arbre(reste[0] if reste else "-")
        if action == "plan" and reste:
            return cmd_dfiq_plan(reste[0])
        if action == "index":
            return cmd_dfiq_index(reste[0] if reste else "-")
        if action == "check":
            return cmd_dfiq_check()
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main())
