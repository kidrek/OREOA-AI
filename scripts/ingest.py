#!/usr/bin/env python3
"""ingest.py - collection ingestion: scan, typing, hashing, manifest.

Usage:
  python3 scripts/ingest.py <case_dir> <collection_path>       # external import (copy)
  python3 scripts/ingest.py <case_dir> --scan [-p PROVENANCE]  # scan analyst deposits in 00_evidence/originals/

Modes:
  - external import: copies the collection to 00_evidence/originals/, hashes the
    imported copy (SHA256), updates the manifest, matches referential artifacts
  - deposit scan: walks 00_evidence/originals/ (analyst drop zone), ingests every
    entry not yet recorded (type, SHA256, manifest) with declared provenance, and
    re-verifies the integrity (SHA256) of recorded entries - any drift is an
    INTEGRITY ALERT (exit code 2)
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
    print("Error: pyyaml module required (pip install pyyaml).")
    sys.exit(1)

SCRIPTS = Path(__file__).resolve().parent

# Types d'artefacts reconnus : (description, famille)
# Cles en minuscules : detecter_type() normalise la casse de l'extension.
TYPES = {
    ".evtx": ("Windows event log", "windows"),
    ".evtx.json": ("Windows event log (JSON)", "windows"),
    ".reg": ("exported registry hive", "windows"),
    ".pcap": ("network capture", "network"),
    ".pcapng": ("network capture", "network"),
    ".json": ("log or JSON export", "linux"),
    ".log": ("text log", "linux"),
    ".auth.log": ("authentication log", "linux"),
    ".syslog": ("syslog log", "linux"),
    ".wtm": ("wtmp/btmp (login log)", "linux"),
    ".txt": ("text log", "linux"),
    ".zip": ("archive", "misc"),
    ".tar.gz": ("archive", "misc"),
    ".raw": ("raw memory dump", "memory"),
    ".lime": ("LiME/AVML memory dump", "memory"),
    ".mem": ("raw memory dump", "memory"),
    ".dmp": ("Windows memory dump (minidump/crash)", "memory"),
    ".e01": ("EnCase disk image (EWF)", "disk"),
    ".aff4": ("AFF4 disk image", "disk"),
    ".dd": ("raw disk image", "disk"),
    ".img": ("raw disk image", "disk"),
    ".rawdisk": ("raw disk image (magic-detected)", "disk"),
}

# Magic bytes distinguishing a disk image from a memory dump when the
# extension is ambiguous (.raw used by both):
#   - MBR boot signature 55 AA at offset 510
#   - GPT header "EFI PART" at offset 512
#   - ext2/3/4 superblock magic 53 EF at offset 0x438
DISK_MAGICS = (
    (510, b"\x55\xaa"),
    (512, b"EFI PART"),
    (0x438, b"\x53\xef"),
)


def magic_disque(chemin: Path) -> bool:
    try:
        with chemin.open("rb") as flux:
            for decalage, signature in DISK_MAGICS:
                flux.seek(decalage)
                if flux.read(len(signature)) == signature:
                    return True
    except OSError:
        return False
    return False


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
            # .raw is ambiguous (memory dump vs raw disk image): probe the magic
            if cle == ".raw" and magic_disque(chemin):
                return ".rawdisk"
            return cle
    if nom.endswith((".auth", ".log.1")):
        return ".log"
    return ".inconnu"


def famille_du(type_cle: str) -> str:
    return TYPES.get(type_cle, ("unknown", "misc"))[1]


def taille_fichier(chemin: Path) -> int:
    try:
        return chemin.stat().st_size
    except OSError:
        return 0


def charger_manifest(affaire: Path) -> dict:
    manifest = affaire / "manifest.yaml"
    if manifest.exists():
        return yaml.safe_load(manifest.read_text())
    return {"case": {"id": affaire.name}, "collections": []}


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
           "/work/scripts/referentiels.py", "artifacts", "match",
           "/affaires/manifest.yaml"]
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    except (OSError, subprocess.TimeoutExpired):
        print("[warn] artifact matching skipped (dt unavailable or timed out)")
        return
    if out.returncode == 0:
        for ligne in out.stdout.splitlines():
            if ligne.startswith(("  ", "[artifacts match] manifest")):
                print("  " + ligne.strip())
    else:
        sortie = (out.stderr or out.stdout).strip()
        print(f"[warn] artifact matching failed: "
              f"{sortie.splitlines()[-1][:100] if sortie else 'exit ' + str(out.returncode)}")


def completer_entree(entree: dict, chemin: Path) -> dict:
    """Disk-specific fields + out-of-scope warnings (v2.0 perimeter)."""
    famille = famille_du(entree["type"])
    if famille == "disk":
        entree["size_bytes"] = taille_fichier(chemin)
        if entree["type"] == ".aff4":
            entree["notes"] = ("AFF4 format out of v2.0 exploitation scope "
                               "(documented gap) - pending analyst decision")
            print(f"[warn] {entree['name']}: AFF4 not exploited in v2.0 "
                  "(documented gap) - recorded pending")
    return entree


def importer_copie(affaire: Path, source: Path) -> None:
    originals = affaire / "00_evidence" / "originals"
    originals.mkdir(parents=True, exist_ok=True)

    dest = originals / source.name
    if source.is_dir():
        shutil.copytree(source, dest, dirs_exist_ok=True)
    else:
        shutil.copy2(source, dest)

    entree = {
        "name": source.name,
        "type": detecter_type(source),
        "original_path": str(source),
        "copy": str(dest),
        "sha256": sha256_fichier(dest),
        "imported_at": datetime.now().isoformat(timespec="seconds"),
    }
    completer_entree(entree, dest)
    donnees = charger_manifest(affaire)
    donnees.setdefault("collections", []).append(entree)
    ecrire_manifest(affaire, donnees)

    print(f"Collection {source.name} imported: sha256={entree['sha256'][:16]}...")
    rapprocher_artefacts(affaire)


def scan_depots(affaire: Path, provenance: str) -> int:
    """Scan of 00_evidence/originals/: new imports + integrity of recorded entries."""
    originals = affaire / "00_evidence" / "originals"
    if not originals.is_dir():
        print(f"Error: {originals} missing (case not scaffolded?).")
        return 1
    donnees = charger_manifest(affaire)
    collections = donnees.setdefault("collections", [])
    enregistres = {c["name"]: c for c in collections}

    # 1. Integrity of already recorded entries
    alertes = 0
    for nom, entree in enregistres.items():
        copie = Path(entree["copy"])
        if not copie.exists():
            print(f"[INTEGRITY ALERT] {nom}: recorded entry missing ({copie}) - "
                  "do not proceed without an analyst decision")
            alertes += 1
            continue
        empreinte = sha256_fichier(copie)
        if empreinte != entree["sha256"]:
            print(f"[INTEGRITY ALERT] {nom}: hash drifted since import "
                  f"({entree['sha256'][:16]}... -> {empreinte[:16]}...) - "
                  "do not proceed without an analyst decision")
            alertes += 1

    # 2. Import of unrecorded deposits
    depot = "analyst deposit" + (f" - {provenance}" if provenance else "")
    nouveaux = 0
    for element in sorted(originals.iterdir()):
        if element.name in enregistres:
            continue
        entree = {
            "name": element.name,
            "type": detecter_type(element),
            "original_path": depot,
            "copy": str(element),
            "sha256": sha256_fichier(element),
            "imported_at": datetime.now().isoformat(timespec="seconds"),
        }
        completer_entree(entree, element)
        collections.append(entree)
        nouveaux += 1
        print(f"Deposit imported: {element.name} ({entree['type']}, "
              f"sha256={entree['sha256'][:16]}...)")

    if nouveaux:
        ecrire_manifest(affaire, donnees)
        rapprocher_artefacts(affaire)

    print(f"[scan] {nouveaux} new deposit(s) imported, "
          f"{len(enregistres)} recorded entry(ies) verified")
    if alertes:
        print(f"[scan] {alertes} INTEGRITY ALERT(S): journalize and ask the analyst "
              "for a decision before anything else")
        return 2
    return 0


def main():
    parseur = argparse.ArgumentParser(description=__doc__,
                                      formatter_class=argparse.RawDescriptionHelpFormatter)
    parseur.add_argument("case_dir")
    parseur.add_argument("collection", nargs="?", help="external collection (copy mode)")
    parseur.add_argument("--scan", action="store_true",
                         help="scan analyst deposits in 00_evidence/originals/")
    parseur.add_argument("-p", "--provenance", default="",
                         help="declared provenance of deposits (scan mode)")
    arguments = parseur.parse_args()

    affaire = Path(arguments.case_dir).resolve()
    if not affaire.is_dir():
        print("Error: case directory not found.")
        return 1
    if not arguments.scan and not arguments.collection:
        parseur.error("provide a collection (copy mode) or --scan (deposit mode)")
    if arguments.scan and arguments.collection:
        parseur.error("--scan takes no collection: deposits are already in originals/")

    if arguments.scan:
        return scan_depots(affaire, arguments.provenance)

    source = Path(arguments.collection).resolve()
    if not source.exists():
        print("Error: collection not found.")
        return 1
    importer_copie(affaire, source)
    return 0


if __name__ == "__main__":
    sys.exit(main())
