#!/usr/bin/env python3
"""fetch_referentiels.py - telechargement et verification des referentiels amont.

Execute DANS le conteneur au build (phase en-ligne du provisioning).
Usage : python3 fetch_referentiels.py /referentiels

Referentiels telecharges :
  - ForensicArtifacts/artifacts : release la plus recente au moment du build
  - google/dfiq : branche main (HEAD au moment du build)

Chaque referentiel recoit :
  - data/           : definitions verbatim (sans modification)
  - MANIFEST.sha256 : empreinte SHA256 de chaque fichier (integrite verifiable)
  - LICENSE         : licence amont copiee avec les donnees

Trace bakee dans /referentiels/traces/ : source, version, date, empreintes.
Tout echec de telechargement ou de verification fait echouer le build.
"""
import hashlib
import io
import json
import sys
import tarfile
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import yaml

API = "https://api.github.com"
SOURCE_ARTIFACTS = "https://github.com/ForensicArtifacts/artifacts"
SOURCE_DFIQ = "https://github.com/google/dfiq"


def telecharger(url: str, timeout: int = 180) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "oreoa-ai-kit"})
    with urllib.request.urlopen(req, timeout=timeout) as reponse:
        return reponse.read()


def sha256(octets: bytes) -> str:
    return hashlib.sha256(octets).hexdigest()


def ecrire_manifest(racine: Path) -> int:
    """Empreinte SHA256 de chaque fichier data/ -> MANIFEST.sha256."""
    lignes = []
    for fichier in sorted((racine / "data").rglob("*")):
        if fichier.is_file():
            relatif = fichier.relative_to(racine).as_posix()
            lignes.append(f"{sha256(fichier.read_bytes())}  {relatif}")
    (racine / "MANIFEST.sha256").write_text("\n".join(lignes) + "\n")
    return len(lignes)


def extraire_membres(tar_bytes: bytes, racine_tar: str, source_sous: str,
                     dest: Path,licence: bool = True) -> int:
    """Extrait <racine_tar>/<source_sous>/*.yaml + LICENSE du tarball."""
    dest.mkdir(parents=True, exist_ok=True)
    n = 0
    with tarfile.open(fileobj=io.BytesIO(tar_bytes), mode="r:gz") as tar:
        for membre in tar.getmembers():
            nom = membre.name
            if licence and nom.endswith("/LICENSE"):
                (dest / "LICENSE").write_bytes(tar.extractfile(membre).read())
                continue
            if not nom.startswith(f"{racine_tar}/{source_sous}/"):
                continue
            if not nom.endswith(".yaml"):
                continue
            cible = dest / "data" / Path(nom).relative_to(f"{racine_tar}/{source_sous}")
            cible.parent.mkdir(parents=True, exist_ok=True)
            cible.write_bytes(tar.extractfile(membre).read())
            n += 1
    return n


def referentiel_artifacts(dest: Path, date_build: str) -> dict:
    url_latest = f"{SOURCE_ARTIFACTS}/releases/latest"
    tag = urllib.request.urlopen(
        urllib.request.Request(url_latest, headers={"User-Agent": "oreoa-ai-kit"}),
        timeout=120).geturl().rstrip("/").split("/tag/")[-1]
    url_tar = f"{SOURCE_ARTIFACTS}/archive/refs/tags/{tag}.tar.gz"
    tar_bytes = telecharger(url_tar)
    racine_tar = f"artifacts-{tag}"
    fichiers = extraire_membres(tar_bytes, racine_tar, "artifacts/data",
                                dest / "artifacts")
    if fichiers == 0:
        raise RuntimeError(f"aucune definition extraite depuis {url_tar}")
    nombre = ecrire_manifest(dest / "artifacts")
    entree = {
        "source": SOURCE_ARTIFACTS,
        "release": tag,
        "tarball": url_tar,
        "tarball_sha256": sha256(tar_bytes),
        "fichiers": nombre,
        "date_build": date_build,
    }
    return entree


def referentiel_dfiq(dest: Path, date_build: str) -> dict:
    commit, date_commit = None, None
    try:
        info = json.loads(telecharger(f"{API}/repos/google/dfiq/commits/main"))
        commit = info["sha"]
        date_commit = info["commit"]["committer"]["date"]
        url_tar = f"https://codeload.github.com/google/dfiq/tar.gz/{commit}"
    except Exception:  # noqa: BLE001 - API indisponible : fallback branche main
        url_tar = "https://github.com/google/dfiq/archive/refs/heads/main.tar.gz"
    tar_bytes = telecharger(url_tar)
    with tarfile.open(fileobj=io.BytesIO(tar_bytes), mode="r:gz") as tar:
        racine_tar = tar.getmembers()[0].name.split("/")[0]
    n_sc = extraire_membres(tar_bytes, racine_tar, "dfiq/data/scenarios", dest / "dfiq")
    n_fa = extraire_membres(tar_bytes, racine_tar, "dfiq/data/facets", dest / "dfiq")
    n_qu = extraire_membres(tar_bytes, racine_tar, "dfiq/data/questions", dest / "dfiq")
    total = n_sc + n_fa + n_qu
    if n_sc == 0 or n_fa == 0 or n_qu == 0:
        raise RuntimeError(f"corpus DFIQ incomplet (S={n_sc}, F={n_fa}, Q={n_qu})")
    ecrire_manifest(dest / "dfiq")
    return {
        "source": SOURCE_DFIQ,
        "commit": commit or "branche main (API indisponible)",
        "date_commit": date_commit or "inconnue",
        "tarball": url_tar,
        "tarball_sha256": sha256(tar_bytes),
        "scenarios": n_sc, "facets": n_fa, "questions": n_qu,
        "date_build": date_build,
    }


def ecrire_trace(chemin: Path, entree: dict, titre: str) -> None:
    lignes = [f"# {titre}", ""] + [f"{k}: {v}" for k, v in entree.items()]
    chemin.write_text("\n".join(lignes) + "\n")


def main():
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    base = Path(sys.argv[1])
    date_build = datetime.now(timezone.utc).isoformat(timespec="seconds")
    traces = base / "traces"
    traces.mkdir(parents=True, exist_ok=True)

    print(f"[referentiels] ForensicArtifacts : telechargement release la plus recente...")
    entree_a = referentiel_artifacts(base, date_build)
    ecrire_trace(traces / "artifacts.txt", entree_a, "Trace referentiel ForensicArtifacts")
    print(f"[referentiels] artifacts {entree_a['release']} : {entree_a['fichiers']} fichiers")

    print("[referentiels] DFIQ : telechargement de la branche main...")
    entree_d = referentiel_dfiq(base, date_build)
    ecrire_trace(traces / "dfiq.txt", entree_d, "Trace referentiel DFIQ")
    print(f"[referentiels] dfiq {str(entree_d['commit'])[:12]} : "
          f"S={entree_d['scenarios']} F={entree_d['facets']} Q={entree_d['questions']}")

    # Validation : chaque YAML doit etre parsable, chaque definition avoir un nom
    for racine, sous in ((base / "artifacts", "data"), (base / "dfiq", "data")):
        for fichier in sorted((racine / sous).rglob("*.yaml")):
            docs = yaml.safe_load_all(fichier.read_text())
            n = 0
            for doc in docs:
                if doc and not doc.get("name"):
                    raise RuntimeError(f"definition sans nom : {fichier}")
                n += 1
            if n == 0:
                raise RuntimeError(f"fichier vide : {fichier}")

    for element in [base] + list(base.rglob("*")):
        try:
            if element.is_dir():
                element.chmod(0o755)
            else:
                element.chmod(0o644)
        except OSError:
            pass
    print("[referentiels] OK - traces et MANIFEST.sha256 bakes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
