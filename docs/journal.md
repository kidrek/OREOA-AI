# Journal de construction - OREOA-AI plateforme v2

Journal append-only, horodate, en francais. Une entree par etape ou
sous-etape, append en fin d'etape (voir `MEMORY.md` pour l'etat courant et la
regle d'usage). Lecture en session : derniere entree au besoin, jamais le
fichier entier. Le detail long-form du projet vit dans le vault :
`1 PROJETS/Projet OREOA-AI.md`.

## Entrees

- 2026-09-04 -- Phase A executee et poussee : (1) tag `kit-v2.1` annote pose sur
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
- 2026-09-04 -- S1.0 - restructuration de la memoire de construction (plan
  etape 1 valide, decision : limiter le contexte lu a chaque session) :
  `MEMORY.md` reecrit en fichier d'etat compact (< 60 lignes : identite,
  table, prochaine action detaillee pour l'etape en cours, decisions
  condensees en pointeurs vers SPEC.md + A1-A6, limites actives) ;
  `docs/journal.md` cree a la racine de docs avec relocation verbatim des 2
  entrees existantes (Phase A, integration reflexion v2 - aucune perte,
  historique git + fiches vault conservent le detail long-form) ;
  `AGENTS.md` autorite #2 et regle de frontiere de contexte mises a jour
  (MEMORY = etat lu integralement ; docs/journal.md = append-only, lecture
  partielle) ; en-tete de provenance de `SPEC.md` renvoie aux deux fichiers
  (note, pas de changement normatif). Decision corpus T0 journalisee dans
  MEMORY : echantillon memoire et snapshots VSS reportes a la sous-etape deep
  lane ; images disque = mkntfs + ntfscp + patcheur MFT sans montage.
  Prochaine action : S1.1 (socle securise)
