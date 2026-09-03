---
description: Guider le deploiement du kit sur ce laptop (ou reprendre le diagnostic)
---
Guide l'analyste pour le deploiement du kit OREOA-AI.

1. Lis MEMORY.md (regles d'usage), puis skills/deploiement.md et docs/DEPLOY.md integralement
2. Determine l'etat reel du laptop : Docker, groupe docker, kit deploye, image provisionnee (doctor check), LLM connecte
3. Pose UNE seule question au depart : profil en-ligne ou air-gap ?
4. Conduis pas a pas (une action a la fois, commandes pretes a copier, sudo a l'analyste quand requis, retour verifie avant de continuer)
5. Qualification finale : python3 scripts/doctor.py test (verdict en 3 lignes) puis passe a l'accueil : presente le guide de demarrage (docs/QUICK-START.md ou .fr.md) et les commandes /case et /analyse
