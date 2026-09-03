#!/usr/bin/env python3
"""ingest.py - scan, typage et empreinte des collections d'une affaire.

Usage :
  python3 scripts/ingest.py <dossier_affaire> <chemin_collection>

Pour chaque collection :
  - detection du type d'artefact (extension, signature)
  - calcul SHA256 de la copie importee
  - mise a jour du manifest.yaml de l'affaire
"""
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

# Types d'artefacts reconnus : (extension, description, famille)
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


def copier_collection(source: Path, dest: Path) -> None:
    if source.is_dir():
        shutil.copytree(source, dest, dirs_exist_ok=True)
    else:
        shutil.copy2(source, dest)


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
        print(f"[warn] rapprochement artefacts en echec : "
              f"{(out.stderr or out.stdout).strip().splitlines()[-1][:100] if (out.stderr or out.stdout).strip() else 'retour ' + str(out.returncode)}")


def main():
    if len(sys.argv) != 3:
        print(__doc__)
        return 2
    affaire = Path(sys.argv[1]).resolve()
    source = Path(sys.argv[2]).resolve()
    if not affaire.is_dir() or not source.exists():
        print("Erreur : dossier d'affaire ou collection introuvable.")
        return 1

    originals = affaire / "00_evidence" / "originals"
    originals.mkdir(parents=True, exist_ok=True)

    dest = originals / source.name
    copier_collection(source, dest)

    entree = {
        "nom": source.name,
        "type": detecter_type(source),
        "chemin_original": str(source),
        "copie": str(dest),
        "sha256": sha256_fichier(dest),
        "date_import": datetime.now().isoformat(timespec="seconds"),
    }

    manifest = affaire / "manifest.yaml"
    donnees = yaml.safe_load(manifest.read_text()) if manifest.exists() else {"affaire": {"id": affaire.name}, "collections": []}
    donnees.setdefault("collections", []).append(entree)
    manifest.write_text(yaml.safe_dump(donnees, sort_keys=False, allow_unicode=True))

    print(f"Collection {source.name} importee : sha256={entree['sha256'][:16]}...")
    rapprocher_artefacts(affaire)
    return 0


if __name__ == "__main__":
    sys.exit(main())
