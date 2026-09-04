# MEMORY.md - Memoire de construction de la plateforme OREOA-AI v2

Fichier d'etat : lu en debut de session, mis a jour a la fin de chaque etape. Il
permet de reprendre le travail a l'identique apres une interruption, un changement
de session ou un changement de modele d'agent.

## Regles d'usage

1. **Debut de session** : lire `SPEC.md` (reference autoritaire) puis ce fichier
   integralement. Reprendre a la section "Prochaine action".
2. **Fin de chaque etape** : mettre a jour ce fichier (table, prochaine action,
   journal append-only) AVANT de passer a l'etape suivante.
3. **Format** : la table d'etat est la source de verite. Le journal est
   append-only, horodate.
4. **Fenetre de contexte** : aux frontieres d'etapes uniquement - mise a jour de
   ce fichier puis handover propre, jamais au milieu d'une etape non journalisee.

## Identite du projet

- Nom : OREOA-AI - plateforme v2 (spec v4 = `SPEC.md`, document fondateur)
- Depot : `kidrek/OREOA-AI` - branche de construction `v2`, PR vers `main` par
  jalon qualifie ; `main` = dernier jalon vert (transition README en attendant)
- Kit precedent : tag `kit-v2.1` (gele, qualifie, utilisable, plus maintenu)
- Licence : AGPL-3.0 (`LICENSE`, `NOTICE` - NOTICE a regenerer pour la stack v2)

## Etat de la construction

| # | Etape | Statut | Date |
|---|-------|--------|------|
| 1 | Phase A - tag `kit-v2.1` pose et pousse, main nettoye (legacy supprime, README transition EN/FR, NOTICE racine, .gitignore/.dockerignore stack v2), commit 2871173 pousse | termine | 2026-09-04 |
| 2 | Phase A - branche `v2` : `SPEC.md` (spec v4 verbatim), `AGENTS.md` (contrat de session), `MIGRATION.md` (mapping complet) | termine | 2026-09-04 |
| 3 | Phase A - migration des actifs : `knowledge/custom/{connaissances,catalogue,methodologie,artifacts}`, `corpus/legacy_{generators,samples}`, `hunts_catalog_seed.yaml` (stub v0.1), `docs/lessons.md` | termine | 2026-09-04 |
| 4 | Phase A - fiches vault mises a jour (Projet, Fiche ressource, _System/MEMORY.md) | termine | 2026-09-04 |

## Prochaine action

**Work order etape 1 - Squelette** (SPEC.md "Work order") : compose (agent+runtime,
proxy, redis, workers, mcp-*), modeles Pydantic, schema DuckDB + migrations + vues
de tiers de stockage, `agents/`, `commands/`, `make runtime-config`,
`make update-knowledge` (sources pinnees, `knowledge/snapshot.json`, DFIQ officiel
+ interne), `/case`, generateurs corpus T0 Windows + T1 + T5.

**Avant l'etape 1, trancher les points de spec ouverts (revue 2026-09-04)** :

1. `journal.md` : la spec dit "append-only + rewritten Current state block" -
   contradiction a arbitrer (proposition : etat courant dans `state/` seul,
   journal strictement append-only)
2. Matrice d'ecriture explicite : 5 surfaces d'etat (`case.yaml`, `journal.md`,
   `state/`, `manifest.json`, DuckDB), 8 acteurs (5 roles + workers fast/deep +
   commandes) - un tableau "qui ecrit quoi" a ajouter a la spec
3. Perimetre formats non arbitre : VSS, LVM/RAID, chiffrement (BitLocker/LUKS),
   AFF4 - couverts ou ecarts documentes (Dissect couvre une partie, AFF4 a
   confirmer au smoke test)
4. Symboles Volatility 3 (pack ISF offline) absents des sources pinnees -
   a ajouter a `make update-knowledge` (symboles absents = ecart documente)
5. `answers.yaml` (mode EXERCICE) : interdire explicitement sa lecture par
   `mcp-evidence`/`mcp-case` (sinon triche possible au `/score`) - verifier en T4
6. Seuil d'acceptation "100 Go E01 < 20 min" : spike de mesure des le squelette,
   recalibrage sinon (un critere rate en T2 bloque chaque PR)
7. Chaine de conservation : section dediee du rapport `/report` (hashes + journal
   existent, le livrable manque)
8. `NOTICE` regeneree pour la stack v2 (Dissect, Hayabusa, Chainsaw/Zircolite,
   capa, FLOSS, ClamAV, regles Elastic/Sigma) avant premiere publication

Puis : premiere PR `v2` -> `main` au squelette qualifie (`make test` T1/T5 verts) -
cadence retenue : PR a chaque jalon qualifie.

## Decisions verrouillees

1. Refonte totale (2026-09-04) : la plateforme v2 remplace le kit autonome ;
   kit v2.1 gele sous tag `kit-v2.1`, `main` nettoye apres pose du tag
2. Branche `v2` = branche de construction ; PR `v2` -> `main` a chaque jalon
   qualifie ; jamais de suppression sur `main` hors PR
3. Nom et depot conserves : OREOA-AI, `kidrek/OREOA-AI`, licence AGPL-3.0
4. `SPEC.md` (spec v4) = document fondateur autoritaire ; `AGENTS.md` = contrat
   de session qui y renvoie ; companion files de la spec a creer au fil du work
   order, derives de la spec, jamais inventes
5. Langues (heritage kit v1.4 + regle v4) : knowledge FR = source de verite ;
   code, schemas, prompts EN ; analyste FR ; build journal FR (ce fichier)
6. Version plateforme : v2.x (v2.0 au premier jalon) ; le document de spec est
   en revision v4 (numerotation independante)
7. Catalogue de hunts : 76 en-tetes (v0.3) = objectif etape 2 ; le coeur verifie
   d'abord, la graine s'elargit apres le jalon etape 2 ; source : signaux SF migres

## Journal de construction

- 2026-09-04 -- Phase A executee et poushee : (1) tag `kit-v2.1` annote pose sur
  main (kit v2.1 = a9217f7) et pousse - kit v2.1 integrement preservé ; (2) main
  nettoye : legacy supprime (scripts, skills, templates, docs, config,
  methodologie, connaissances, catalogue, referentiels-kit, tests, Dockerfile,
  runtimes opencode/claude, MEMORY.md, install.sh), README transition EN/FR,
  NOTICE racine (inventaire image kit + note de transition), .gitignore et
  .dockerignore reecrits pour le layout v2 - commit 2871173 pousse ; (3) branche
  `v2` creee depuis main sain ; (4) `SPEC.md` persiste verbatim (en-tete
  provenance) ; `AGENTS.md` (contrat de session, autorite SPEC.md) ;
  `MIGRATION.md` (mapping actifs migres / non migres / principes conserves) ;
  (5) actifs migres : `knowledge/custom/connaissances` (FR), `catalogue` (66 SF +
  9 chaines + index generes), `methodologie`, `artifacts` (README consolide,
  conventions custom:<name> et plage interne Q0xxx), `corpus/legacy_generators`
  (gen_samples, gen_disk, gen_browser_db), `corpus/legacy_samples` (auth.log,
  syslog, security.jsonl, c2.pcap, clean.pcap, rules.yar, testfile.bin) ;
  `hunts_catalog_seed.yaml` stub v0.1 (12 hunts nommes dans la spec) ;
  `docs/lessons.md` (18 lecons du kit) ; exception .gitignore pour les pcaps
  legacy ; (6) fiches vault mises a jour

## Limites connues

- Companion files de la spec non encore crees : skeletons `case.yaml`/`journal.md`,
  `normalized_data_model.md`, `dfiq_mapping.md`, `docker_build_spec.md`,
  `knowledge/custom/dfiq/`, `knowledge/custom/allowlist.yaml`,
  `prompt_injection_patterns.yaml`, `crosswalk/` - au fil du work order
- `hunts_catalog_seed.yaml` = stub (12 en-tetes sur 76 vise) - completion a
  l'etape 2 depuis les signaux SF migres
- Les fiches knowledge migrees referencent des mecanismes du kit v2.1 (`dt`,
  `doctor`, manifest FR/EN) - relecture obligatoire a la restructuration en
  packs OS (etapes 2-4)
- Corpus legacy = echantillons statiques + generateurs ad hoc - remplacer par le
  corpus declaratif T0 par scenarios des l'etape 1
- Groupe docker : effectif uniquement a l'ouverture d'une nouvelle session
  (mecanique conservee du kit - voir docs/lessons.md #10)
