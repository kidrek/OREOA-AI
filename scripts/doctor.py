#!/usr/bin/env python3
"""doctor.py - sante du kit DFIR Agent Kit.

Usage :
  python3 scripts/doctor.py check   # verification de sante
  python3 scripts/doctor.py fix     # reparation des problemes corretables
  python3 scripts/doctor.py test    # tests fonctionnels de bout en bout
"""
import shutil
import subprocess
import sys
from pathlib import Path

KIT = Path(__file__).resolve().parent.parent

# (chemin relatif, requis, type)
STRUCTURE = [
    ("AGENTS.md", True, "fichier"),
    ("README.md", True, "fichier"),
    ("install.sh", True, "fichier"),
    ("create_case.sh", True, "fichier"),
    ("Dockerfile", True, "fichier"),
    ("opencode.json", True, "fichier"),
    ("config/tools.yaml", True, "fichier"),
    ("scripts/ingest.py", True, "fichier"),
    ("skills", True, "dossier"),
    ("methodologie", True, "dossier"),
    ("catalogue", True, "dossier"),
    ("templates", True, "dossier"),
    ("tests/samples", True, "dossier"),
    ("cases", True, "dossier"),
]


def check_docker():
    try:
        out = subprocess.run(
            ["docker", "version", "--format", "{{.Server.Version}}"],
            capture_output=True, text=True, timeout=10,
        )
        if out.returncode == 0:
            return True, f"daemon actif (v{out.stdout.strip()})"
        if "permission denied" in out.stderr.lower():
            return False, (
                "daemon actif mais acces refuse : utilisateur hors du groupe docker "
                "(corriger avec : sudo usermod -aG docker $USER, puis reconnexion)"
            )
        return False, "daemon injoignable"
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False, "docker absent"


class Resultat:
    def __init__(self):
        self.ok = []      # (nom, detail)
        self.warn = []    # (nom, detail)
        self.fail = []    # (nom, detail)
        self.actions_fix = []  # callables pour fix

    def verdict(self):
        if self.fail:
            return "ECHEC"
        if self.warn:
            return "AVERTISSEMENTS"
        return "OK"

    def affiche(self):
        for nom, detail in self.ok:
            print(f"  [ok]  {nom} -- {detail}")
        for nom, detail in self.warn:
            print(f"  [warn] {nom} -- {detail}")
        for nom, detail in self.fail:
            print(f"  [fail] {nom} -- {detail}")


def run_check(fix=False):
    r = Resultat()

    # Docker
    ok, detail = check_docker()
    (r.ok if ok else r.fail).append(("docker", detail))

    # Git
    if shutil.which("git"):
        r.ok.append(("git", shutil.which("git")))
    else:
        r.fail.append(("git", "absent"))

    # Structure
    for rel, requis, genre in STRUCTURE:
        chemin = KIT / rel
        if chemin.exists():
            r.ok.append((rel, "present"))
        else:
            cible = r.fail if requis else r.warn
            cible.append((rel, "absent"))
            if genre == "dossier":
                r.actions_fix.append(lambda c=chemin: c.mkdir(parents=True, exist_ok=True))

    # Scripts executables
    for rel in ("install.sh", "create_case.sh", "scripts/doctor.py", "scripts/ingest.py"):
        chemin = KIT / rel
        if chemin.exists() and not chemin.stat().st_mode & 0o111:
            r.warn.append((rel, "non executable"))
            r.actions_fix.append(lambda c=chemin: c.chmod(c.stat().st_mode | 0o755))

    return r


def run_fix():
    r = run_check()
    print("Reparation :")
    for action in r.actions_fix:
        try:
            action()
            print("  [fix] applique")
        except Exception as exc:  # noqa: BLE001
            print(f"  [error] {exc}")
    print("Nouvelle verification :")
    r2 = run_check()
    r2.affiche()
    return 0 if not r2.fail else 1


def run_test():
    r = run_check()
    print("Sante des prerequis :")
    r.affiche()
    if r.fail:
        print("Prerequis en echec : tests fonctionnels non lances.")
        return 1
    print("Lancement des tests fonctionnels (scaffolding E2E) :")
    script = KIT / "tests" / "e2e.sh"
    if not script.exists():
        print(f"  [warn] {script.name} absent : la couche methodologique est en cours de production.")
        return 0
    return subprocess.run([str(script)]).returncode


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
