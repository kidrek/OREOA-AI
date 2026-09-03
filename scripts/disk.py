#!/usr/bin/env python3
"""disk.py - disk image tooling (The Sleuth Kit, raw + E01/EWF).

Runs INSIDE the container (via dt): case evidence mounted at /affaires
(00_evidence read-only), artifacts paths file can come from
`referentiels.py artifacts paths <name>` (one path per line).

AFF4 images are out of the v2.0 exploitation scope (documented gap).

Usage:
  disk.py info <image>                        image format, media size, partitions,
                                              filesystems, disk-space barrier check
  disk.py verify <image>                      SHA256 of the image + E01 metadata (media
                                              size, acquisition header, embedded digest)
  disk.py bodyfile <image> --offset SECTORS --out <path.body>
                                              recursive TSK bodyfile (fls -r -p -m /)
  disk.py extract <image> --offset SECTORS --paths <paths.txt> --out <dir>
                                              targeted extraction (icat) of paths matching
                                              the request list (suffix + wildcard match),
                                              TSV report with SHA256 per extracted file

Offsets are in 512-byte sectors (mmls "Start" column convention) unless
--sector-size overrides. Partition-less filesystems use --offset 0.
"""
import argparse
import fnmatch
import hashlib
import os
import re
import subprocess
import sys
from pathlib import Path

SECTEUR_DEFAUT = 512

# Disk-space barrier (multiplier of the image size) applied before writes:
# the super-timeline storage and the extractions must fit beside the image.
MULTIPLICATEUR_ESPACE = 3


def sha256_fichier(chemin: Path, bloc=1024 * 1024) -> str:
    h = hashlib.sha256()
    with chemin.open("rb") as flux:
        while morceau := flux.read(bloc):
            h.update(morceau)
    return h.hexdigest()


def espace_libre(chemin: str) -> int:
    return os.statvfs(chemin).f_bavail * os.statvfs(chemin).f_frsize


def ouvrir_image(chemin: str):
    """pytsk3 Img_Info (auto-detects raw and EWF/E01 via libtsk)."""
    import pytsk3
    return pytsk3.Img_Info(chemin)


def verifier_espace(chemin_image: Path, destination: str, action: str,
                    multiplicateur: int = MULTIPLICATEUR_ESPACE) -> bool:
    taille = chemin_image.stat().st_size
    requis = taille * multiplicateur
    libre = espace_libre(destination)
    ok = libre >= requis
    print(f"[space] image: {taille} bytes, free: {libre} bytes, "
          f"required: {requis} bytes ({multiplicateur}x) -> "
          f"{'OK' if ok else 'INSUFFICIENT'}")
    if not ok:
        print(f"[barrier] {action} refused: free the space first "
              "(kit rule: no write below the disk barrier)")
    return ok


def cmd_info(chemin_image: Path):
    if not chemin_image.is_file():
        print(f"Error: image not found: {chemin_image}", file=sys.stderr)
        return 1
    taille = chemin_image.stat().st_size

    # Format (TSK auto-detection)
    out = subprocess.run(["img_stat", str(chemin_image)], capture_output=True, text=True)
    type_image = "unknown"
    if out.returncode == 0:
        m = re.search(r"Image type:\s*(\S+)", out.stdout, re.IGNORECASE)
        if m:
            type_image = m.group(1)
    print(f"[info] image: {chemin_image}")
    print(f"[info] format: {type_image} (TSK auto-detection)")
    print(f"[info] file_size: {taille}")

    # E01 metadata (pyewf): media size + acquisition header + embedded digest
    if type_image.lower() == "ewf":
        try:
            import pyewf
            h = pyewf.handle()
            h.open([str(chemin_image)], "r")
            print(f"[info] ewf_media_size: {h.get_media_size()}")
            entetes = {}
            try:
                entetes = h.get_header_values() or {}
            except Exception:  # noqa: BLE001
                pass
            for cle in ("case_number", "evidence_number", "examiner",
                        "acquisition_date", "description"):
                if entetes.get(cle):
                    print(f"[info] ewf_header.{cle}: {entetes[cle]}")
            try:
                # libewf stores the acquisition digest (MD5) in the hash section
                empreinte = h.get_calculated_digest()
                if empreinte:
                    print(f"[info] ewf_media_digest: {empreinte.hex()}")
            except Exception:  # noqa: BLE001
                print("[info] ewf_media_digest: unavailable")
            h.close()
        except Exception as exc:  # noqa: BLE001
            print(f"[warn] E01 metadata unreadable: {exc}")

    # Partition table (mmls) - text parse of the Start column
    partitions = []
    out = subprocess.run(["mmls", "-B", str(chemin_image)],
                         capture_output=True, text=True)
    if out.returncode == 0:
        for ligne in out.stdout.splitlines():
            m = re.match(r"\s*(\d+):\s+\d+:\d+\s+(\d+)\s+\d+\s+\d+\s+(\S.*)$", ligne)
            if m:
                partitions.append((int(m.group(2)), m.group(3).strip()))
    if partitions:
        print(f"[info] partitions ({len(partitions)}):")
        for debut, description in partitions:
            print(f"[info]   offset_sectors={debut} ({description})")
    else:
        print("[info] partitions: none detected (partition-less filesystem "
              "or non-partitioned image -> use --offset 0)")

    # Filesystem detection per candidate offset
    candidats = [(debut, description) for debut, description in partitions] or [(0, "whole image")]
    img = None
    try:
        img = ouvrir_image(str(chemin_image))
        import pytsk3
        for debut, description in candidats:
            try:
                fs = pytsk3.FS_Info(img, offset=debut * SECTEUR_DEFAUT)
                ftype = fs.info.ftype
                noms = {v: k for k, v in vars(pytsk3).items()
                        if k.startswith("TSK_FS_TYPE") and isinstance(v, int)}
                nom = noms.get(ftype, f"type_{ftype}")
                print(f"[info] filesystem: offset_sectors={debut} ({description}) -> {nom}")
            except Exception:  # noqa: BLE001
                print(f"[info] filesystem: offset_sectors={debut} ({description}) -> none detected")
    except Exception as exc:  # noqa: BLE001
        print(f"[error] image unreadable by TSK: {exc}", file=sys.stderr)
        return 1
    finally:
        if img is not None:
            img.close()

    # Disk-space barrier visibility (writes happen outside 00_evidence: 01_work,
    # 02_analysis, plaso storage). Informational here, enforced by the analyst.
    libre = espace_libre(str(chemin_image.parent))
    verifier_espace(chemin_image, str(chemin_image.parent), "timeline/extraction writes")
    return 0


def cmd_verify(chemin_image: Path) -> int:
    if not chemin_image.is_file():
        print(f"Error: image not found: {chemin_image}", file=sys.stderr)
        return 1
    print(f"[verify] image: {chemin_image}")
    print(f"[verify] sha256: {sha256_fichier(chemin_image)}")
    with chemin_image.open("rb") as flux:
        if flux.read(8) == b"EVF\x09\x0d\x0a\xff\x00":
            try:
                import pyewf
                h = pyewf.handle()
                h.open([str(chemin_image)], "r")
                print(f"[verify] ewf_media_size: {h.get_media_size()}")
                try:
                    empreinte = h.get_calculated_digest()
                    if empreinte:
                        print(f"[verify] ewf_media_digest(md5): {empreinte.hex()}")
                except Exception:  # noqa: BLE001
                    print("[verify] ewf_media_digest(md5): unavailable in this libewf build")
                h.close()
            except Exception as exc:  # noqa: BLE001
                print(f"[warn] E01 metadata unreadable: {exc}")
    return 0


def lire_listing(chemin_image: Path, offset: int) -> list:
    """fls -r -p -> [{'type','deleted','inode','path'}] (paths normalized to /)."""
    out = subprocess.run(["fls", "-r", "-p", "-o", str(offset), str(chemin_image)],
                         capture_output=True, text=True, timeout=1800)
    if out.returncode != 0:
        print(f"Error: fls failed: {(out.stderr or '').strip()[:300]}", file=sys.stderr)
        sys.exit(1)
    entrees = []
    for ligne in out.stdout.splitlines():
        morceaux = ligne.split("\t", 1)
        if len(morceaux) != 2:
            continue
        entete, chemin = morceaux
        champs = entete.split()
        if len(champs) < 2 or ":" not in champs[-1]:
            continue
        entrees.append({
            "type": champs[0],
            "deleted": "*" in champs[1:-1],
            "inode": champs[-1].rstrip(":").strip("()"),
            "path": chemin.replace("\\", "/").strip("/"),
        })
    return entrees


def normaliser(pattern: str) -> list:
    """Artifact path -> component list (drive stripped, lowercased, / separated)."""
    pattern = pattern.strip().replace("\\", "/")
    pattern = re.sub(r"^[A-Za-z]:", "", pattern)
    return [c.casefold() for c in pattern.split("/") if c not in ("", ".", "..")]


def matcher(cible: list, chemin: list) -> bool:
    """Suffix component matching, case-insensitive, wildcards:
    '*' (fnmatch) and referential placeholders match any single component."""
    if not cible or len(cible) > len(chemin):
        return False
    fenetre = chemin[len(chemin) - len(cible):]
    for motif, composant in zip(cible, fenetre):
        if motif.startswith("<") and motif.endswith(">"):
            continue
        if not fnmatch.fnmatch(composant, motif):
            return False
    return True


def cmd_bodyfile(chemin_image: Path, offset: int, sortie: Path) -> int:
    if not chemin_image.is_file():
        print(f"Error: image not found: {chemin_image}", file=sys.stderr)
        return 1
    if not verifier_espace(chemin_image, str(sortie.parent), "bodyfile/super-timeline"):
        return 1
    out = subprocess.run(["fls", "-r", "-p", "-m", "/", "-o", str(offset),
                          str(chemin_image)], capture_output=True, text=True,
                         timeout=1800)
    if out.returncode != 0 and not out.stdout.strip():
        print(f"Error: fls -m failed: {(out.stderr or '').strip()[:300]}", file=sys.stderr)
        return 1
    sortie.parent.mkdir(parents=True, exist_ok=True)
    n_lignes = 0
    with sortie.open("w") as flux:
        for ligne in out.stdout.splitlines():
            if ligne.strip():
                flux.write(ligne + "\n")
                n_lignes += 1
    print(f"[bodyfile] {sortie} written ({n_lignes} entries, offset {offset})")
    return 0


def cmd_extract(chemin_image: Path, offset: int, cibles_path: Path, sortie_dir: Path) -> int:
    if not chemin_image.is_file():
        print(f"Error: image not found: {chemin_image}", file=sys.stderr)
        return 1
    cibles = [l.strip() for l in cibles_path.read_text().splitlines()
              if l.strip() and not l.strip().startswith("#")]
    if not cibles:
        print("Error: empty paths file (one resolved artifact path per line).", file=sys.stderr)
        return 1
    if not verifier_espace(chemin_image, str(sortie_dir.parent), "extraction",
                           multiplicateur=1):
        return 1
    entrees = lire_listing(chemin_image, offset)
    sortie_dir.mkdir(parents=True, exist_ok=True)
    rapport = sortie_dir / "extraction-report.txt"
    n_extraits, n_echecs = 0, 0
    with rapport.open("w") as flux:
        flux.write("# disk.py extraction report - image: %s offset_sectors: %d\n"
                   % (chemin_image.name, offset))
        flux.write("# requested_path\tinode\ttype\tdest_file\tsha256\tstatus\n")
        for cible in cibles:
            motif = normaliser(cible)
            correspondances = [e for e in entrees
                               if not e["type"].startswith("d/")
                               and matcher(motif, normaliser(e["path"]))]
            if not correspondances:
                flux.write(f"{cible}\t-\t-\t-\t-\tnot-found\n")
                print(f"[extract] not found: {cible}")
                continue
            for entree in correspondances:
                dest = sortie_dir / Path(entree["path"]).name
                if dest.exists():
                    dest = sortie_dir / f"{entree['inode'].replace(':', '-')}_{Path(entree['path']).name}"
                out = subprocess.run(["icat", "-o", str(offset), str(chemin_image),
                                      entree["inode"]], capture_output=True, timeout=600)
                statut = "extracted"
                if out.returncode != 0:
                    statut = "failed"
                    n_echecs += 1
                else:
                    dest.write_bytes(out.stdout)
                    n_extraits += 1
                empreinte = sha256_fichier(dest) if statut == "extracted" else "-"
                flux.write(f"{entree['path']}\t{entree['inode']}\t{entree['type']}"
                           f"\t{dest.name if statut == 'extracted' else '-'}\t{empreinte}\t{statut}\n")
                print(f"[extract] {statut}: {entree['path']} (inode {entree['inode']}"
                      + (f", sha256={empreinte[:16]}...)" if empreinte != "-" else ")"))
    print(f"[extract] done: {n_extraits} extracted, {n_echecs} failed -> {rapport}")
    return 0


def resoudre_offset(chemin_image: Path, offset: str) -> int:
    if offset == "auto":
        out = subprocess.run(["mmls", "-B", str(chemin_image)],
                             capture_output=True, text=True)
        if out.returncode == 0:
            for ligne in out.stdout.splitlines():
                m = re.match(r"\s*(\d+):\s+\d+:\d+\s+(\d+)\s+\d+\s+\d+\s+\S.*$", ligne)
                if m:
                    return int(m.group(2))
        return 0
    try:
        return int(offset)
    except ValueError:
        print(f"Error: invalid offset: {offset}", file=sys.stderr)
        sys.exit(1)


def main():
    parseur = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parseur.add_argument("action", choices=["info", "verify", "bodyfile", "extract"])
    parseur.add_argument("image")
    parseur.add_argument("--offset", default="auto",
                         help="partition offset in 512-byte sectors (mmls Start) or 'auto'")
    parseur.add_argument("--out", help="output file (bodyfile) or directory (extract)")
    parseur.add_argument("--paths", help="target paths file (one resolved path per line)")
    arguments = parseur.parse_args()
    chemin_image = Path(arguments.image)
    offset = resoudre_offset(chemin_image, arguments.offset)
    if arguments.action == "info":
        return cmd_info(chemin_image)
    if arguments.action == "verify":
        return cmd_verify(chemin_image)
    if arguments.action == "bodyfile":
        if not arguments.out:
            print("Error: --out required for bodyfile.", file=sys.stderr)
            return 1
        return cmd_bodyfile(chemin_image, offset, Path(arguments.out))
    if arguments.action == "extract":
        if not arguments.out or not arguments.paths:
            print("Error: --out and --paths required for extract.", file=sys.stderr)
            return 1
        return cmd_extract(chemin_image, offset, Path(arguments.paths), Path(arguments.out))
    return 2


if __name__ == "__main__":
    sys.exit(main())
