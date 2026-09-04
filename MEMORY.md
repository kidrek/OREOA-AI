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
| 6 | S1.3 - modeles + DuckDB : `vocab.py` (vocabulaires fermes + API validation forensic_artifacts/attack/dfiq mode API+fixtures), `normalize.py` (record_id, path_norm, summary 160c, raw_policy), `manifest_model.py` + `jobs_model.py`, `db.py` (migration v1 : 25 types enum + 11 familles materialisees + events/entities/relations + hosts/evidence ; 6 vues de tiers read_parquet union_by_name EXCLUDE raw ; load idempotent par ev_id ; find_raw ; schema Parquet) ; 94/94 T1, 21/21 T5 verts | termine | 2026-09-04 |

## Prochaine action

**S1.4 - Pipeline Redis/RQ + 4 MCP** : `worker.py` harnais RQ (queues
`fast`/`deep`/`fetch`, un job par etape avec timeout par pack, ecritures
manifest/phase par etape, completion fast -> notification) ;
`mcp_server.py` : 4 serveurs - evidence (lecture case.duckdb + resolution
Parquet, caps 50/500, troncature 512, raw uniquement via get_raw cap 20),
case (mutations gated `confirmed_by_analyst` + verification de citations,
A1), jobs (enqueue/status/cancel sur payloads `jobs_model.py`), knowledge
(scaffold lecture knowledge/ - loader complet S1.5) ; ACL redis rq validee
en reel ; tests T3 squelette (schemas, caps, refus mutation sans gate).
Puis S1.5 (update-knowledge + loader DFIQ interne), S1.6 (corpus T0
Windows), S1.7 (spike seuils A3, NOTICE stack v2 A5, `make test` T1+T5
vert, fiches vault, PR `v2`->`main`).

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
6. `record_id` = sha256 de `ev_id|artifact|source_ref` - separateur `|`
   non ambigu : ev_id (pattern `EV-###`) et artifact (vocabulaire ou
   `custom:`) ne peuvent pas en contenir
7. `raw_policy` (kept/omitted_lossless) ajoutee au core - SPEC storage
   tiers ; ordre Parquet = core(+raw_policy, raw) + colonnes famille, la
   table DuckDB = core sans raw + famille (alignement teste)
8. Set materialise = SPEC storage tiers ; `detections.score`/`score_factors`
   ajoutes (section triage scoring) ; `hosts.os` = enum, `os_version` =
   texte libre de case.yaml
9. Queue `fetch` ajoutee : le fetcher (profil symbol-fetch, reseau
   external) ne peut pas partager les queues fast/deep (internal)
10. Vocabulaires externes (FA/ATT&CK/DFIQ) = API + sets injectes (mode
    API+fixtures arbitre) ; la charge reelle arrive avec update-knowledge
    (S1.5)

## Limites connues

- A creer au fil du work order : `knowledge/custom/dfiq/`, `allowlist.yaml`,
  `prompt_injection_patterns.yaml`, `crosswalk/`
- Fiches knowledge migrees : mecanismes kit v2.1 (`dt`, `doctor`, manifest) -
  relecture a la restructuration en packs OS (etapes 2-4)
- Corpus legacy = echantillons statiques - remplacer par le corpus declaratif
  T0 des l'etape 1
- Groupe docker : effectif a l'ouverture d'une nouvelle session (lessons #10)
- `steps` du manifest : cles libres pour l'instant - liste fermee a
  l'implementation des etapes (S1.4/S2)
- `events` : table prete en v1, logique de rebuild incremental avec les
  mappings (etape 2)
- mcp-evidence (etape 2) : ajouter duckdb aux requirements de l'image mcp -
  la base n'embarque que pydantic+pyyaml, `oreoa.db` lazy-importe
  duckdb/pyarrow
- Deps host T1 : duckdb 1.5.5 + pyarrow 25.0.1 installes pip --user
  --break-system-packages (precedent pydantic sur ce host)
