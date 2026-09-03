#!/usr/bin/env python3
"""referentiels.py - exploitation des referentiels amont embarques (artefacts + DFIQ).

Execute DANS le conteneur (via dt) : lit /referentiels (bake a la build) et
/referentiels-kit (custom kit, monte en ro si present).

Usage :
  artefacts match <manifest.yaml>     rapprochement collections <-> definitions, maj manifest
  artefacts expand <NomArtefact>      resolution d'un artefact -> sources resolues + outils kit
  artefacts index [fichier|-]         regenere la section generee du catalogue (marqueurs)
  artefacts check                     integrite (MANIFEST.sha256) + parsage + traces
  dfiq arbre [S-id|-]                 arbre scenario -> facets -> questions
  dfiq plan <Q-id|F-id|S-id>          plan de reponse : approches + resolution ForensicArtifact
  dfiq index [fichier|-]              regenere la section generee du catalogue DFIQ
  dfiq check                          integrite + coherence parentale du corpus
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
    from artifacts import reader as artefacts_reader
except ImportError:
    artefacts_reader = None

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
    "FILE": "super-timeline log2timeline (dt) ; extraction fls/icat (dt) sur image disque",
    "PATH": "super-timeline log2timeline (dt) ; enumeration fls (dt) sur image disque",
    "REGISTRY_KEY": "parsing regipy (python in-image) ; ruche extraite via fls/icat (dt)",
    "WMI": "hors perimetre runtime - referentiel informatif (collecte WMI en mode guidance)",
}


# ---------------------------------------------------------------- chargement

def charger_artefacts():
    """Definitions amont + customs kit -> liste (artefact, origine)."""
    definitions = []
    if artefacts_reader is None:
        print("Erreur : bibliotheque artifacts absente de l'image.", file=sys.stderr)
        sys.exit(1)
    if ARTIFACTS_DATA.is_dir():
        for artefact in artefacts_reader.YamlArtifactsReader().ReadDirectory(str(ARTIFACTS_DATA)):
            definitions.append((artefact, "amont"))
    if KIT_ARTIFACTS.is_dir():
        for fichier in sorted(KIT_ARTIFACTS.glob("*.yaml")):
            for artefact in artefacts_reader.YamlArtifactsReader().ReadFile(str(fichier)):
                definitions.append((artefact, "kit"))
    return definitions


def charger_dfiq():
    """Corpus DFIQ amont + customs kit -> (scenarios, facets, questions) par id."""
    corpus = {"scenario": {}, "facet": {}, "question": {}, "kit": set()}
    for fichier in sorted(DFIQ_DATA.rglob("*.yaml")):
        try:
            docs = [d for d in yaml.safe_load_all(fichier.read_text()) if d]
        except yaml.YAMLError as exc:
            print(f"Erreur parsage {fichier} : {exc}", file=sys.stderr)
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
    """Lit /referentiels/traces/<nom>.txt -> dict cle: valeur."""
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
    """Rapproche une collection (nom de fichier/dossier) des sources FILE/PATH."""
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


def cmd_artefacts_match(chemin_manifest: str):
    manifest = Path(chemin_manifest)
    if not manifest.is_file():
        print(f"Erreur : manifest introuvable : {manifest}", file=sys.stderr)
        return 1
    donnees = yaml.safe_load(manifest.read_text())
    definitions = charger_artefacts()
    print(f"[artefacts match] {len(definitions)} definitions chargees "
          f"(amont + kit), manifest : {manifest.name}")
    for collection in donnees.get("collections", []):
        trouve = matcher_collection(collection.get("nom", ""), definitions)
        collection["artefacts"] = [nom for nom, _ in trouve]
        kit = [nom for nom, origine in trouve if origine == "kit"]
        detail = ", ".join(nom + (" [kit]" if origine == "kit" else "")
                           for nom, origine in trouve) or "-"
        print(f"  {collection.get('nom','?')} -> {detail}")
        if kit:
            print(f"    (definitions kit utilisees : {', '.join(kit)})")
    info_a, info_d = lire_trace("artifacts"), lire_trace("dfiq")
    donnees["referentiels"] = {
        "artefacts": {
            "source": (info_a or {}).get("source", "inconnue"),
            "version": (info_a or {}).get("release", "inconnue"),
            "date_build": (info_a or {}).get("date_build", "inconnue"),
        },
        "dfiq": {
            "source": (info_d or {}).get("source", "inconnue"),
            "commit": (info_d or {}).get("commit", "inconnu"),
            "date_build": (info_d or {}).get("date_build", "inconnue"),
        },
    }
    manifest.write_text(yaml.safe_dump(donnees, sort_keys=False, allow_unicode=True))
    print("[artefacts match] manifest mis a jour (champ artefacts par collection + referentiels)")
    return 0


# ------------------------------------------------------------------- expand

def resoudre_chemin(pattern: str):
    variables = sorted(set(re.findall(r"%%([^%]+)%%", pattern)))
    resolu = re.sub(r"%%([^%]+)%%",
                    lambda m: VARIABLES.get(m.group(1), f"<{m.group(1)}>"), pattern)
    return resolu, variables


def decrire_artefact(artefact, origine, verbose=True):
    lignes = [f"## {artefact.name} [{'kit' if origine == 'kit' else 'amont'}]",
              f"OS : {', '.join(artefact.supported_os or ['tous'])}"]
    doc = (artefact.description or "").strip().splitlines()
    if doc:
        lignes.append(f"Description : {doc[0]}")
    for source in artefact.sources or []:
        lignes.append(f"- source {source.type_indicator}")
        if source.type_indicator == "ARTIFACT_GROUP":
            for nom in (source.AsDict() or {}).get("names", []):
                lignes.append(f"  - membre : {nom}")
            continue
        attributs = source.AsDict() or {}
        for pattern in attributs.get("paths", attributs.get("keys", [])):
            lignes.append(f"  - pattern : {pattern}")
            if verbose:
                resolu, variables = resoudre_chemin(pattern)
                suffixe = f" (variables : {', '.join(variables)})" if variables else ""
                lignes.append(f"    resolu : {resolu}{suffixe}")
        if verbose and OUTILS_PAR_TYPE.get(source.type_indicator):
            lignes.append(f"  outils kit : {OUTILS_PAR_TYPE[source.type_indicator]}")
    return "\n".join(lignes)


def cmd_artefacts_expand(nom: str):
    definitions = charger_artefacts()
    for artefact, origine in definitions:
        if artefact.name == nom:
            print(decrire_artefact(artefact, origine))
            return 0
    insensibles = [a.name for a, _ in definitions if a.name.casefold() == nom.casefold()]
    if insensibles:
        print(f"Artefact '{nom}' introuvable ; orthographe exacte : {insensibles[0]}")
        return 1
    print(f"Artefact '{nom}' introuvable dans le referentiel (amont + kit). "
          "Utiliser : artefacts index")
    return 1


# ------------------------------------------------------------------- index

def ecrire_genere(chemin: Path, marqueur: str, contenu: str, titre_defaut: str):
    """Ecrit la section generee entre marqueurs, en preservant le reste du fichier."""
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


def cmd_artefacts_index(sortie: str):
    definitions = charger_artefacts()
    lignes = [
        f"Index genere depuis le referentiel bake ({len(definitions)} definitions, "
        "amont + kit) - ne pas editer cette section.",
        "",
        "| Artefact | OS | Sources | Description |",
        "|----------|----|---------|-------------|",
    ]
    for artefact, origine in sorted(definitions, key=lambda a: a[0].name.casefold()):
        os_txt = ",".join(o.split()[0] for o in (artefact.supported_os or ["tous"]))
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
        ecrire_genere(Path(sortie), "artefacts", contenu,
                      "# Referentiel d'artefacts ForensicArtifacts\n\n"
                      "Mapping kit et usage : sections ci-dessous et ci-dessus. "
                      "Le referentiel amont est bake dans l'image a chaque build "
                      "(versions : manifest de l'affaire, champ `referentiels`).")
        print(f"Index artefacts ecrit : {sortie}")
    return 0


# ------------------------------------------------------------------- check

def verifier_manifest(manifest: Path, racine: Path):
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


def cmd_artefacts_check():
    problems = []
    n_fichiers = len(list(ARTIFACTS_DATA.rglob("*.yaml")))
    ok_manifest, detail = verifier_manifest(ARTIFACTS_MANIFEST, ARTIFACTS_MANIFEST.parent)
    if not ok_manifest:
        problems.append(f"integrite MANIFEST : {detail}")
    if n_fichiers < 10:
        problems.append(f"corpus anormalement petit ({n_fichiers} fichiers)")
    n_defs = len(charger_artefacts())
    for trace in ("artifacts", "dfiq"):
        if not (TRACES / f"{trace}.txt").is_file():
            problems.append(f"trace absente : /referentiels/traces/{trace}.txt")
    customs = len(list(KIT_ARTIFACTS.glob("*.yaml"))) if KIT_ARTIFACTS.is_dir() else 0
    for nom, info in ({"artifacts": lire_trace("artifacts"), "dfiq": lire_trace("dfiq")}).items():
        if info:
            version = info.get("release") or str(info.get("commit", ""))[:12]
            print(f"  referentiel {nom} : {version} (build {info.get('date_build')})")
    print(f"  corpus : {n_fichiers} fichiers, {n_defs} definitions chargees, {customs} customs kit")
    if problems:
        print("[artefacts check] ECHEC : " + " ; ".join(problems))
        return 1
    print("[artefacts check] OK")
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
        print(f"Scenario '{id_scenario}' introuvable. Scenarios : "
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
                print(f"    - {question['id']}{origine_q} : {question.get('name')} "
                      f"(approches : {n_app})")
    return 0


def cmd_dfiq_plan(identifiant: str):
    corpus = charger_dfiq()
    tout = {**corpus["scenario"], **corpus["facet"], **corpus["question"]}
    if identifiant not in tout:
        print(f"Identifiant '{identifiant}' introuvable (S/F/Q amont + kit).")
        return 1
    doc = tout[identifiant]
    origine = " [kit]" if identifiant in corpus["kit"] else ""
    if doc["type"] == "scenario":
        cmd_dfiq_arbre(identifiant)
        print("\nUtiliser : dfiq plan <Q-id> pour le plan de reponse d'une question.")
        return 0
    if doc["type"] == "facet":
        print(f"## {doc['id']}{origine} - {doc.get('name')}")
        for question in sorted(enfants(corpus, "facet", doc["id"]), key=lambda d: d.get("id", "")):
            print(f"  - {question['id']} : {question.get('name')} "
                  f"(approches : {len(question.get('approaches') or [])})")
        print("\nUtiliser : dfiq plan <Q-id> pour le plan de reponse d'une question.")
        return 0
    tags = ", ".join(doc.get("tags") or []) or "-"
    print(f"## {doc['id']}{origine} - {doc.get('name')} [{tags}]")
    if doc.get("description"):
        print("   " + " ".join(doc["description"].split()))
    approches = doc.get("approaches") or []
    if not approches:
        print("\nAucune approche executable dans le corpus amont pour cette question.")
        print("Traitement kit : passer par les signaux du catalogue (catalogue/) et les "
              "skills d'analyse ; documenter l'ecart ; candidat a une approche custom "
              "(referentiels-kit/dfiq/).")
        return 0
    definitions = {a.name: (a, o) for a, o in charger_artefacts()}
    for i, approche in enumerate(approches, 1):
        print(f"\n### Approche {i} : {approche.get('name')}")
        if approche.get("description"):
            print("   " + " ".join(approche["description"].split()))
        notes = approche.get("notes") or {}
        if notes.get("covered"):
            print("   couvre : " + " ; ".join(" ".join(str(c).split()) for c in notes["covered"]))
        if notes.get("not_covered"):
            print("   ne couvre pas : "
                  + " ; ".join(" ".join(str(c).split()) for c in notes["not_covered"]))
        for etape in approche.get("steps") or []:
            stage = etape.get("stage", "?")
            print(f"   - [{stage}] {etape.get('name')}")
            if etape.get("type") == "ForensicArtifact" and etape.get("value"):
                cible = definitions.get(etape["value"])
                if cible:
                    print(f"     -> artefact {etape['value']} :")
                    print("     " + decrire_artefact(cible[0], cible[1]).replace("\n", "\n     "))
                else:
                    print(f"     -> artefact {etape['value']} introuvable dans le referentiel "
                          "bake (versions amont evoluent) : chercher dans artefacts index "
                          "ou definir un artefact kit.")
    return 0


def cmd_dfiq_index(sortie: str):
    corpus = charger_dfiq()
    n_app = sum(len(q.get("approaches") or []) for q in corpus["question"].values())
    lignes = [
        f"Index genere depuis le corpus bake ({len(corpus['scenario'])} scenarios, "
        f"{len(corpus['facet'])} facets, {len(corpus['question'])} questions, "
        f"{n_app} approches) - ne pas editer cette section.",
        "",
    ]
    for scenario in sorted(corpus["scenario"].values(), key=lambda d: d.get("id", "")):
        tags = ", ".join(scenario.get("tags") or []) or "-"
        origine = " [kit]" if scenario["id"] in corpus["kit"] else ""
        lignes.append(f"## {scenario['id']}{origine} - {scenario.get('name')} [{tags}]")
        facets = enfants(corpus, "scenario", scenario["id"])
        lignes.append(f"Facets : {len(facets)} ; questions : "
                      f"{sum(len(enfants(corpus, 'facet', f['id'])) for f in facets)}")
        for facet in sorted(facets, key=lambda d: d.get("id", "")):
            origine_f = " [kit]" if facet["id"] in corpus["kit"] else ""
            lignes.append(f"### {facet['id']}{origine_f} - {facet.get('name')}")
            for question in sorted(enfants(corpus, "facet", facet["id"]),
                                   key=lambda d: d.get("id", "")):
                origine_q = " [kit]" if question["id"] in corpus["kit"] else ""
                n = len(question.get("approaches") or [])
                lignes.append(f"- {question['id']}{origine_q} : {question.get('name')} "
                              f"(approches : {n})")
        lignes.append("")
    contenu = "\n".join(lignes)
    if sortie == "-":
        print(contenu)
    else:
        ecrire_genere(Path(sortie), "dfiq", contenu,
                      "# Referentiel DFIQ (Digital Forensics Investigation Questions)\n\n"
                      "Mapping kit et usage : sections ci-dessus et ci-dessous. "
                      "Le corpus amont est bake dans l'image a chaque build.")
        print(f"Index DFIQ ecrit : {sortie}")
    return 0


def cmd_dfiq_check():
    problems = []
    ok_manifest, detail = verifier_manifest(DFIQ_MANIFEST, DFIQ_MANIFEST.parent)
    if not ok_manifest:
        problems.append(f"integrite MANIFEST : {detail}")
    corpus = charger_dfiq()
    if not (corpus["scenario"] and corpus["facet"] and corpus["question"]):
        problems.append("corpus incomplet (S/F/Q)")
    tout = {**corpus["scenario"], **corpus["facet"], **corpus["question"]}
    orphelins = [doc["id"] for doc in {**corpus["facet"], **corpus["question"]}.values()
                 for p in (doc.get("parent_ids") or []) if p not in corpus["scenario"]
                 and p not in corpus["facet"] and p not in corpus["question"]]
    if orphelins:
        problems.append(f"parents introuvables : {', '.join(sorted(set(orphelins))[:5])}")
    info = lire_trace("dfiq")
    if info:
        print(f"  referentiel dfiq : {str(info.get('commit', ''))[:12]} "
              f"(build {info.get('date_build')})")
    print(f"  corpus : S={len(corpus['scenario'])} F={len(corpus['facet'])} "
          f"Q={len(corpus['question'])}, kit={len(corpus['kit'])}")
    if problems:
        print("[dfiq check] ECHEC : " + " ; ".join(problems))
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
    if famille == "artefacts":
        if action == "match" and reste:
            return cmd_artefacts_match(reste[0])
        if action == "expand" and reste:
            return cmd_artefacts_expand(reste[0])
        if action == "index":
            return cmd_artefacts_index(reste[0] if reste else "-")
        if action == "check":
            return cmd_artefacts_check()
    if famille == "dfiq":
        if action == "arbre":
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
