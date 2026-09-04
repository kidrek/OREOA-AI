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
- 2026-09-04 -- S1.1 - socle securise (build order 11.1 : posture avant tout
  outil forensique). Cree : `versions.env` (pins initiaux resolvus en ligne :
  python:3.12-slim-bookworm digest-pinne, node:22-bookworm-slim, opencode-ai
  1.18.27, claude-code 2.1.260, redis 8.8.2-alpine3.23, tinyproxy Debian
  1.11.1-2.1+deb12u1, tools pip dissect 3.25.1 / plaso 20260720 / volatility3
  2.28.0 / yara-python 4.5.4 / pyarrow 25.0.1 / duckdb 1.5.5 / rq 2.12.0 /
  mcp 2.1.1, commits knowledge 13 depots en sha complet + ATT&CK v19.2 ;
  binaires forensiques laisses vides, pinnes a l'etape 2) ;
  `.env.example` ; `compose.yaml` (topologie 2 : reseau internal sans route,
  egress agent-proxy, external proxy seul ; ancre x-hardened : user 10001,
  read_only, cap_drop ALL, no-new-privileges + seccomp, pids_limit 512,
  tmpfs /tmp noexec, init, logs bornes ; services proxy, redis, agent,
  worker-fast, worker-deep (harnais RQ sans outils, outils a l'etape 2),
  mcp-evidence/knowledge/case/jobs (image mcp unique, 4 commandes),
  proxy-fetch + fetcher en profil symbol-fetch) ; `compose.local-llm.yaml`
  (override host.docker.internal, proxy desactive pour cet hote) ;
  `docker/{base,proxy,mcp,agent,worker-fast,worker-deep,fetcher,redis,
  seccomp}` (base multi-stage sans compilateurs au runtime, user oreoa
  10001, tini ; seccomp = copie pinnee du profil default moby v28.0.4,
  possede par le depot) ; Makefile (secrets, build-base, build sequencé
  base->worker-fast->reste, pins, runtime-config, up/down, shell, case-new,
  lint-compose, test, test-infra, clean-derived, image-sizes) ;
  `scripts/make_pins.py` (resolveur pins : digest images, npm, PyPI, tags
  docker hub, paquet Debian, tetes GitHub ; reecriture ligne a ligne avec
  diff + confirmation) ; `scripts/case_new.sh` (squelette basique de cas,
  la CLI /case arrive en 1.2) ; paquet `src/oreoa` v2.0.0a0 + stubs
  worker/mcp_server/fetcher (implementation 1.2-1.5) + requirements locks
  (pip-compile) ; tests : T1-lite versions.env (format, digest, shas
  knowledge), T5 #1 statique (aucun privileged/cap_add/devices/docker.sock/
  host network + ancre durcissement + reseaux, y compris profil
  symbol-fetch), T5 #5 runtime (uid 10001 sur les 9 services). Vert :
  26/26 (make lint-compose, make test, make test-infra) ; images construites
  ; smoke test redis : demarrage ACL + PING rq accepte, CONFIG/FLUSHALL
  refuses. Decisions/arbitrages : (1) base proxy = debian:bookworm-slim au
  lieu d'alpine - le paquet alpine tinyproxy 1.11.3 est compile sans le
  module Filter (directive indisponible, verifie en conteneur) ; arbitre
  avec l'analyste, note de deviation ajoutee a docker_build_spec.md 3.7,
  chemins Filter/PidFile quotes (syntaxe tinyproxy 1.11) ; (2) zircolite
  absent de PyPI - traite comme binaire release pinne a l'etape 2 (note
  versions.env) ; (3) secrets fichier = bind mounts, compose ignore `mode`
  hors swarm -> fichiers 0644 sur l'hote (repertoire secrets/ 0700 +
  gitignore), lisible par uid 10001 ; ACL redis : rq = +@all -@dangerous
  -@scripting, jeu de commandes RQ reel valide par test en 1.4 ; (4) ecart
  spec table 2 vs 3.6 : fetcher reste sur internal seul, proxy-fetch porte
  l'egress (internal+external) - 3.6 plus strict, retenu. Notes build :
  ARG multi-stage doit etre declare au-dessus du premier FROM (agent) ;
  worker-deep FROM worker-fast -> build sequencé dans le Makefile ;
  entrypoint proxy n'exec pas $@ (normal, tinyproxy en avant-plan).
  Prochaine action : S1.2 (agent + runtime-config + /case)
- 2026-09-04 -- S1.2 - agent + runtime-config + /case. Cree : `agents/` (5
  prompts de roles EN : ingest, triage, analyst, reviewer, reporter - contrats
  SPEC : ingestion sans raisonnement, triage jamais promoteur, boucle DFIQ de
  l'analyst avec bandeau/citations/revue obligatoire, reviewer adversarial
  avec la regle legitimite != explication benigne, reporter etat valide +
  chaine de conservation A4) ; `commands/` (24 fichiers canoniques : frontmatter
  YAML description/argument-hint/step + corps EN avec $ARGUMENTS ; /case et
  /help fonctionnels des maintenant, les autres declaratifs - machinerie aux
  etapes 2-5) ; `src/oreoa/case_model.py` (Pydantic schema v2 : enums fermes
  confidence/criticity/status/review, ids H#/F#/S# contraints, worked template
  du vault = autorite de validation) ; `src/oreoa/scaffold.py` (squelettes
  vides : case.yaml genere par les modeles, journal.md mirroir vide des regles
  du template, answers.yaml EXERCICE uniquement A2, perms partagees
  hote/conteneur) ; `src/oreoa/runtime_config.py` (generateur deterministe :
  opencode.json - provider openai-compatible depuis LLM_BASE_URL, 4 serveurs
  MCP remote, permissions bash deny sudo - ; agents+commands opencode et
  claude ; layouts project/global, runtimes selectables ; sources canoniques
  OREOA_AGENTS_DIR/OREOA_COMMANDS_DIR pour le conteneur) ; `src/oreoa/cli.py`
  + `__main__.py` (case new/list/switch/current, banner `Case: <id> · <TYPE> ·
  Model: <model> @ <endpoint>`, runtime-config render) ; entrypoint agent :
  rendu opencode global dans $HOME/.config/opencode au demarrage du conteneur
  + claude par cas. Tests T1 : worked template valide, enums rejetes, ids
  contraints ; scaffold (squelette, EXERCICE->answers, refus existant, perms) ;
  runtime-config (determinisme byte-identique, 5 roles + 24 commandes,
  contenu opencode.json, cablage modeles par role, corps verbatim depuis
  agents/). Vert : 43/43. Smoke conteneur : case list/banner + rendu
  runtime-config au demarrage OK. Decisions : (1) umask partage hote/
  conteneur - compose `user: 10001:${OREOA_HOST_GID}` + group_add + case dirs
  770/fichiers 660 (les 750 de la spec §8 rendaient case.yaml illisible pour
  uid 10001 ; l'analyste reste proprietaire, les autres n'ont rien) ;
  (2) runtime-config re-rendu au demarrage du conteneur depuis les mounts ro
  (spec 3.2 : editer un prompt ne demande pas de rebuild) - mais le paquet
  oredoa vit dans l'image BASE : toute modif de src/ -> make build (base
  d'abord) ; (3) /case new genere les squelettes vides depuis les modeles
  Pydantic (worked template intact comme exemple), coherence testee par
  revalidation ; (4) provider LLM : LLM_BASE_URL ajoute a .env.example +
  compose (le generator n'emet provider/model que si defini - defaut opencode
  sinon). Corrige au passage : typo oredoa->oreoa (Dockerfile user/CMD,
  entrypoint, Makefile, requirements.in, tests, journal S1.1).
  Prochaine action : S1.3 (modeles + DuckDB)
- 2026-09-04 -- S1.3 - modeles + DuckDB (work order etape 1, sous-etapes
  restantes : S1.4-S1.7). Cree : `src/oreoa/vocab.py` (vocabulaires fermes du
  modele de donnees : 17 familles, os/user_id_type/ts_desc/op/levels/
  mechanisms/event types/entry types/hives/ioc types/engine/status/entities/
  relations/raw_policy + vocab manifest kind/container/encryption/protector/
  unlock/key_type/symbol_status/step_status ; patterns id EV-###, case, hunt,
  custom:, ATT&CK, DFIQ, SHA256, GUID ; API de validation - validate_closed,
  validate_artifact (echappatoire custom:), validate_attack_id(s),
  validate_dfiq_id(s) - mode "API + fixtures" arbitre avec l'analyste : les
  sets externes sont injectes par l'appelant, la charge reelle depuis
  knowledge/ arrive avec make update-knowledge en S1.5) ; `normalize.py`
  (record_id = sha256("ev_id|artifact|source_ref", separateur non ambigu car
  ev_id et artifact ne peuvent contenir | ; path_norm : slashes avant,
  minuscules windows/macos, cas preserve linux, lettre de lecteur gardee ;
  build_summary deterministe <= 160 chars - drop detail puis coupure nette
  avec "..." ; raw_policy_for(lossless) ; utc_now naive UTC) ;
  `manifest_model.py` (Evidence/Manifest : files[] avec sha256/size, steps{}
  avec StepResult horodate, container_format obligatoire pour disk_image,
  coherence encryption/protector/unlock, symbols present->file /
  missing->identifier exact, VSS [{index, created_at, size}] ; save atomique
  tmp+os.replace ; contrat des lignes 86-100 du SPEC) ; `jobs_model.py`
  (FetchSymbolPayload - pdb_name dans KNOWN_KERNEL_PDBS {ntkrnlmp.pdb,
  ntkrpamp.pdb}, GUID regex ^[0-9A-F]{32}[0-9]+$, confirmed_by_analyst
  obligatoire ; UnlockPayload sans aucune matiere de cle - le worker lit
  state/keys/<EV-id>.yaml 0600 ; ExtractPayload avec
  safe_case_relative_path - anti zip-slip : absolu/..../lettre de
  lecteur/NUL refuses ; AddKeyPayload types password/recovery_key/bek/
  keyfile/clear ; JobEnvelope avec validation typee par job_type ;
  validate_payload passthrough pour les etapes pipeline - schemas avec leur
  implementation en S1.4/S2) ; `db.py` (migration v1 transactionnelle :
  25 types ENUM generes depuis les memes tuples que vocab.py, 11 familles
  materialisees + events + entities/relations + hosts/evidence avec colonnes
  core exactes du modele de donnees ; vues de tiers CREATE OR REPLACE sur
  read_parquet('derived/*/parquet/<f>.parquet', union_by_name=true)
  EXCLUDE raw - creees seulement si au moins un fichier existe ;
  load_evidence_family delete+insert par ev_id - idempotent - avec CAST
  explicites enum/JSON ; find_raw sur le Parquet autoritaire (bloc
  get_raw etape 2, cap 20 cote appelant) ; parquet_arrow_schema +
  write_parquet pour le corpus T0 et les tests ; ordre de colonnes
  contractuel : core(+raw_policy, raw) + famille en Parquet, core sans raw
  + famille dans DuckDB). Tests T1 nouveaux (51) : vocab (rejets, custom:,
  patterns ATT&CK/DFIQ, unicite des vocabulaires, partition
  materialise/vues), normalize (determinisme record_id, path_norm 3 OS +
  UNC, summary 160c/determinisme/troncature, raw_policy), manifest (coherences image/symboles,
  round-trip JSON, save atomique), jobs (gate confirmed_by_analyst, GUID
  malforme, zip-slip, types de cles), db (migrations idempotentes, enums
  DuckDB == tuples vocab via enum_range, aucun raw dans DuckDB, vues
  multi-evidence, round-trip Parquet->DuckDB->vues, find_raw, ordre de
  colonnes, tables de reference). Corrige en cours de dev : (1) les
  familles accounts/auth_events/detections redéclaraient des colonnes core
  (user_name/user_id/user_id_type/host) - le core du modele de donnees est
  present sur TOUTES les tables, colonnes retirees des listes famille +
  test anti-duplication ajoute ; (2) schema_version creee deux fois
  (prologue apply_migrations + migration v1) - creation retiree de la
  migration ; (3) fixture de test T1003 absente du set ATT&CK de test.
  Decisions/arbitrages : detections.score + score_factors ajoutes (section
  triage scoring) ; hosts.os = enum os_t et os_version = texte libre de
  case.yaml ; queue `fetch` ajoutee pour le profil symbol-fetch (le
  fetcher sur external ne peut pas partager fast/deep) ; raw_policy dans
  le core (SPEC storage tiers, le tableau du modele de donnees ne la
  connait pas encore - note d'arbitrage) ; deps host T1 : duckdb 1.5.5 +
  pyarrow 25.0.1 en pip --user --break-system-packages (precedent pydantic,
  user-space uniquement) ; oreoa.db lazy-importe duckdb/pyarrow (l'image
  base reste pydantic+pyyaml - mcp-evidence devra ajouter duckdb a ses
  requirements en etape 2). Vert : 94/94 T1 (43 precedents + 51
  nouveaux), 21/21 T5. Prochaine action : S1.4 (pipeline Redis/RQ + 4 MCP)
- 2026-09-04 -- S1.4 - pipeline Redis/RQ + 4 MCP (squelette, arbitre avec
  l'analyste sur 4 points). Cree : `requirements-mcp.in/.lock` (mcp 2.1.1 +
  redis 8.1.0 + duckdb 1.5.5, pip-compile) + `docker/mcp/Dockerfile`
  (installe le lock, CMD inchanges) ; `src/oreoa/worker.py` (harnais RQ :
  `python -m oreoa.worker fast|deep`, refus lane fetch - reservee au fetcher
  S1.5 ; connexion Redis via REDIS_HOST/PORT + secret ; handler run_step qui
  revalide l'enveloppe puis dispatch un registre d'etapes vide au squelette
  (note "step 2+" dans le manifest) ; ecritures manifest.json (StepResult
  horodate, save atomique) + state/phase.json derive du manifest (A1 :
  workers seuls redacteurs) sous lock flock par cas (state/.locks/case.lock,
  concurrence multi-replicas) ; notification fin de lane fast par hote =
  passage fast_done + une ligne append-only [pipeline] au journal (mecanisme
  etat, pas de pub/sub - arbitre) ; refus de run si evidence/ writable (T5
  6) ; table de timeouts par etape (spec 5b : hash 10m ... plaso 6h,
  volatility 2h) avec override packs/pipeline.yaml, result_ttl=600,
  failure_ttl=86400) ; `src/oreoa/mcp_server.py` (4 serveurs MCPServer 2.x,
  streamable HTTP :8000 stateless, TransportSecuritySettings allowed_hosts
  mcp-*.8000+localhost ; commun : resolve_case containment sous OREOA_CASES,
  wrap() delimitateurs OREOA-DATA + note untrusted, json_safe troncature
  512, cap 50/500, @guarded -> ToolError/isError jamais de traceback ;
  evidence : list_evidence, inventory, query (SELECT only, single statement,
  raw refuse, LIMIT clamp), search (ILIKE + regex), schema, detections,
  timeline, hunt_list (seed v0.3, filtre OS), get_raw (cap 20, SANS
  troncature, gate type de cas via case.yaml, resolution Parquet via
  find_raw sur connexion en memoire - le Parquet est autoritaire, pas besoin
  de case.duckdb) ; case : read_case/read_journal/read_state + mutations
  gatees upsert_hypothesis/upsert_finding/record_gap (gate confirmed_by_
  analyst, validation modeles, verification de citations - record_id non
  resoluble = refus + ligne hallucination au journal) + mark_detections_
  reviewed heberge par mcp-case (arbitre : A1 "narrow mutation", connexion
  DuckDB writable courte sans migration, transaction, uniquement
  new->reviewed) ; jobs : enqueue/extract/unlock/fetch_symbol/status/cancel/
  wait, prepare_envelope valide avant enqueue, registre Redis
  oreoa:jobs:<case_id> (case scoping, job inconnu refuse), send_stop_job_
  command pour cancel, wait borne 5-600s ; knowledge : knowledge_list/
  knowledge_read (sandbox OREOA_KNOWLEDGE) + snapshot()) ; compose (workers
  : REDIS_HOST/PORT/PASSWORD_FILE + secret + depends_on redis +
  OREOA_CASES=/cases ; mcp-evidence/case : OREOA_CASES=/cases - bug latent
  corrige ; mcp-knowledge : OREOA_KNOWLEDGE=/knowledge) ; Makefile (up
  passe --scale worker-fast=$WORKER_FAST_REPLICAS ; test = tests/unit +
  tests/mcp) ; .env.example (WORKER_FAST_REPLICAS=1) ; entrypoint worker
  simplifie (exec "$@"). jobs_model etendu : case_id obligatoire sur
  l'enveloppe (pattern + anti-traversal), queue_for_step (fast/deep/fetch,
  coherence queue/type verifiee), extract (fast, pack) separe de
  extract_unitary (deep, /extract - SPEC 107/190), ev_id enveloppe fusionne
  dans les payloads typees, ValidationError interne remontee lisiblement.
  T1 nouveaux (test_worker 11) : manifest/phase, placeholder, revalidation,
  evidence inconnue, writable refuse, notification + idempotence (pas de
  doublon), etape failed, table timeouts + override, containment case_id,
  refus fetch lane. T3 nouveaux (tests/mcp, 33) : harnais ASGI in-process
  (httpx2 ASGITransport + session_manager.run(), meme pile HTTP que
  compose), schemas/outils par serveur, SELECT-only + raw + multi-
  statements, caps 50/500 + clamp LIMIT utilisateur, troncature 512,
  delimitateurs + note, get_raw cap 20 + gate + incident/exercice autorises,
  citations non resolubles + hallucination journalisee, transitions
  detections fermees + rollback sans effet, jobs validation + case scoping,
  knowledge sandbox + snapshot. T5 nouveaux (2 smokes reels) : cycle RQ
  complet sous l'ACL rq (enqueue/burst worker/refresh/result, cancel,
  CONFIG refuse - le jeu de commandes RQ passe avec +@all -@dangerous
  -@scripting, promesse S1.1 tenue) dans l'image worker-fast avec cas
  temporaire 0777/evidence 0555 ; MCP dans l'image mcp reelle (OREOA_CASES
  verifie, outil inconnu refuse, cas lisible via mount ro). Decisions/
  arbitrages (4, valides avec l'analyste) : (1) detections.status -> mcp-case
  ; (2) concurrence fast configurable au lancement (WORKER_FAST_REPLICAS,
  --scale, 1 par defaut ; la spec 5b "2 processus dans le conteneur" ecartee
  - chaque replica porte son cap et le flock serialise les ecritures
  partagees) ; (3) get_raw autorise pour les deux types de cas, refus
  mecanique si le type n'est pas etabli ; (4) notification par etat
  (phase.json + journal). Notes techniques : connexions Redis plateforme en
  bytes (decode_responses=False - RQ stocke des payloads compresses, HGETALL
  en utf-8 cassait refresh) ; MCP 2.x : FastMCP renomme MCPServer, ToolError
  pour isError, liste_tools client = ListToolsResult (.tools) ; hosts MCP
  acceptes via allowed_hosts (le Host header mcp-evidence:8000 serait refuse
  par defaut). Corrige en cours de dev : ValidationError pydantic interne
  (ExtractPayload ev_id) remontee sur le mauvais champ de l'enveloppe ;
  finished_at non reinitialise au re-run d'une etape ; imports date/yaml
  manquants ; extract_unitary absent de TYPED_PAYLOADS (chemins non
  valides) ; double connexion DuckDB read-write/read-only dans la
  verification de citations (rollback sans transaction) - con partage.
  Vert : 140/140 T1+T3 (107 + 33), 23/23 T5 (21 + 2 smokes), images
  reconstruites (base->worker-fast->mcp). Prochaine action : S1.5
  (update-knowledge + loader DFIQ interne + fetcher)
