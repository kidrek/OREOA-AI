# MEMORY.md - Etat de construction de la plateforme OREOA-AI v2

Fichier d'etat compact : lu integralement en debut de session, repris a
"Prochaine action". Le journal detaille vit dans `docs/journal.md`
(append-only : une entree horodatee par etape, lecture partielle - derniere
entree au besoin). Regle intacte : une etape non journalisee est une etape
perdue - mise a jour de ce fichier + append du journal AVANT l'etape suivante.

## Identite

- Plateforme d'agent DFIR conteneurisee - autorite : `SPEC.md` (spec v4,
  revision complete) + amendements normatifs A1-A6 ; compagnons integres :
  `normalized_data_model.md`, `docker_build_spec.md`, `hunts_catalog_seed.yaml`
  (v0.3, 76 en-tetes), `dfiq_mapping.md`, `templates/case/`
- Depot `kidrek/OREOA-AI` - construction sur branche `v2`, PR vers `main` par
  jalon qualifie ; kit v2.1 gele sous tag `kit-v2.1` ; licence AGPL-3.0
- Langues : code/schemas/prompts EN ; journal de build FR ; knowledge FR
- Version plateforme v2.x ; spec en revision v4 (numerotation independante)

## Etat de la construction

| # | Etape | Statut | Date |
|---|-------|--------|------|
| 1 | Phase A : tag `kit-v2.1`, main nettoye (2871173), branche `v2` + SPEC/AGENTS/MIGRATION, migration actifs, fiches vault | termine | 2026-09-04 |
| 2 | Integration reflexion v2 : SPEC revision complete, compagnons, amendements A1-A6 (b1ec23c) | termine | 2026-09-04 |
| 3 | S1.0 - memoire restructuree : `MEMORY.md` compact, `docs/journal.md` (relocation verbatim), AGENTS.md + en-tete SPEC mis a jour | termine | 2026-09-04 |
| 4 | S1.1 - socle securise : versions.env + compose + docker/{base,proxy,mcp,agent,worker-fast,worker-deep,fetcher,redis,seccomp} + Makefile + pins resolvus ; T5 #1/#5 verts (26/26), images construites, redis ACL fume ; deviation proxy = debian:bookworm-slim (alpine sans module Filter), notee en docker_build_spec 3.7 | termine | 2026-09-04 |
| 5 | S1.2 - agent + runtime-config + /case : agents/ (5 roles), commands/ (24), case_model + scaffold + runtime_config + CLI, entrypoint agent ; 43/43 verts, smoke conteneur OK ; perms partagees hote/conteneur (user 10001:HOST_GID, 770/660) | termine | 2026-09-04 |

## Prochaine action

**S1.3 - Modeles + DuckDB** : `src/oreoa` Pydantic (manifest evidence + job
payloads, enums vocabulaires `forensic_artifacts`/`attack`/`dfiq`,
`record_id = sha256(ev_id|artifact|source_ref)` deterministe, `path_norm`,
`summary` deterministe <= 160 chars) ; schema DuckDB + migrations +
vues de tiers (`normalized_data_model.md` exactement : core columns, 14
familles materialisees SANS `raw`, vues `read_parquet(union_by_name)` pour
familles massives, `events` materialise sans `raw`, `hosts`/`evidence`,
`schema_version`, regle `lossless` obligatoire par mapping). Tests T1 :
enums, record_id, path_norm, summary, migrations, round-trip lossless.

Puis S1.4 (redis/RQ + 4 MCP), S1.5 (update-knowledge + loader DFIQ
interne), S1.6 (corpus T0 Windows), S1.7 (spike seuils A3, NOTICE stack v2
A5, `make test` T1+T5 vert, fiches vault, PR `v2`->`main`).

## Decisions verrouillees

1. Refonte totale v2 (2026-09-04) : plateforme remplace le kit autonome gele
   sous `kit-v2.1` ; branche `v2` = construction, PR vers main par jalon
2. Autorite = `SPEC.md` + A1-A6 (matrice d'ecriture, answers.yaml couche score
   uniquement, seuils dans `evaluation/thresholds.yaml`, chaine de conservation
   dans /report, NOTICE a l'etape 1, sourcing DFIQ) - ne pas dupliquer ici
3. Officiel DFIQ / knowledge jamais bake : monte ro via `make update-knowledge`
   (hote), `knowledge/snapshot.json` ; interne Q0xxx (`knowledge/custom/dfiq/`)
   ecrit dans le depot, contenu autoritaire = `dfiq_mapping.md`
4. Hunts v0.3 = en-tetes ; SQL + 1 test/OS a l'etape 2 ; croisement 66 SF + 9
   chaines migres <-> H-* a verifier a l'etape 2
5. Corpus T0 (decision 2026-09-04) : echantillon memoire et snapshots VSS
   reportes a la sous-etape deep lane ; images disque = mkntfs + ntfscp +
   patcheur MFT, sans aucun montage

## Limites connues

- A creer au fil du work order : `knowledge/custom/dfiq/`, `allowlist.yaml`,
  `prompt_injection_patterns.yaml`, `crosswalk/`
- Fiches knowledge migrees : mecanismes kit v2.1 (`dt`, `doctor`, manifest) -
  relecture a la restructuration en packs OS (etapes 2-4)
- Corpus legacy = echantillons statiques - remplacer par le corpus declaratif
  T0 des l'etape 1
- Groupe docker : effectif a l'ouverture d'une nouvelle session (lessons #10)
