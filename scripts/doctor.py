#!/usr/bin/env python3
"""doctor.py - sante et provisioning du kit OREOA-AI.

Usage :
  python3 scripts/doctor.py check   # sante : prerequis, image, bundle, espace disque
  python3 scripts/doctor.py fix     # provisioning : bundle air-gap ou build de l'image
  python3 scripts/doctor.py test    # tests fonctionnels : outils du conteneur + E2E
"""
import shutil
import subprocess
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("Erreur : module pyyaml requis (pip install pyyaml).")
    sys.exit(1)

KIT = Path(__file__).resolve().parent.parent
CONFIG = KIT / "config" / "tools.yaml"
GO = 1024 ** 3

# (chemin relatif, requis, type)
STRUCTURE = [
    ("AGENTS.md", True, "fichier"),
    ("README.md", True, "fichier"),
    ("MEMORY.md", True, "fichier"),
    ("LICENSE", True, "fichier"),
    ("install.sh", True, "fichier"),
    ("create_case.sh", True, "fichier"),
    ("Dockerfile", True, "fichier"),
    ("opencode.json", True, "fichier"),
    ("config/tools.yaml", True, "fichier"),
    ("scripts/ingest.py", True, "fichier"),
    ("docs/NOTICE", True, "fichier"),
    ("skills", True, "dossier"),
    ("methodologie", True, "dossier"),
    ("catalogue", True, "dossier"),
    ("connaissances", True, "dossier"),
    ("templates", True, "dossier"),
    ("tests/samples", True, "dossier"),
    ("cases", True, "dossier"),
]


def load_config():
    return yaml.safe_load(CONFIG.read_text())


def docker_cmd(args, timeout=90):
    try:
        return subprocess.run(["docker"] + args, capture_output=True, text=True, timeout=timeout)
    except FileNotFoundError:
        return subprocess.CompletedProcess(["docker"], 127, "", "docker absent")
    except subprocess.TimeoutExpired:
        return subprocess.CompletedProcess(["docker"], 124, "", "delai depasse")


def etat_daemon():
    out = docker_cmd(["version", "--format", "{{.Server.Version}}"], timeout=15)
    if out.returncode == 0:
        return True, f"daemon actif (v{out.stdout.strip()})"
    if "permission denied" in out.stderr.lower():
        return False, ("daemon actif mais acces refuse : utilisateur hors du groupe docker "
                       "(corriger avec : sudo usermod -aG docker $USER, puis reconnexion)")
    if out.returncode == 127:
        return False, "docker absent"
    return False, "daemon injoignable"


def image_ref(cfg):
    return f"{cfg['image']['name']}:{cfg['image']['tag']}"


def taille_lisible(octets):
    if octets >= GO:
        return f"{octets / GO:.1f} Go"
    return f"{octets / (1024 * 1024):.0f} Mo"


def image_info(ref):
    out = docker_cmd(["image", "inspect", ref, "--format", "{{.Id}}|{{.Size}}"])
    if out.returncode == 0:
        identifiant, taille = out.stdout.strip().split("|")
        return identifiant, int(taille)
    return None, None


def espace_libre(chemin):
    out = subprocess.run(["df", "-B1", "--output=avail", str(chemin)],
                         capture_output=True, text=True)
    lignes = [l for l in out.stdout.strip().splitlines() if l.strip()]
    try:
        return int(lignes[-1])
    except (IndexError, ValueError):
        return None


def docker_root_dir():
    out = docker_cmd(["info", "--format", "{{.DockerRootDir}}"], timeout=15)
    return out.stdout.strip() if out.returncode == 0 and out.stdout.strip() else "/var/lib/docker"


class Resultat:
    def __init__(self):
        self.ok, self.warn, self.fail = [], [], []
        self.actions_fix = []

    def affiche(self):
        for nom, detail in self.ok:
            print(f"  [ok]   {nom} -- {detail}")
        for nom, detail in self.warn:
            print(f"  [warn] {nom} -- {detail}")
        for nom, detail in self.fail:
            print(f"  [fail] {nom} -- {detail}")

    def verdict(self):
        if self.fail:
            return "ECHEC"
        if self.warn:
            return "AVERTISSEMENTS"
        return "OK"


def run_check():
    cfg = load_config()
    r = Resultat()
    ref = image_ref(cfg)
    bundle = KIT / cfg["provisioning"]["bundle"]
    seuil_build = cfg["provisioning"]["seuil_espace_build_go"] * GO

    # Prerequis
    ok, detail = etat_daemon()
    (r.ok if ok else r.fail).append(("docker", detail))
    r.ok.append(("git", shutil.which("git") or "ABSENT"))
    if not shutil.which("git"):
        r.fail[-1] = ("git", "absent")

    # Structure et scripts
    for rel, requis, genre in STRUCTURE:
        chemin = KIT / rel
        if chemin.exists():
            r.ok.append((rel, "present"))
        else:
            (r.fail if requis else r.warn).append((rel, "absent"))
            if genre == "dossier":
                r.actions_fix.append(lambda c=chemin: c.mkdir(parents=True, exist_ok=True))
    for rel in ("install.sh", "create_case.sh", "scripts/doctor.py",
                "scripts/ingest.py", "scripts/dt"):
        chemin = KIT / rel
        if chemin.exists() and not chemin.stat().st_mode & 0o111:
            r.warn.append((rel, "non executable"))
            r.actions_fix.append(lambda c=chemin: c.chmod(c.stat().st_mode | 0o755))

    # Image
    if ok:
        identifiant, taille = image_info(ref)
        if identifiant:
            r.ok.append((f"image {ref}", f"presente ({taille_lisible(taille)})"))
        else:
            r.warn.append((f"image {ref}", "absente - provisioner avec : python3 scripts/doctor.py fix"))
            if bundle.exists():
                r.ok.append(("bundle air-gap", f"{bundle} detecte (docker load possible)"))
            else:
                r.warn.append(("bundle air-gap", "absent (le provisioning passera par docker build)"))
            # Espace disque (information, la barriere dure est appliquee par fix)
            libre = espace_libre(docker_root_dir())
            if libre is None:
                r.warn.append(("espace disque", "non mesurable"))
            else:
                go_libre = libre / GO
                if libre < seuil_build:
                    r.fail.append(("espace disque", f"{go_libre:.1f} Go libres sur {docker_root_dir()} "
                                                   f"- inferieur au seuil de build ({seuil_build // GO} Go)"))
                else:
                    r.ok.append(("espace disque", f"{go_libre:.1f} Go libres sur {docker_root_dir()}"))
    return r


def run_fix():
    cfg = load_config()
    ref = image_ref(cfg)
    bundle = KIT / cfg["provisioning"]["bundle"]
    seuil_build = cfg["provisioning"]["seuil_espace_build_go"] * GO
    seuil_load = cfg["provisioning"]["seuil_espace_load_go"] * GO

    print("== Provisioning ==")
    r = run_check()
    print("Etat avant intervention :")
    r.affiche()
    for action in r.actions_fix:
        try:
            action()
            print("  [fix] correction structure appliquee")
        except Exception as exc:  # noqa: BLE001
            print(f"  [error] correction impossible : {exc}")

    identifiant, _ = image_info(ref)
    if identifiant:
        print(f"\nImage {ref} deja presente.")
        print(f"  digest : {identifiant}")
        print("  Journalisation conseillee : consigner ce digest dans le journal de l'affaire en cours.")
        return 0

    ok, detail = etat_daemon()
    if not ok:
        print(f"\nProvisioning impossible : {detail}")
        print("Aucune ecriture effectuee. Corriger puis relancer : python3 scripts/doctor.py fix")
        return 1

    # Barriere dure d'espace disque AVANT toute ecriture
    if bundle.exists():
        seuil = seuil_load
        mode = f"docker load du bundle {cfg['provisioning']['bundle']}"
    else:
        seuil = seuil_build
        mode = f"docker build depuis {cfg['image']['dockerfile']}"
    racine = docker_root_dir()
    libre = espace_libre(racine)
    if libre is None:
        print(f"\nProvisioning refuse : espace disque non mesurable sur {racine}.")
        print("Aucune ecriture effectuee.")
        return 1
    if libre < seuil:
        print(f"\nProvisioning REFUSE (barriere d'espace disque).")
        print(f"  Requis : {seuil // GO} Go libres pour {mode}")
        print(f"  Disponible : {libre / GO:.1f} Go sur {racine}")
        print("Aucune ecriture effectuee. Liberer de l'espace puis relancer : python3 scripts/doctor.py fix")
        return 1
    print(f"\nEspace disque : {libre / GO:.1f} Go libres (seuil {seuil // GO} Go respecte)")

    # Provisioning
    if bundle.exists():
        print(f"Chargement du bundle air-gap : {bundle}")
        out = docker_cmd(["load", "-i", str(bundle)], timeout=900)
    else:
        print(f"Construction de l'image depuis {cfg['image']['dockerfile']} "
              f"(premier build possible : plusieurs minutes)...")
        out = subprocess.run(["docker", "build", "-t", ref, str(KIT)],
                             capture_output=True, text=True)
    if out.returncode != 0:
        print(f"\nProvisioning en echec :")
        print((out.stderr or out.stdout)[-1500:])
        return 1

    identifiant, taille = image_info(ref)
    if not identifiant:
        print("Provisioning termine mais image introuvable (verifier le nom dans config/tools.yaml).")
        return 1
    print(f"\nImage {ref} provisionnee ({taille_lisible(taille)}).")
    print(f"  digest : {identifiant}")
    print("  Journalisation conseillee : consigner ce digest dans le journal de l'affaire en cours.")
    return 0


def run_test():
    cfg = load_config()
    ref = image_ref(cfg)
    echecs = 0

    print("== Tests fonctionnels ==")
    identifiant, _ = image_info(ref)
    if not identifiant:
        print(f"  [skip] image {ref} absente : provisionner d'abord (python3 scripts/doctor.py fix)")
    else:
        print(f"Outils du conteneur {ref} :")
        for nom, outil in cfg["outils"].items():
            if outil.get("test_cmd"):
                args = ["sh", "-c", outil["test_cmd"]]
                trace = outil["test_cmd"][:40]
            else:
                args = [outil["binaire"], outil["test"]]
                trace = f"{outil['binaire']} {outil['test']}"
            out = docker_cmd(["run", "--rm", "--network", "none", ref] + args, timeout=120)
            if out.returncode == 0:
                version = (out.stdout or out.stderr).strip().splitlines()[0] if (out.stdout or out.stderr) else ""
                print(f"  [ok]   {nom} ({trace}) -- {version[:70]}")
            else:
                echecs += 1
                print(f"  [fail] {nom} ({trace}) -- {(out.stderr or out.stdout).strip()[:70]}")

        bibliotheques = " ; ".join(f"import {m}" for m in cfg["imports"])
        out = docker_cmd(["run", "--rm", "--network", "none", ref,
                          "python3", "-c", f"{bibliotheques}; print('imports ok')"], timeout=120)
        if out.returncode == 0:
            print(f"  [ok]   bibliotheques python ({', '.join(cfg['imports'])})")
        else:
            echecs += 1
            print(f"  [fail] bibliotheques python -- {(out.stderr or '').strip()[:70]}")

        # Conformite licences : fichiers copyright embarques dans l'image
        fichiers = " ".join(f"/usr/share/doc/{p}/copyright"
                            for p in ("tshark", "sleuthkit", "yara", "hashdeep", "lzip"))
        out = docker_cmd(["run", "--rm", "--network", "none", "--user", "0", ref,
                          "sh", "-c", f"for f in {fichiers}; do test -f $f || exit 1; done; echo ok"],
                         timeout=120)
        if out.returncode == 0:
            print("  [ok]   fichiers copyright des paquets Debian presents (conformite licences)")
        else:
            echecs += 1
            print("  [fail] fichiers copyright des paquets Debian absents")

    print("\nTest de bout en bout (scaffolding, ingestion, manifest, preuves, conteneur) :")
    script = KIT / "tests" / "e2e.sh"
    if script.exists():
        out = subprocess.run([str(script)])
        echecs += out.returncode
    else:
        print("  [fail] tests/e2e.sh absent")
        echecs += 1

    print(f"\nVerdict tests : {'ECHEC' if echecs else 'OK'}")
    return 1 if echecs else 0


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "check"
    if cmd == "check":
        r = run_check()
        r.affiche()
        print(f"Verdict : {r.verdict()}")
        return 0 if not r.fail else 1
    if cmd == "fix":
        return run_fix()
    if cmd == "test":
        return run_test()
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main())
