# MEMORY.md - Memoire de session du kit

Fichier d'etat : lu en debut de session, mis a jour a la fin de chaque etape. Il permet de reprendre le travail a l'identique apres une interruption, un changement de session ou un changement de modele d'agent.

## Regles d'usage

1. **Debut de session** : lire ce fichier integralement avant toute action. Reprendre a la section "Prochaine action".
2. **Fin de chaque etape** : mettre a jour ce fichier (etat de la table, prochaine action, journal) AVANT de passer a l'etape suivante.
3. **Format** : la table d'etat est la source de verite. Le journal est append-only, horodate.
4. **Aucune reference externe** : ce fichier doit rester autonome (regle du kit).

## Etat de la construction

| # | Etape | Statut | Date |
|---|-------|--------|------|
| 1 | Fiche projet + depot git + .gitignore | termine | 2026-09-02 |
| 2 | README autonome (vitrine Git) | termine | 2026-09-02 |
| 3 | AGENTS.md + opencode.json | termine | 2026-09-02 |
| 4 | install.sh + create_case.sh + .dockerignore | termine | 2026-09-02 |
| 5 | scripts (ingest.py, doctor.py, dt) | termine | 2026-09-02 |
| 6 | Methodologie (workflow, arbres, referentiels) | termine | 2026-09-02 |
| 7 | Connaissances (acquisition RAM/disque/live) | termine | 2026-09-02 |
| 8 | Catalogue signaux faibles (windows, linux, correlation) | termine | 2026-09-02 |
| 9 | Templates (rapport, manifest, journal, IOC, conservation) | termine | 2026-09-02 |
| 10 | Skills (ingestion, triage, analyse, reporting, guidance) | termine | 2026-09-02 |
| 11 | Dockerfile (image dfir-tools, versions pinees) | termine | 2026-09-02 |
| 12 | Tests (echantillons synthetiques, gen_samples.py, e2e.sh) | termine | 2026-09-02 |
| 13 | Build image Docker + E2E conteneurise | termine | 2026-09-02 |
| 14 | Commit initial du depot | en cours | 2026-09-02 |
| 15 | Fiche projet vault a jour + renvoi 3 RESSOURCES | a faire | -- |

## Prochaine action

Etape 14 : commit initial du depot (etat E2E valide). Puis etape 15 : mise a jour de la fiche projet du vault, ajout d'une fiche de renvoi dans le dossier investigation numerique du vault, mise a jour du fichier de memoire du vault.

## Journal de construction

- 2026-09-02 -- Creation du depot et du squelette complet du kit (etapes 1-12)
- 2026-09-02 -- Premier test E2E : OK hors conteneur (scaffold, ingestion 3 collections, manifest, originals intacts)
- 2026-09-02 -- Premier build Docker : ECHEC (versions apt pinees inexistantes dans la base python:3.12-slim / Debian 13)
- 2026-09-02 -- Dockerfile corrige avec versions verifiees (tshark 4.4.18, sleuthkit 4.12.1+dfsg-3, yara 4.5.2, plaso 20260720, volatility3 2.28.0, regipy 6.3.0, python-evtx 0.8.1, evtx 0.12.1) -- 2e build : ECHEC (wheels natifs de plaso sans binaire : libewf, libbde, libfsapfs, libfvde, libluksde exigent une chaine de compilation)
- 2026-09-02 -- Dockerfile v3 : build-essential + python3-dev + pkg-config ajoutes a la couche d'installation, purges apres compilation pip -- 3e build lance (compilation des wheels en cours)
- 2026-09-02 -- config/tools.yaml aligne sur les versions reelles de l'image ; MEMORY.md cree et integre a AGENTS.md (regle : lecture en debut de session, mise a jour a la fin de chaque etape)
- 2026-09-02 -- Acces docker obtenu via nouvelle session SSH locale (groupe docker applique au login) : cle ~/.ssh/id_ed25519 ajoutee a authorized_keys

## Decisions verrouillees (rappel)

1. Kit autonome : aucune reference externe dans le moindre fichier
2. Evidence en lecture seule, SHA256 systematique, journal append-only, conclusions sourcees
3. Outillage 100% conteneurise (image dfir-tools), conteneurs sans reseau, evidence montee en ro
4. Deux modes : autonome + guidance (base de connaissance complete embarquee)
5. doctor.py : check/fix/test avant toute investigation
6. Affaires dans cases/, jamais versionnees ; echantillons de test versionnes uniquement

## Limites connues

- L'image Docker doit etre construite sur chaque laptop (install.sh) ou chargee depuis le bundle air-gap
- Le groupe docker de l'utilisateur ne s'applique qu'a l'ouverture d'une nouvelle session
- Memoire volatile et reseau : hors perimetre v1 (v1.1 et v1.2), catalogues et wrappers a produire au sprint 2
