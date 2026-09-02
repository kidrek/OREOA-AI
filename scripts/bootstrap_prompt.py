#!/usr/bin/env python3
"""bootstrap_prompt.py - genere le message initial de session de l'agent.

Usage :
  python3 scripts/bootstrap_prompt.py [--profil online|airgap]

Etat reel determine (gate leger) :
  - image oreoa-ai-tools:<tag> presente ? (docker image inspect, config/tools.yaml)

Sortie : le message initial (texte) a transmettre a l'agent. Les tests
d'outils ne sont pas executes ici : l'agent les lance lui-meme en debut de
session (doctor check + test) - apres connexion au LLM.
"""
import argparse
import subprocess
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("Erreur : module pyyaml requis.", file=sys.stderr)
    sys.exit(1)

KIT = Path(__file__).resolve().parent.parent


def image_presente(ref):
    out = subprocess.run(["docker", "image", "inspect", ref],
                         capture_output=True, text=True, timeout=30)
    return out.returncode == 0


PROMPT_DEPLOIEMENT = """Session OREOA-AI - kit non provisionne (image conteneur absente).

1. Lis MEMORY.md (regles d'usage) puis skills/deploiement.md et docs/DEPLOY.md.
2. Guide l'analyste pour le deploiement - pose UNE seule question au depart :
   profil en-ligne ou air-gap ?
3. Conduis pas a pas (une action a la fois, commandes pretes a copier, retour
   verifie avant de continuer) :
   - prerequis hote (Docker, groupe docker - commandes sudo a l'analyste)
   - provisioning : lance toi-meme python3 scripts/doctor.py fix
   - qualification : lance toi-meme python3 scripts/doctor.py test - verdict en 3 lignes
   - LLM : la session fonctionne donc un modele repond ; verifier et completer
     la configuration au besoin (arbre de decision docs/DEPLOY.md section 5)
4. A la fin : passe a l'accueil - presente docs/GUIDE-UTILISATION.md et la
   commande /analyse (voir prompt d'accueil).
Sois bref et operationnel."""

PROMPT_ACCUEIL = """Session OREOA-AI - lancement.

1. Lis MEMORY.md (regles d'usage).
2. Lance toi-meme la verification de sante :
   python3 scripts/doctor.py check
   python3 scripts/doctor.py test
   Rapporte le verdict en 3 lignes maximum.
3. Routage :
   - image absente ou verdict en echec -> enchaine le guidage de deploiement
     (skills/deploiement.md + docs/DEPLOY.md) - une seule question au depart :
     profil en-ligne ou air-gap ?
   - verdict OK -> accueille l'analyste :
     * presente en quelques lignes le guide d'utilisation (docs/GUIDE-UTILISATION.md)
     * donne LA commande pour lancer une analyse de preuve :
         /analyse chemin/vers/collection
       (ou manuellement : ./create_case.sh puis import puis "conduis l'investigation")
     * mentionne le mode guidance (capture RAM, acquisition disque, live response)
     * demande son intention (nouvelle analyse, reprise d'affaire, autre)
Sois bref et operationnel."""


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--profil", choices=["online", "airgap"], default="online")
    args = parser.parse_args()

    cfg = yaml.safe_load((KIT / "config" / "tools.yaml").read_text())
    ref = f"{cfg['image']['name']}:{cfg['image']['tag']}"

    if image_presente(ref):
        print(PROMPT_ACCUEIL)
    else:
        print(PROMPT_DEPLOIEMENT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
