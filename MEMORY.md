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
| 1 | Phase A : tag `kit-v2.1`, main nettoye, branche `v2` + SPEC/AGENTS/MIGRATION, actifs migres, fiches vault (2871173) | termine | 2026-09-04 |
| 2 | Integration reflexion v2 : SPEC revision complete, compagnons, amendements A1-A6 (b1ec23c) | termine | 2026-09-04 |
| 3 | S1.0 - memoire restructuree (MEMORY compact, docs/journal.md, AGENTS.md) | termine | 2026-09-04 |
| 4 | S1.1 - socle securise : versions.env + compose + 9 Dockerfiles + Makefile + pins ; deviation proxy debian:bookworm-slim (3.7) ; 26/26 T1/T5, redis ACL fume | termine | 2026-09-04 |
| 5 | S1.2 - agent + runtime-config + /case : 5 roles, 24 commandes, case_model/scaffold/runtime_config/CLI, perms 10001:HOST_GID 770/660 ; 43/43 verts | termine | 2026-09-04 |
| 6 | S1.3 - modeles + DuckDB : vocab/normalize/manifest_model/jobs_model, db.py migration v1 (11 familles materialisees + events + vues de tiers, load idempotent, find_raw) ; 94/94 T1, 21/21 T5 | termine | 2026-09-04 |
| 7 | S1.4 - pipeline Redis/RQ + 4 MCP : worker.py (harnais fast/deep, manifest/phase + flock, fast_done notifie, timeouts), mcp_server.py (evidence/case/jobs/knowledge streamable HTTP :8000 stateless), jobs_model etendu, requirements-mcp, compose REDIS+OREOA_CASES, T3 (33) + 2 smokes T5 reels (ACL rq validee) ; 140/140 T1+T3, 23/23 T5 | termine | 2026-09-04 |

## Prochaine action

**S1.5 - update-knowledge + loader DFIQ interne + fetcher** : `scripts/update_knowledge.py`
(hote : clone/download des 13 sources pinnees versions.env -> `knowledge/upstream/`,
`knowledge/snapshot.json` {name, url, commit, fetched_at, licence} ; profil minimal
par defaut, `--full-symbols`/`--nsrl`/`--symbol <os> <id>` optionnels) ; objets DFIQ
internes `knowledge/custom/dfiq/` (plage Q0xxx, contenu autoritaire = `dfiq_mapping.md`,
meme loader que le package dfiq officiel) ; loader `mcp-knowledge` (questions/facettes
officielles + internes, is_internal flag, OS-filter par defaut, `snapshot()` branche) ;
`fetcher.py` (queue `fetch`, pdbconv, provenance json, refus URL hors pdb_name/guid
valides) ; Makefile target update-knowledge. Puis S1.6 (corpus T0 Windows), S1.7
(spike seuils A3, NOTICE stack v2 A5, `make test` T1+T3 + T5 vert, fiches vault,
PR `v2`->`main`).

## Decisions verrouillees

1. Refonte totale v2 (2026-09-04) : plateforme remplace le kit gele `kit-v2.1` ;
   branche `v2` = construction, PR vers main par jalon
2. Autorite = `SPEC.md` + A1-A6 - ne pas dupliquer ici
3. Officiel DFIQ / knowledge jamais bake : monte ro via `make update-knowledge`
   (hote), `knowledge/snapshot.json` ; interne Q0xxx ecrit dans le depot,
   contenu autoritaire = `dfiq_mapping.md`
4. Hunts v0.3 = en-tetes ; SQL + 1 test/OS a l'etape 2 ; croisement 66 SF + 9
   chaines migres <-> H-* a verifier a l'etape 2
5. Corpus T0 : memoire + VSS reportes a la sous-etape deep lane ; images disque
   = mkntfs + ntfscp + patcheur MFT, sans montage
6. `record_id` = sha256 de `ev_id|artifact|source_ref` (separateur non ambigu)
7. `raw_policy` dans le core ; ordre Parquet = core(+raw_policy, raw) + famille,
   table DuckDB = core sans raw + famille (alignement teste)
8. Set materialise = SPEC ; detections.score/score_factors ajoutes ; hosts.os
   enum, os_version texte libre
9. Queue `fetch` dediee au fetcher (profil symbol-fetch, external)
10. Vocabulaires externes (FA/ATT&CK/DFIQ) = API + sets injectes ; charge
    reelle avec update-knowledge (S1.5)
11. S1.4 arbitres : detections.status -> mcp-case (gate + DuckDB writable
    courte, new->reviewed uniquement) ; concurrence fast = `--scale
    worker-fast=$WORKER_FAST_REPLICAS` (make up, defaut 1, flock par cas) ;
    get_raw autorise incident+exercice (refus si type non etabli) ;
    notification = phase.json + journal [pipeline] (pas de pub/sub) ;
    `extract` (fast, pack) separe de `extract_unitary` (deep, /extract)
12. Redis plateforme en bytes (decode_responses=False - payloads RQ compresses)
13. MCP 2.x : MCPServer + ToolError (isError), streamable HTTP stateless :8000,
    allowed_hosts mcp-*+localhost ; resultats OREOA-DATA (note untrusted),
    cap 50/500, troncature 512, get_raw cap 20 sans troncature

## Limites connues

- A creer au fil du work order : `knowledge/custom/dfiq/`, `allowlist.yaml`,
  `prompt_injection_patterns.yaml`, `crosswalk/`
- Fiches knowledge migrees (kit v2.1 : `dt`, `doctor`, manifest) - relecture
  a la restructuration en packs OS (etapes 2-4)
- Corpus legacy = echantillons statiques - remplacer par le corpus T0 (S1.6)
- Groupe docker : effectif a l'ouverture d'une nouvelle session (lessons #10)
- `steps` du manifest : cles libres - liste fermee a l'implementation (S2)
- `events` : table prete en v1, rebuild incremental avec les mappings (etape 2)
- Etapes pipeline = squelette ("step 2+" dans le manifest) ; hunt_run/
  prevalence/baseline_check/pivot/sigma_hits/coverage absents de mcp-evidence
  (hunt_list lit deja le seed v0.3)
- Deps host tests : mcp 2.1.1 + redis 8.1.0 + pip-tools en pip --user
  --break-system-packages (precedent duckdb/pyarrow sur ce host)
