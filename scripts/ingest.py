#!/usr/bin/env python3
"""ingest.py - scan, typage et empreinte des collections d'une affaire.

Usage :
  python3 scripts/ingest.py <dossier_affaire> <chemin_collection>     # import d'une collection externe (copie)
  python3 scripts/ingest.py <dossier_affaire> --scan [-p PROVENANCE]  # scan des depots dans 00_evidence/originals/

Modes :
  - import externe : copie la collection vers 00_evidence/originals/, calcule le
    SHA256 de la copie importee, met a jour le manifest, rapproche les artefacts
  - scan des depots : parcourt 00_evidence/originals/ (depot de l'analyste),
    importe (type, SHA256, manifest) tout element non encore enregistre, avec
    provenance declaree ; reverifie l'integrite (SHA256) des elements deja
    enregistres - toute derivation est une ALERTE d'integrite (code retour 2)
"""
import argparse
import hashlib
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

try:
    import yaml
except ImportError:
    print("Erreur : module pyyaml requis (pip install pyyaml).")
    sys.exit(1)

SCRIPTS = Path(__file__).resolve().parent

# Types d'artefacts reconnus : (description, famille)
# Cles en minuscules : detecter_type() normalise la casse de l'extension.
TYPES = {
    ".evtx": ("journal evenements Windows", "windows"),
    ".evtx.json": ("journal evenements Windows (JSON)", "windows"),
    ".reg": ("ruche registre exportee", "windows"),
    ".pcap": ("capture reseau", "reseau"),
    ".pcapng": ("capture reseau", "reseau"),
    ".json": ("journal ou export JSON", "linux"),
    ".log": ("journal texte", "linux"),
    ".auth.log": ("journal authentification", "linux"),
    ".syslog": ("journal syslog", "linux"),
    ".wtm": ("wtmp/btmp (journal connexions)", "linux"),
    ".txt": ("journal texte", "linux"),
    ".zip": ("archive", "divers"),
    ".tar.gz": ("archive", "divers"),
    ".raw": ("dump memoire brut (raw)", "memoire"),
    ".lime": ("dump memoire LiME/AVML", "memoire"),
    ".mem": ("dump memoire brut", "memoire"),
    ".dmp": ("dump memoire Windows (minidump/crash)", "memoire"),
    ".e01": ("image disque EnCase", "disque"),
    ".aff4": ("image disque AFF4", "disque"),
}


def sha256_fichier(chemin: Path, bloc=1024 * 1024) -> str:
    h = hashlib.sha256()
    with chemin.open("rb") as flux:
        while morceau := flux.read(bloc):
            h.update(morceau)
    return h.hexdigest()


def detecter_type(chemin: Path) -> str:
    nom = chemin.name.lower()
    suffixes = "".join(chemin.suffixes[-2:]).lower()
    for cle in (suffixes, chemin.suffix.lower()):
        if cle in TYPES:
            return cle
    if nom.endswith((".auth", ".log.1")):
        return ".log"
    return ".inconnu"


def charger_manifest(affaire: Path) -> dict:
    manifest = affaire / "manifest.yaml"
    if manifest.exists():
        return yaml.safe_load(manifest.read_text())
    return {"affaire": {"id": affaire.name}, "collections": []}


def ecrire_manifest(affaire: Path, donnees: dict) -> None:
    (affaire / "manifest.yaml").write_text(
        yaml.safe_dump(donnees, sort_keys=False, allow_unicode=True))


def rapprocher_artefacts(affaire: Path) -> None:
    """Rapproche les collections des definitions d'artefacts (referentiel in-image).

    Execution conteneurisee via dt (scripts/referentiels.py). Non bloquant :
    en l'absence d'image, le manifest reste sans champ artefacts (doctor check
    signale l'image absente).
    """
    cmd = [str(SCRIPTS / "dt"), "-c", affaire.name, "python3",
           "/work/scripts/referentiels.py", "artefacts", "match",
           "/affaires/manifest.yaml"]
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    except (OSError, subprocess.TimeoutExpired):
        print("[warn] rapprochement artefacts non effectue (dt indisponible ou delai depasse)")
        return
    if out.returncode == 0:
        for ligne in out.stdout.splitlines():
            if ligne.startswith(("  ", "[artefacts match] manifest")):
                print("  " + ligne.strip())
    else:
        sortie = (out.stderr or out.stdout).strip()
        print(f"[warn] rapprochement artefacts en echec : "
              f"{sortie.splitlines()[-1][:100] if sortie else 'retour ' + str(out.returncode)}")


def importer_copie(affaire: Path, source: Path) -> None:
    originals = affaire / "00_evidence" / "originals"
    originals.mkdir(parents=True, exist_ok=True)

    dest = originals / source.name
    if source.is_dir():
        shutil.copytree(source, dest, dirs_exist_ok=True)
    else:
        shutil.copy2(source, dest)

    entree = {
        "nom": source.name,
        "type": detecter_type(source),
        "chemin_original": str(source),
        "copie": str(dest),
        "sha256": sha256_fichier(dest),
        "date_import": datetime.now().isoformat(timespec="seconds"),
    }
    donnees = charger_manifest(affaire)
    donnees.setdefault("collections", []).append(entree)
    ecrire_manifest(affaire, donnees)

    print(f"Collection {source.name} importee : sha256={entree['sha256'][:16]}...")
    rapprocher_artefacts(affaire)


def scan_depots(affaire: Path, provenance: str) -> int:
    """Scan de 00_evidence/originals/ : imports nouveaux + integrite des enregistres."""
    originals = affaire / "00_evidence" / "originals"
    if not originals.is_dir():
        print(f"Erreur : {originals} inexistant (affaire scaffoldee ?).")
        return 1
    donnees = charger_manifest(affaire)
    collections = donnees.setdefault("collections", [])
    enregistres = {c["nom"]: c for c in collections}

    # 1. Integrite des elements deja enregistres
    alertes = 0
    for nom, entree in enregistres.items():
        copie = Path(entree["copie"])
        if not copie.exists():
            print(f"[ALERTE INTEGRITE] {nom} : element enregistre introuvable "
                  f"({copie}) - ne pas continuer sans decision analyste")
            alertes += 1
            continue
        empreinte = sha256_fichier(copie)
        if empreinte != entree["sha256"]:
            print(f"[ALERTE INTEGRITE] {nom} : empreinte deriver depuis l'import "
                  f"({entree['sha256'][:16]}... -> {empreinte[:16]}...) - "
                  "ne pas continuer sans decision analyste")
            alertes += 1

    # 2. Import des depots non encore enregistres
    depot_manuel = "depot manuel analyste" + (f" - {provenance}" if provenance else "")
    nouveaux = 0
    for element in sorted(originals.iterdir()):
        if element.name in enregistres:
            continue
        entree = {
            "nom": element.name,
            "type": detecter_type(element),
            "chemin_original": depot_manuel,
            "copie": str(element),
            "sha256": sha256_fichier(element),
            "date_import": datetime.now().isoformat(timespec="seconds"),
        }
        collections.append(entree)
        nouveaux += 1
        print(f"Depot importe : {element.name} ({entree['type']}, "
              f"sha256={entree['sha256'][:16]}...)")

    if nouveaux:
        ecrire_manifest(affaire, donnees)
        rapprocher_artefacts(affaire)

    print(f"[scan] {nouveaux} nouveau(x) depot(s) importe(s), "
          f"{len(enregistres)} element(s) deja enregistre(s) verifies")
    if alertes:
        print(f"[scan] {alertes} ALERTE(S) D'INTEGRITE : journaliser et demander "
              "la decision de l'analyste avant toute suite")
        return 2
    return 0


def main():
    parseur = argparse.ArgumentParser(description=__doc__,
                                      formatter_class=argparse.RawDescriptionHelpFormatter)
    parseur.add_argument("dossier_affaire")
    parseur.add_argument("collection", nargs="?", help="collection externe (mode copie)")
    parseur.add_argument("--scan", action="store_true",
                         help="scan des depots de 00_evidence/originals/")
    parseur.add_argument("-p", "--provenance", default="",
                         help="provenance declaree des depots (mode scan)")
    arguments = parseur.parse_args()

    affaire = Path(arguments.dossier_affaire).resolve()
    if not affaire.is_dir():
        print("Erreur : dossier d'affaire introuvable.")
        return 1
    if not arguments.scan and not arguments.collection:
        parseur.error("fournir une collection (mode copie) ou --scan (mode depots)")
    if arguments.scan and arguments.collection:
        parseur.error("--scan ne prend pas de collection : les depots sont deja dans originals/")

    if arguments.scan:
        return scan_depots(affaire, arguments.provenance)

    source = Path(arguments.collection).resolve()
    if not source.exists():
        print("Erreur : collection introuvable.")
        return 1
    importer_copie(affaire, source)
    return 0


if __name__ == "__main__":
    sys.exit(main())
