# GUIDE-UTILISATION - mode d'emploi de l'analyste

Usage quotidien du kit OREOA-AI, une fois le deploiement termine. Le protocole d'installation est dans `docs/DEPLOY.md` ; ce document couvre ce que tu fais ensuite.

## 1. Le quotidien

Lance le kit :

```bash
./agent.sh
```

L'agent verifie automatiquement la connexion LLM, la sante des outils (doctor check + test), et t'accueille. Si quelque chose manque, il te guide pas a pas sans que tu aies rien a demander.

Ce que tu peux lui demander ensuite :

- lancer une analyse (section 2)
- "Ou en est l'affaire CASE-2026-0042 ?"
- "Guide-moi pour capturer la RAM de la machine Y" (mode guidance, section 5)
- "Produis le resume executif de l'affaire" (formats de rapport, section 4)

## 2. Lancer une analyse de preuve

**Voie rapide (recommandee)** - dans l'agent :

```text
/analyse chemin/vers/ta-collection
```

L'agent cree l'affaire (ou te demande son nom), importe la collection (SHA256, manifest), puis conduit les phases 1 a 6 avec une validation a chaque gate.

**Voie manuelle** :

```bash
./create_case.sh "Incident serveur web 2026-45"
python3 scripts/ingest.py cases/CASE-2026-0001 chemin/vers/collection
```

```text
> Conduis l'investigation de CASE-2026-0001 et produis le rapport
```

Les collections importees vont dans `cases/<ID>/00_evidence/originals/` - jamais modifiees, toujours empreintees.

## 3. Suivre l'enquete

L'investigation suit les 7 phases (`methodologie/workflow.md`) :

| Phase | Ce que produit l'agent | Ton role |
|-------|------------------------|----------|
| 0. Import | manifest.yaml (types, SHA256) | fournir les collections |
| 1. Triage | type d'affaire, hypotheses | valider le triage |
| 2-4. Analyse | timeline, correlations, hypotheses testees | valider a chaque gate |
| 5. Observables | tableau des IOC avec confiance | valider |
| 6. Rapport | rapport final source | lecture et validation |

Chaque gate : l'agent s'arrete, presente sa synthese, attend ta decision. Le `journal.md` de l'affaire trace chaque action (append-only).

## 4. Recuperer le rapport

```text
cases/<ID>/02_analysis/report/rapport.md
```

Structure en 13 sections (resume executif, procedure, inventaire, actifs, timeline, observables, hypotheses, conclusion, containment, remediation, recommandations, annexes). Chaque conclusion cite sa source (collection + artefact + hash). Formats disponibles a la demande : `full`, `executive`, `technique`. Les observables sont aussi exportables (`02_analysis/ioc/`).

## 5. Mode guidance - les actions hors portee de l'agent

Certaines actions se font sur des machines vivantes - l'agent te guide alors pas a pas (une etape a la fois, commandes pretes a copier, verification de tes retours) :

- **Capture RAM** : outil selon OS, support externe, empreinte immediate (`connaissances/acquisition/capture-ram.md`)
- **Acquisition disque** : image raw/E01, write-blocker, empreinte des deux cotes
- **Live response** : ordre de volatilite, commandes Windows et Linux pretes
- **Deploiement du kit** : demande `/deploy`

Les preuves ramenees sont depositees dans `00_evidence/` et l'investigation reprend en mode autonome.

## 6. Signaux faibles

L'agent teste systematiquement les signaux du catalogue (`catalogue/windows.md`, `catalogue/linux.md`, `catalogue/memoire.md`, `catalogue/reseau.md`) et les chaines de correlation (`catalogue/correlation.md`). Le rapport inclut une annexe "signaux testes" (detecte / non detecte / non applicable + evidence) - la base de la reproducibilite de l'analyse.

## 7. Securite - ce qui est garanti

- `00_evidence/originals/` en lecture seule stricte (montee `:ro` dans les conteneurs)
- SHA256 de chaque collection des l'import, journal append-only
- Conteneurs sans reseau ; parsing de contenu isole de l'hote
- Aucune conclusion sans source citee

## 8. Aide-memoire

| Commande | Role |
|----------|------|
| `./agent.sh` | lancer le kit (preflight LLM, autotest, accueil) |
| `./agent.sh --profil airgap` | variante air-gap (endpoint local) |
| `/analyse <collection>` | lancer une investigation complete |
| `/deploy` | relancer le guidage de deploiement |
| `python3 scripts/doctor.py check\|fix\|test` | sante / provisioning / qualification |
| `./create_case.sh "<nom>"` | nouvelle affaire |
| `python3 scripts/ingest.py <affaire> <collection>` | importer une collection |
| `./install.sh check\|fix\|test` | alternative manuelle (hors agent) |
