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
| 5 | Integration reflexion v2 : SPEC.md revision complete v4 ((g)+(h)), compagnons (hunts v0.3, normalized_data_model, docker_build_spec, dfiq_mapping, templates/case), amendements A1-A6, AGENTS.md | termine | 2026-09-04 |

## Prochaine action

**Work order etape 1 - Squelette** (SPEC.md "Work order") : compose (agent+runtime,
proxy, redis, workers, mcp-*), modeles Pydantic, schema DuckDB + migrations + vues
de tiers de stockage, `agents/`, `commands/`, `make runtime-config`,
`make update-knowledge` (sources pinnees, `knowledge/snapshot.json`, DFIQ officiel
+ objets internes), `/case` (scaffold depuis `templates/case/`), generateurs corpus
T0 Windows + T1 + T5, spike de mesure des seuils de perf (A3), NOTICE stack v2 (A5).

Les points de spec ouverts sont fermes (arbitrage 2026-09-04, amendements A1-A6
en fin de SPEC.md) : matrice d'ecriture (A1), `answers.yaml` couche score
uniquement (A2), seuils de perf dans `evaluation/thresholds.yaml` (A3), chaine de
conservation dans `/report` (A4), NOTICE (A5), sourcing DFIQ - officiel monte ro
via `make update-knowledge`, jamais bake, interne Q0xxx ecrit dans le depot (A6).
Journal : regle tranchee par le squelette `templates/case/journal.md` (bloc
"Etat courant" reecrit par `analyst`, reste append-only). Symboles Volatility :
couverts par la decision (h) de la revision complete. Formats restants a
confirmer au smoke test : LVM/RAID via dissect.volume (T2), AFF4 = ecart documente.

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
7. Catalogue de hunts : v0.3 (76 en-tetes) integre au depot le 2026-09-04
   (remplace le stub v0.1 de la Phase A, material reflexion de l'architecte) ;
   SQL + un test par OS a ecrire a l'etape 2 ; croisement avec les 66 SF + 9
   chaines migres a verifier (mapping SF <-> H-*) a l'etape 2
8. Compagnons de la spec integres au depot (2026-09-04) depuis la reflexion
   archivee ; seuls les objets DFIQ internes (`knowledge/custom/dfiq/`) restent
   a creer, contenu autoritaire = `dfiq_mapping.md` ; mode DFIQ officiel =
   monte ro depuis l'hote (`make update-knowledge`), jamais bake dans les
   images (changement deliberé vs kit v2.1) ; amendements normatifs A1-A6 en
   fin de SPEC.md, meme autorite que la spec

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
- 2026-09-04 -- Integration de la reflexion v2 (dossier `OREOA-AI.v2--reflexion`,
  archive au vault) : `SPEC.md` remplace par la revision complete de la spec v4
  (decisions (g) chiffrement/VSS userspace + (h) profil minimal connaissances /
  symboles a la demande ; en-tete de provenance mis a jour, incoherence
  "74 headers v0.2" corrigee en v0.3/76) ; compagnons integres :
  `hunts_catalog_seed.yaml` v0.3 (76 en-tetes, remplace le stub v0.1),
  `normalized_data_model.md`, `docker_build_spec.md`, `dfiq_mapping.md`,
  `templates/case/{case.yaml,journal.md}` (squelettes verbatim, exemple worked
  2026-09-INC-042) + `templates/case/README.md` ; points de spec fermes :
  journal tranche par le squelette, symboles couverts par (h), 5 amendements
  normatifs A1-A5 (matrice d'ecriture, answers.yaml couche score, seuils perf
  dans evaluation/thresholds.yaml, chaine de conservation dans /report, NOTICE
  stack v2 a l'etape 1), A6 = sourcing DFIQ (officiel monte ro via make
  update-knowledge, interne Q0xxx ecrit dans le depot) ; formats restants a
  confirmer au smoke test : LVM/RAID (T2), AFF4 (ecart documente) ; AGENTS.md
  mis a jour (compagnons existants) ; dossier reflexion deplace dans
  `4 ARCHIVES/` du vault ; prochaine action : work order etape 1 (squelette)

## Limites connues

- Objets de connaissance restant a creer : `knowledge/custom/dfiq/` (47 questions
  internes Q0xxx + 6 facettes + scenario S0001, contenu autoritaire =
  `dfiq_mapping.md`), `knowledge/custom/allowlist.yaml`,
  `prompt_injection_patterns.yaml`, `crosswalk/` - au fil du work order
- `hunts_catalog_seed.yaml` v0.3 = en-tetes uniquement (76/76) ; SQL + un test
  par OS a ecrire a l'etape 2 ; les lignes `test:` reposent sur le corpus T0
  declaratif pas encore construit
- Les fiches knowledge migrees referencent des mecanismes du kit v2.1 (`dt`,
  `doctor`, manifest FR/EN) - relecture obligatoire a la restructuration en
  packs OS (etapes 2-4)
- Corpus legacy = echantillons statiques + generateurs ad hoc - remplacer par le
  corpus declaratif T0 par scenarios des l'etape 1
- Groupe docker : effectif uniquement a l'ouverture d'une nouvelle session
  (mecanique conservee du kit - voir docs/lessons.md #10)
