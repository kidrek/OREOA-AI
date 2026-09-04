# MIGRATION - kit v2.1 -> plateforme v2

Date : 2026-09-04. Refonte totale decidee : le kit autonome v2.1 (mono-agent,
manifest + fichiers, image `oreoa-ai-tools`) laisse place a la plateforme v2
(spec v4 - `SPEC.md`). `main` a ete nettoye apres pose du tag `kit-v2.1` ;
le kit reste integrement recuperable et utilisable via ce tag et sur les
laptops deja deployes.

## Actifs migres

| Kit v2.1 (tag `kit-v2.1`) | Emplacement v2 | Destinee (work order) |
|---------------------------|----------------|------------------------|
| `connaissances/**` (FR) | `knowledge/custom/connaissances/**` | restructuration en `packs/<os>/knowledge/` et sections transverses (etapes 2-4) |
| `catalogue/*.md` (66 signaux SF + 9 chaines) | `knowledge/custom/catalogue/**` | graines des en-tetes de `hunts_catalog_seed.yaml` (etape 2) ; chaines -> regles de corroboration du scoring |
| `catalogue/artefacts.md`, `catalogue/dfiq.md` (index generes) | `knowledge/custom/catalogue/` | references ; regeneres depuis le snapshot `make update-knowledge` |
| `methodologie/**` (workflow 7 phases ISO, arbres, referentiels) | `knowledge/custom/methodologie/**` | informe `agents/analyst.md` (boucle DFIQ) et les templates de rapport |
| `referentiels-kit/**` (definitions kit-custom) | `knowledge/custom/artifacts/` (README consolide) | definitions `custom:<name>` + objets DFIQ internes `S0/F0/Q0xxx` (convention v4) |
| `tests/gen_samples.py`, `tests/samples/gen_disk.py`, `gen_browser_db.py` | `corpus/legacy_generators/` | reecrits en generateurs T0 declaratifs pilotes par `corpus/scenarios/*.yaml` |
| `tests/samples/*` (echantillons statiques : auth.log, syslog, security.jsonl, c2.pcap, clean.pcap, rules.yar, testfile.bin) | `corpus/legacy_samples/` | absorbes par le corpus T0 par scenarios |
| `docs/NOTICE` (inventaire licences image kit) | `NOTICE` (racine, note de transition) | regenere pour la stack v2 avant la premiere publication |
| `MEMORY.md` (journal de construction du kit, incidents instruits) | `docs/lessons.md` (lecons curatees) + `MEMORY.md` (nouveau journal v2) | lecons reinjectees dans les etapes du work order |

## Non migre (remplace par l'architecture v4)

| Element kit v2.1 | Remplacement v2 |
|------------------|-----------------|
| `scripts/dt` (wrapper conteneurise) | conteneurs workers compose (`worker-fast`, `worker-deep`) |
| `scripts/doctor.py` (check/fix/test) | `make doctor` (smoke test analyste) + `tests/infra/` |
| `scripts/ingest.py` (manifest + scan) | lane `fast` + `derived/manifest.json` + regles delta |
| `scripts/referentiels.py` | `mcp-knowledge` + `make update-knowledge` (snapshot pinné) |
| `scripts/fetch_referentiels.py` | `make update-knowledge` (sources pincees, `knowledge/snapshot.json`) |
| `Dockerfile` (image unique oreoa-ai-tools) | `docker_build_spec.md` + `versions.env` (images multiples) |
| `opencode.json`, `.claude/`, `.opencode/commands/` | `make runtime-config` (generation depuis `agents/` + `commands/`) |
| `skills/`, `templates/` | `agents/<role>.md`, `commands/*.md`, templates de rapport |
| `config/tools.yaml`, profils online/airgap | `versions.env`, profils compose (`local-llm`) |
| `methodologie` en contrat unique AGENTS.md mono-agent | `SPEC.md` + `agents/*.md` par role |
| `tests/e2e.sh` | `tests/` T0-T6 (pytest, corpus declaratif, fixtures enregistrees) |
| `config/suricata/` (regles reseau kit) | hunts SQL + Sigma ; suricata reste un outil worker si requis |

## Principes conserves a l'identique

1. Evidence en lecture seule, SHA256 systematique, journal append-only,
   conclusions sourcees (SPEC.md contraintes 2, 8, 9)
2. Aucun montage d'image disque (le kit l'etablissait des v2.0 - la v4 l'etend :
   Dissect direct, jamais de FUSE ni root)
3. Referentiels amont pinnés, jamais edites (le kit le faisait au build - la v4
   ajoute le snapshot versionne par session)
4. Regles de langues (knowledge FR source de verite, code EN, analyste FR)
5. Barriere d'espace disque, conteneurs sans reseau, utilisateur non root
