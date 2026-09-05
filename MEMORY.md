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
| 8 | S1.5 - update-knowledge + loader DFIQ interne + fetcher : gen_internal_dfiq.py (54 objets commites S0001/F0001-F0006/Q0001-Q0047 v1.1.0), dfiq_loader.py (parseur v1.1.0 officiel+interne, package dfiq ecarte - donnees pinniees inchargeables par lui), update_knowledge.py (14 sources + clamav one-shot par defaut, snapshot.json, run reel OK), fetcher.py complet (refus pre-reseau, ISF+provenance), mcp-knowledge dfiq_list/dfiq_get, seed monte ro mcp-evidence+knowledge ; 200/200 (138 T1 + 37 T3 + 25 T5) | termine | 2026-09-04 |
| 9 | S1.6 - corpus T0 Windows : scenarios declaratifs (win-workstation-01 couvrant 49 hunts Windows fast + clean-host-01), generateurs deterministes (Velociraptor offline-collector JSONL + KAPE Module_Output CSV + image NTFS raw v0 via conteneur one-shot corpus-ntfs + patcheur MFT sans montage), 9 mappings velociraptor + parse_velociraptor (projections EID->familles, record_id, raw_policy) + step parse branche worker (skip explicite autres kinds, refused si hash mismatch, skipped compte fait pour fast_done) ; image byte-reproductible (serial/timestamps/INDX normalises, timestomping SI 2019 vs FN 2026 plante) ; 247/247 (T1+T3 217 + T5 30, 1 skip) ; artefacts : corpus_manifest.json commite, mappings/ bake worker-fast | termine | 2026-09-05 |
| 10 | S1.7 - cloture etape 1 : seuils A3 (evaluation/thresholds.yaml + loader src/oreoa/thresholds.py + spike scripts/measure_thresholds.py en conteneur worker-fast : lane fast courante 1.56 s, parse win-workstation-01 0.49 s, DuckDB 4.7 MB ; rapport commite evaluation/measurements/2026-09-05_s1.7_spike.json) + NOTICE v2 regenere en anglais (A5, licences binaires verifyees a la source : Hayabusa AGPL-3.0, Chainsaw GPL-3.0, Zircolite LGPL-3.0, capa/FLOSS Apache-2.0, DIE MIT, OpenCode MIT) + test T1 couverture NOTICE vs snapshot.json ; 260/260 (T1+T3 231 + T5 29, 0 skip) ; PR v2->main mergee (jalon etape 1) | termine | 2026-09-05 |

## Prochaine action

**Etape 2 - jalon dur** : affaire d'exercice reelle (une semaine d'usage).
Windows end-to-end (SPEC work order 2) : fast lane complete (Sigma Hayabusa/
Zircolite/Chainsaw, YARA, ClamAV, events, hunts, rank_signals), quick parsers
KAPE MFT/USN/Amcache, manifest/delta + /ingest, `events`, 20 hunts avec tests,
`rank_signals`, mcp-evidence (search, get_raw), mcp-jobs, roles ingest+triage,
/ingest /status /triage, T2 + T4 pour ces roles, make record, make doctor,
SBOM/scan. Corpus multi-hote plante a ce moment (H-LM-001 declare deep dans
le scenario). Avant dependance : T2 consomme evaluation/thresholds.yaml
(make measure re-passe la lane fast complete et alimente le re-baseline PR).

## Decisions verrouillees

1. Refonte totale v2 (2026-09-04) : plateforme remplace le kit gele `kit-v2.1` ;
   branche `v2` = construction, PR vers main par jalon
2. Autorite = `SPEC.md` + A1-A6 - ne pas dupliquer ici
3. Officiel DFIQ / knowledge jamais bake : monte ro via `make update-knowledge`
   (hote), `knowledge/snapshot.json` ; interne Q0xxx ecrit dans le depot,
   contenu autoritaire = `dfiq_mapping.md` ; objets internes GENERES par
   `scripts/gen_internal_dfiq.py` (seed + mapping, PR only, --check anti-derive)
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
    REELLE faite en S1.5 (14/14 sources aux pins, snapshot.json commite,
    clamav one-shot par defaut)
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
14. S1.5 arbitres : contenu Q0xxx derive du seed hunts (name = titre du hunt
    primaire, parents = facettes internes sinon officielles des rows,
    facettes ATT&CK-alignees) ; ClamAV refresh PAR DEFAUT dans
    update-knowledge via conteneur one-shot (jamais freshclam sur l'hote),
    opt-out --no-clamav ; package dfiq PyPI/repo ECARTe - parseur maison
    v1.1.0 versionne contre DFIQ_COMMIT (le package ne charge pas les
    donnees pinniees, faits journalises) ; fetcher sans mount cases
    (journal = stdout + provenance)
15. S1.6 arbitres (3 points avec l'analyste) : memoire+ISF, E01, chiffrement
    (BitLocker/LUKS2), VSS et .pf binaires REPORTES au sub-step deep lane
    (le signal fast voyage dans le JSONL Velociraptor ; raw EVTX/hives sans
    consommateur avant plaso) ; build corpus = Python hote + conteneur
    one-shot pinne pour les steps NTFS (pattern ClamAV S1.5,
    NTFS3G_VERSION dans versions.env, sans montage ni privileged) ; parsers
    S1.6 = Velociraptor seul (les quick parsers KAPE MFT/USN/Amcache CSV
    sont l'etape 2) ; rows shapes Velociraptor = convention documentee dans
    corpus_gen/velociraptor.py, a confirmer sur une vraie collecte a
    l'etape 2 ; image v0 = fichiers a la racine (ntfs-3g sans mkdir),
    arborescence declarative dans MFT.csv
16. S1.6 technique : determinisme image NTFS = patcheur MFT (serial boot
    derive du scenario, SI/FN de tous les records, INDEX_ROOT + buffers
    INDX balayes au-dela de l'horizon = fin de fenetre scenario,
    $LogFile/$UsnJrnl:$J zeroes, $MFTMirr reecrit) - timestomping = SI forge
    via si_created/si_modified du scenario, FN garde les temps reels ;
    parse step : kinds non-velociraptor = SkipStep explicite, sha256
    reverifie avant parse, uploads JAMAUS extraits (l'extract etape 2 en
    est responsable) ; `skipped` compte comme fait pour fast_done ;
    mappings/ bake dans worker-fast (/oreoa/mappings + OREOA_MAPPINGS_DIR)
17. S1.7 arbitres : NOTICE en ANGLAIS (ecart assume a la regle langues -
    surface legale arbitree avec l'analyste 2026-09-05, le reste du depot
    garde ses langues) ; seuils = donnees (loader src/oreoa/thresholds.py,
    cles requises des 4 seuils SPEC, valeurs > 0, additives par PR) ; spike
    = mesure en conteneur worker-fast reel (redis ACL + RQ burst, cas
    jetable, rapport JSON evaluation/local/ gitignore, copie commitee dans
    evaluation/measurements/) ; le corpus T0 (51 Ko) ne calibre PAS les
    seuils 10-min/20-min/1-GB - valeurs SPEC conservees, calibration reelle
    a T2 (etape 2) ; NOTICE verifie aux sources (API GitHub) : Hayabusa
    AGPL-3.0, Chainsaw GPL-3.0, Zircolite LGPL-3.0-or-later, capa/FLOSS
    Apache-2.0, DIE MIT, OpenCode MIT, Claude Code proprietaire (profil
    optionnel, non construit), Redis 8 tri-licence AGPL-3.0 option retenue ;
    test T1 NOTICE = chaque source de snapshot.json a une entree + licence
    (custom -> pointeur upstream) + check redistribution Elastic EL2.0 +
    section VSL ; compteur T5 corrige (29 tests, le 30+1 de S1.6 = erreur de
    saisie, suite inchangee depuis 978df48)

## Limites connues

- A creer au fil du work order : `allowlist.yaml`,
  `prompt_injection_patterns.yaml`, `crosswalk/` ; approches DFIQ internes
  vides a S1.5 (A6 : set complet avec mcp-knowledge a l'etape 3 ; navigation
  question->hunt deja derivable du seed)
- Seuils A3 : valeurs SPEC provisoires pour triage/E01/duckdb (le corpus T0
  51 Ko ne calibre pas 10-min/20-min/1-GB) - T2 (etape 2) mesure la lane
  fast complete et re-baseline par PR ; SBOM/scan syft-grype = etape 2
- `velociraptor_artifacts` : pas de pin versions.env (reference only) -
  a pinner quand les mappings velociraptor en ont besoin (etape 2)
- Corpus T0 : memoire+ISF, E01, chiffrement, VSS et .pf binaires reportes au
  sub-step deep lane (decision 15) ; rows shapes Velociraptor synthetiques a
  confronter a une vraie collecte (etape 2) ; image v0 sans arborescence
  (fichiers a la racine, arborecence declarative dans MFT.csv)
- `--nsrl` refuse jusqu'au pin NIST (arbitrage architecte requis) ;
  `--full-symbols` exige les sha256 VOL_SYMBOLS_* (vides aujourd'hui)
- Fiches knowledge migrees (kit v2.1 : `dt`, `doctor`, manifest) - relecture
  a la restructuration en packs OS (etapes 2-4)
- Groupe docker : effectif a l'ouverture d'une nouvelle session (lessons #10)
- `steps` du manifest : cles libres - liste fermee a l'implementation (S2)
- `events` : table prete en v1, rebuild incremental avec les mappings (etape 2)
- Etapes pipeline = squelette ("step 2+" dans le manifest) ; hunt_run/
  prevalence/baseline_check/pivot/sigma_hits/coverage absents de mcp-evidence
  (hunt_list lit deja le seed v0.3)
- Deps host tests : mcp 2.1.1 + redis 8.1.0 + pip-tools en pip --user
  --break-system-packages (precedent duckdb/pyarrow sur ce host)
