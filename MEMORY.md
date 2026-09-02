# MEMORY.md - Memoire de session du kit OREOA-AI

Fichier d'etat : lu en debut de session, mis a jour a la fin de chaque etape. Il permet de reprendre le travail a l'identique apres une interruption, un changement de session ou un changement de modele d'agent.

## Regles d'usage

1. **Debut de session** : lire ce fichier integralement avant toute action. Reprendre a la section "Prochaine action".
2. **Fin de chaque etape** : mettre a jour ce fichier (etat de la table, prochaine action, journal) AVANT de passer a l'etape suivante.
3. **Format** : la table d'etat est la source de verite. Le journal est append-only, horodate.
4. **Aucune reference externe** : ce fichier doit rester autonome (regle du kit).

## Identite du projet

- Nom : OREOA-AI (branche agentique d'OREOA)
- Depot GitHub : public - a pour remote `git@github.com:kidrek/oreoa-ai.git`
- Licence : AGPL-3.0 (fichier LICENSE ; mentions tierces : docs/NOTICE)
- Image conteneur : `oreoa-ai-tools:1.0.0`

## Etat de la construction

| # | Etape | Statut | Date |
|---|-------|--------|------|
| 1 | Depot + squelette complet (etapes initiales) | termine | 2026-09-02 |
| 2 | Build image + E2E valide (premiere generation) | termine | 2026-09-02 |
| 3 | Renommage OREOA-AI (depot, image oreoa-ai-tools, titres) | termine | 2026-09-02 |
| 4 | doctor.py v2 : provisioning autonome (barriere disque, bundle, tests par outil) | termine | 2026-09-02 |
| 5 | Conformite depot public : LICENSE AGPL-3.0, NOTICE, README, sanitisation | termine | 2026-09-02 |
| 6 | Rebuild image oreoa-ai-tools + doctor test complet + E2E | termine | 2026-09-02 |
| 7 | Push GitHub kidrek/OREOA-AI (depot public) | termine | 2026-09-02 |
| 8 | Mise a jour fichiers de reference du vault associe | termine | 2026-09-02 |
| 9 | Sprint 2 - guide multi-laptops : docs/DEPLOY.md + skills/deploiement.md (guidage agent) | termine | 2026-09-02 |
| 10 | Sprint 2 - accueil agentique : agent.sh, bootstrap_prompt.py, /analyse, /deploy, GUIDE-UTILISATION, CLAUDE.md | termine | 2026-09-02 |
| 11 | Sprint 2 - memoire volatile outillee (volatility3) | termine | 2026-09-02 |
| 12 | Sprint 2 - reseau outille (tshark) + skills timeline/ioc | a faire | -- |

## Prochaine action

Etape 11 terminee : memoire volatile outillee (connaissances, catalogue SF-M, chaines C-M-01/R-04/R-05/R-06, ingestion type memoire, E2E memoire optionnel, perimetre v1.1 dans AGENTS/CLAUDE/README). Prochaine session : sprint 2 - etape 12 (reseau tshark outille + skills timeline et ioc completes). A relire en session docker active : doctor test + E2E conteneurise (etape 5bis memoire), voir journal.

## Journal de construction

- 2026-09-02 -- Creation du depot et du squelette complet du kit (methodologie, catalogue 26 signaux, 5 skills, 5 templates, scripts, tests synthetiques)
- 2026-09-02 -- Premier test E2E : OK hors conteneur (scaffold, ingestion 3 collections, manifest, originals intacts)
- 2026-09-02 -- Build Docker : deux echecs instruits (versions apt pinees inexistantes ; wheels natifs de plaso exigent une chaine de compilation) puis succes avec build-essential purge apres compilation - image validee E2E conteneurise, commit initial
- 2026-09-02 -- Le groupe docker de l'utilisateur ne s'applique qu'a l'ouverture d'une nouvelle session ; les travaux Docker s'executent via une session locale reinitialisee (mecanique documentee dans Limites connues)
- 2026-09-02 -- Renommage du projet : OREOA-AI (coherence avec le projet OREOA existant, dont c'est la branche agentique) - dossier, image oreoa-ai-tools:1.0.0, titres ; verification disponibilite : namespace GitHub libre, namespace Docker Hub libre
- 2026-09-02 -- doctor.py v2 : provisioning autonome avec barriere d'espace disque (refus avant toute ecriture si seuil insuffisant), chargement du bundle air-gap prioritaire sur le build, test unitaire de chaque outil pine, verification des fichiers copyright embarques
- 2026-09-02 -- Conformite depot public : LICENSE AGPL-3.0 (texte officiel), docs/NOTICE (licences tierces : plaso Apache-2.0, python-evtx Apache-2.0, regipy MIT, evtx MIT/Apache-2.0, yara BSD-3, volatility3 VSL v1.0 - cas special documente), README reecrit pour le parcours agent, MEMORY.md sanitaire (aucun detail d'environnement personnel)
- 2026-09-02 -- Rebuild image : instantane grace au LABEL place en fin de Dockerfile (cache apt/pip preserve) - digest 8774d5eab ; doctor test complet : 7 outils + 3 bibliotheques + copyright + E2E tous OK (corrections en cours de route : volatility3 sans --version -> importlib.metadata, modules reels regipy/evtx/Evtx, jointure d'imports)
- 2026-09-02 -- docs/licences-image.txt genere depuis le conteneur via scripts/gen_licences.sh (165 paquets inventories, reproductible apres chaque changement d'image)
- 2026-09-02 -- Push GitHub : remote git@github.com:kidrek/OREOA-AI.git (URL canonique majuscules), main = 35a5f8a verifiee par ls-remote - depot public operationnel
- 2026-09-02 -- Fichiers de reference du vault mis a jour : fiche projet renommee Projet OREOA-AI.md, fiche ressource Fiche -- OREOA-AI.md, section projet du fichier de memoire actualisee
- 2026-09-02 -- Sprint 2 (1/3) : docs/DEPLOY.md (protocole depuis OS vierge : prerequis Debian/Ubuntu, acquisition, provisioning, arbre de decision LLM - /connect pour le cloud, bloc provider pour passerelle et Ollama/vLLM en air-gap, echange d'affaires, coherence de version entre instances autonomes, checklist) + skills/deploiement.md (guidage agent : diagnostic initial, pas-a-pas avec verification des retours, qualification consignee dans le MEMORY.md de l'instance - pas de registre central, instances autonomes) + accroches (AGENTS.md, opencode.json, README, profils)
- 2026-09-02 -- Sprint 2 (2/3) : accueil agentique zero-frappe - agent.sh (preflight LLM hors agent : auth.json ou endpoint local joignable, sinon guide de connexion + proposition opencode auth login ; puis lancement avec message initial genere), scripts/bootstrap_prompt.py (gate sur image presente -> prompt deploiement ou accueil, l'agent lance lui-meme doctor check/test a l'ouverture), commandes personnalisees /analyse (investigation complete) et /deploy, docs/GUIDE-UTILISATION.md (mode d'emploi analyste), exemple provider air-gap (config globale, kit pristine), CLAUDE.md genere + synchronisation automatisee dans doctor fix, AGENTS.md : sante elevee en comportement d'accueil (autotest spontane, routage guidage/accueil, commande /analyse)
- 2026-09-02 -- Sprint 2, etape 11 (memoire volatile outillee, v1.1) : connaissances/memoire/exploitation-volatility.md (sequencement plugins Windows/Linux, execution via dt, symboles ISF et ecarts, procedure dump de test hors depot) ; catalogue/memoire.md (10 signaux SF-M-001 a SF-M-021 : processus masque, injection, hollowing, cmdline, consoles, netscan, vol de credentials, services, rootkit Linux) ; correlation.md : chaine C-M-01 + croisements R-04/R-05/R-06 ; skills/analyse.md : section exploitation memoire ; ingest.py : types memoire (.raw/.lime/.mem/.dmp) + correction casse .E01 (jamais reconnu auparavant) ; e2e.sh : etape 5bis memoire optionnelle (skip sans dump, warn si symboles requis) ; arbres-decision.md : arbre memoire ; AGENTS/CLAUDE : perimetre v1.1 ; README : etat + roadmap ; connaissances/README : organisation corrigee (memoire/, windows/, linux/). Verifie : E2E hors conteneur OK, typage 9 cas OK, syntaxes bash/python OK. Session docker inactive (groupe non effectif, sg exige un mot de passe) : doctor test + E2E conteneurise (dont 5bis) a rejouer en session docker active

## Decisions verrouillees (rappel)

1. Kit autonome : aucune reference externe dans le moindre fichier
2. Evidence en lecture seule, SHA256 systematique, journal append-only, conclusions sourcees
3. Outillage 100% conteneurise (image oreoa-ai-tools), conteneurs sans reseau, evidence montee en ro
4. Deux modes : autonome + guidance (base de connaissance complete embarquee)
5. doctor.py : check/fix/test avant toute investigation ; provisioning autonome avec barriere disque
6. Affaires dans cases/, jamais versionnees ; echantillons de test versionnes uniquement
7. Nom OREOA-AI, depot GitHub public kidrek/oreoa-ai, licence AGPL-3.0, image oreoa-ai-tools:1.0.0

## Limites connues

- L'image doit etre provisionnee sur chaque laptop (doctor fix : build ou bundle) - le LABEL du Dockerfile est place en fin de fichier pour preserver le cache des couches apt/pip entre versions
- Le groupe docker de l'utilisateur ne s'applique qu'a l'ouverture d'une nouvelle session (mecanique de reinitialisation de session requise sur les laptops)
- Les licences Debian des paquets embarques sont verifiees in-conteneur par doctor test (fichiers copyright) ; l'inventaire factuel est archive dans docs/licences-image.txt
- Memoire volatile et reseau : hors perimetre v1 (v1.1 et v1.2), catalogues et wrappers a produire au sprint 2
