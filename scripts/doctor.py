#!/usr/bin/env python3
"""doctor.py - health and provisioning of the OREOA-AI kit.

Usage:
  python3 scripts/doctor.py check   # health: prerequisites, image, bundle, disk space
  python3 scripts/doctor.py fix     # provisioning: air-gap bundle or image build
  python3 scripts/doctor.py test    # functional tests: container tools + E2E
"""
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

try:
    import yaml
except ImportError:
    print("Error: pyyaml module required (pip install pyyaml).")
    sys.exit(1)

KIT = Path(__file__).resolve().parent.parent
CONFIG = KIT / "config" / "tools.yaml"
GO = 1024 ** 3

# (chemin relatif, requis, type)
STRUCTURE = [
    ("AGENTS.md", True, "fichier"),
    ("README.md", True, "fichier"),
    ("README.fr.md", True, "fichier"),
    ("MEMORY.md", True, "fichier"),
    ("LICENSE", True, "fichier"),
    ("install.sh", True, "fichier"),
    ("Dockerfile", True, "fichier"),
    ("opencode.json", True, "fichier"),
    (".claude/settings.json", True, "fichier"),
    (".opencode/commands", True, "dossier"),
    (".opencode/commands/analyse.md", True, "fichier"),
    (".opencode/commands/case.md", True, "fichier"),
    (".opencode/commands/lang.md", True, "fichier"),
    (".opencode/commands/deploy.md", True, "fichier"),
    ("config/tools.yaml", True, "fichier"),
    ("config/suricata/regles-kit.rules", True, "fichier"),
    ("config/suricata/disable.conf", True, "fichier"),
    ("config/suricata/threshold.config", True, "fichier"),
    ("scripts/ingest.py", True, "fichier"),
    ("scripts/fetch_referentiels.py", True, "fichier"),
    ("scripts/referentiels.py", True, "fichier"),
    ("scripts/disk.py", True, "fichier"),
    ("docs/NOTICE", True, "fichier"),
    ("docs/USER-GUIDE.md", True, "fichier"),
    ("docs/USER-GUIDE.fr.md", True, "fichier"),
    ("docs/DEPLOY.md", True, "fichier"),
    ("docs/DEPLOY.fr.md", True, "fichier"),
    ("docs/QUICK-START.md", True, "fichier"),
    ("docs/QUICK-START.fr.md", True, "fichier"),
    ("docs/REFERENTIALS.md", True, "fichier"),
    ("docs/REFERENTIALS.fr.md", True, "fichier"),
    ("referentiels-kit", True, "dossier"),
    ("referentiels-kit/artifacts", True, "dossier"),
    ("referentiels-kit/dfiq", True, "dossier"),
    ("skills", True, "dossier"),
    ("methodologie", True, "dossier"),
    ("catalogue", True, "dossier"),
    ("catalogue/reseau.md", True, "fichier"),
    ("catalogue/disque.md", True, "fichier"),
    ("catalogue/artefacts.md", True, "fichier"),
    ("catalogue/dfiq.md", True, "fichier"),
    ("connaissances", True, "dossier"),
    ("connaissances/reseau", True, "dossier"),
    ("connaissances/disque", True, "dossier"),
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
        return True, f"daemon active (v{out.stdout.strip()})"
    if "permission denied" in out.stderr.lower():
        return False, ("daemon active but access denied: user outside the docker group "
                       "(fix with: sudo usermod -aG docker $USER, then re-login)")
    if out.returncode == 127:
        return False, "docker missing"
    return False, "daemon unreachable"


def image_ref(cfg):
    return f"{cfg['image']['name']}:{cfg['image']['tag']}"


def taille_lisible(octets):
    """Human-readable size (kept unit labels bilingual-safe)."""
    if octets >= GO:
        return f"{octets / GO:.1f} Go"
    return f"{octets / (1024 * 1024):.0f} Mo"


def image_info(ref):
    """(image id, size) or (None, None)."""
    out = docker_cmd(["image", "inspect", ref, "--format", "{{.Id}}|{{.Size}}"])
    if out.returncode == 0:
        identifiant, taille = out.stdout.strip().split("|")
        return identifiant, int(taille)
    return None, None


def traces_referentiels(ref):
    """Upstream referential versions baked in-image (None if missing)."""
    out = docker_cmd(["run", "--rm", "--network", "none", ref,
                      "sh", "-c", "cat /referentiels/traces/*.txt 2>/dev/null"], timeout=60)
    if out.returncode != 0 or not out.stdout.strip():
        return None
    versions, courant = {}, None
    for ligne in out.stdout.splitlines():
        ligne = ligne.strip()
        if ligne.startswith("# Trace referentiel"):
            courant = ligne.replace("# Trace referentiel", "").strip()
            versions[courant] = {}
        elif courant and ":" in ligne:
            cle, valeur = ligne.split(":", 1)
            versions[courant][cle.strip()] = valeur.strip()
    return versions or None


def version_courte(info):
    """Short display version of a referential trace."""
    return info.get("release") or str(info.get("commit", ""))[:12] or "?"


def espace_libre(chemin):
    """Free bytes on the path filesystem (None if unmeasurable)."""
    out = subprocess.run(["df", "-B1", "--output=avail", str(chemin)],
                         capture_output=True, text=True)
    lignes = [l for l in out.stdout.strip().splitlines() if l.strip()]
    try:
        return int(lignes[-1])
    except (IndexError, ValueError):
        return None


def docker_root_dir():
    """Docker storage root (default /var/lib/docker)."""
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
            return "FAILED"
        if self.warn:
            return "WARNINGS"
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
            (r.fail if requis else r.warn).append((rel, "missing"))
            if genre == "dossier":
                r.actions_fix.append(lambda c=chemin: c.mkdir(parents=True, exist_ok=True))
    for rel in ("install.sh", "scripts/doctor.py",
                "scripts/ingest.py", "scripts/dt",
                "scripts/fetch_referentiels.py", "scripts/referentiels.py",
                "scripts/disk.py"):
        chemin = KIT / rel
        if chemin.exists() and not chemin.stat().st_mode & 0o111:
            r.warn.append((rel, "not executable"))
            r.actions_fix.append(lambda c=chemin: c.chmod(c.stat().st_mode | 0o755))

    # Synchronisation CLAUDE.md (parite Claude Code)
    agents_md = KIT / "AGENTS.md"
    claude_md = KIT / "CLAUDE.md"
    if agents_md.exists() and (not claude_md.exists()
                               or agents_md.stat().st_mtime > claude_md.stat().st_mtime):
        r.warn.append(("CLAUDE.md", "missing or out of sync with AGENTS.md"))
        r.actions_fix.append(lambda a=agents_md, c=claude_md: shutil.copy2(a, c))

    # Image
    if ok:
        identifiant, taille = image_info(ref)
        if identifiant:
            r.ok.append((f"image {ref}", f"present ({taille_lisible(taille)})"))
            # Referentiels amont bakes in-image (fraicheur)
            versions = traces_referentiels(ref)
            seuil_age = cfg.get("referentiels", {}).get("vieillissement_jours", 30)
            if not versions:
                r.warn.append(("upstream referentials",
                               "missing from the image - refresh with: python3 scripts/doctor.py fix"))
            else:
                for nom, info in versions.items():
                    age_txt = ""
                    try:
                        age = (datetime.now(timezone.utc)
                               - datetime.fromisoformat(info.get("date_build", ""))).days
                        age_txt = f", {age} d old"
                        if age >= seuil_age:
                            r.warn.append((f"referential {nom}",
                                           f"{version_courte(info)}{age_txt} - {seuil_age} d threshold exceeded, "
                                           "refresh: python3 scripts/doctor.py fix"))
                            continue
                    except ValueError:
                        pass
                    r.ok.append((f"referential {nom}", f"{version_courte(info)}{age_txt}"))
        else:
            r.warn.append((f"image {ref}", "missing - provision with: python3 scripts/doctor.py fix"))
            if bundle.exists():
                r.ok.append(("air-gap bundle", f"{bundle} detected (docker load possible)"))
            else:
                r.warn.append(("air-gap bundle", "absent (provisioning will use docker build)"))
            # Espace disque (information, la barriere dure est appliquee par fix)
            libre = espace_libre(docker_root_dir())
            if libre is None:
                r.warn.append(("disk space", "not measurable"))
            else:
                go_libre = libre / GO
                if libre < seuil_build:
                    r.fail.append(("disk space", f"{go_libre:.1f} Go free on {docker_root_dir()} "
                                                 f"- below build threshold ({seuil_build // GO} GB)"))
                else:
                    r.ok.append(("disk space", f"{go_libre:.1f} Go free on {docker_root_dir()}"))
    return r


def run_fix():
    """Provisioning: air-gap bundle load or always-refresh image build."""
    cfg = load_config()
    ref = image_ref(cfg)
    bundle = KIT / cfg["provisioning"]["bundle"]
    seuil_build = cfg["provisioning"]["seuil_espace_build_go"] * GO
    seuil_load = cfg["provisioning"]["seuil_espace_load_go"] * GO

    print("== Provisioning ==")
    r = run_check()
    print("State before intervention:")
    r.affiche()
    for action in r.actions_fix:
        try:
            action()
            print("  [fix] structure correction applied")
        except Exception as exc:  # noqa: BLE001
            print(f"  [error] correction failed: {exc}")

    identifiant, _ = image_info(ref)
    if identifiant:
        print(f"\nImage {ref} present: systematic rebuild "
              "(upstream referentials refresh guaranteed).")
        print("  Cache preserved: only the referentials and LABEL layers rebuild.")

    ok, detail = etat_daemon()
    if not ok:
        print(f"\nProvisioning impossible: {detail}")
        print("Nothing written. Fix then rerun: python3 scripts/doctor.py fix")
        return 1

    # Hard disk-space barrier BEFORE any write
    if bundle.exists():
        seuil = seuil_load
        mode = f"docker load of bundle {cfg['provisioning']['bundle']}"
    else:
        seuil = seuil_build
        mode = f"docker build from {cfg['image']['dockerfile']}"
    racine = docker_root_dir()
    libre = espace_libre(racine)
    if libre is None:
        print(f"\nProvisioning refused: disk space not measurable on {racine}.")
        print("Nothing written.")
        return 1
    if libre < seuil:
        print(f"\nProvisioning REFUSED (disk space barrier).")
        print(f"  Required: {seuil // GO} GB free for {mode}")
        print(f"  Available: {libre / GO:.1f} GB on {racine}")
        print("Nothing written. Free space then rerun: python3 scripts/doctor.py fix")
        return 1
    print(f"\nDisk space: {libre / GO:.1f} GB free (threshold {seuil // GO} GB respected)")

    # Provisioning
    if bundle.exists():
        print(f"Loading air-gap bundle: {bundle}")
        out = docker_cmd(["load", "-i", str(bundle)], timeout=900)
    else:
        horodatage = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        print(f"Building image from {cfg['image']['dockerfile']} "
              f"(upstream referentials refreshed at build: {horodatage})...")
        out = subprocess.run(["docker", "build", "--build-arg",
                              f"REFERENTIELS_DATE={horodatage}", "-t", ref, str(KIT)],
                             capture_output=True, text=True)
    if out.returncode != 0:
        print(f"\nProvisioning failed:")
        print((out.stderr or out.stdout)[-1500:])
        return 1

    identifiant, taille = image_info(ref)
    if not identifiant:
        print("Provisioning done but image not found (check the name in config/tools.yaml).")
        return 1
    print(f"\nImage {ref} provisioned ({taille_lisible(taille)}).")
    print(f"  digest : {identifiant}")
    versions = traces_referentiels(ref)
    if versions:
        for nom, info in versions.items():
            print(f"  referential {nom}: {version_courte(info)}")
    else:
        print("  [warn] upstream referentials missing from the image (check the Dockerfile layer)")
    print("  Recommended: record this digest and the referential versions in the "
          "journal of the case in progress.")
    return 0


def run_test():
    """Functional tests: container tools, copyright, referentials, E2E."""
    cfg = load_config()
    ref = image_ref(cfg)
    echecs = 0

    print("== Functional tests ==")
    identifiant, _ = image_info(ref)
    if not identifiant:
        print(f"  [skip] image {ref} missing: provision first (python3 scripts/doctor.py fix)")
    else:
        print(f"Container {ref} tools:")
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
            print(f"  [ok]   python libraries ({', '.join(cfg['imports'])})")
        else:
            echecs += 1
            print(f"  [fail] python libraries -- {(out.stderr or '').strip()[:70]}")

        # License compliance: copyright files embedded in the image
        fichiers = " ".join(f"/usr/share/doc/{p}/copyright"
                            for p in ("tshark", "sleuthkit", "yara", "suricata", "hashdeep", "lzip"))
        out = docker_cmd(["run", "--rm", "--network", "none", "--user", "0", ref,
                          "sh", "-c", f"for f in {fichiers}; do test -f $f || exit 1; done; echo ok"],
                         timeout=120)
        if out.returncode == 0:
            print("  [ok]   Debian package copyright files present (license compliance)")
        else:
            echecs += 1
            print("  [fail] Debian package copyright files missing")

        # Upstream referentials: baked hash integrity + corpus present
        cmd = ("test -f /referentiels/traces/artifacts.txt"
               " && test -f /referentiels/traces/dfiq.txt"
               " && cd /referentiels/artifacts && sha256sum -c MANIFEST.sha256 --quiet"
               " && cd /referentiels/dfiq && sha256sum -c MANIFEST.sha256 --quiet"
               " && n=$(find /referentiels/artifacts/data -name '*.yaml' | wc -l)"
               " && d=$(find /referentiels/dfiq/data -name '*.yaml' | wc -l)"
               " && test $n -ge 10 && test $d -ge 100"
               " && echo \"referentials integrated (artifacts=$n files, dfiq=$d files)\"")
        out = docker_cmd(["run", "--rm", "--network", "none", ref, "sh", "-c", cmd], timeout=300)
        if out.returncode == 0:
            print(f"  [ok]   upstream referentials -- {out.stdout.strip().splitlines()[-1]}")
        else:
            echecs += 1
            print(f"  [fail] upstream referentials -- {(out.stderr or out.stdout).strip()[:70]}")

    print("\nEnd-to-end test (scaffold, ingestion, manifest, evidence, container):")
    script = KIT / "tests" / "e2e.sh"
    if script.exists():
        out = subprocess.run([str(script)])
        echecs += out.returncode
    else:
        print("  [fail] tests/e2e.sh missing")
        echecs += 1

    print(f"\nTest verdict: {'FAILED' if echecs else 'OK'}")
    return 1 if echecs else 0


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "check"
    if cmd == "check":
        r = run_check()
        r.affiche()
        print(f"Verdict: {r.verdict()}")
        return 0 if not r.fail else 1
    if cmd == "fix":
        return run_fix()
    if cmd == "test":
        return run_test()
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main())
