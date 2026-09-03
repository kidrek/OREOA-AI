# GUIDE-UTILISATION (USER-GUIDE) - mode d'emploi de l'analyste

Version francaise. Version anglaise : [USER-GUIDE.md](USER-GUIDE.md).

Usage quotidien du kit OREOA-AI, une fois le deploiement termine. Le protocole d'installation est dans `docs/DEPLOY.md` ; ce document couvre ce que tu fais ensuite.

## 1. Le quotidien

Lance ton outil agentique directement dans le dossier du kit :

```bash
opencode        # ou claude, ou tout agent lisant AGENTS.md
```

L'agent verifie automatiquement la sante des outils (doctor check + test) et t'accueille. Au premier lancement, il affiche le guide de demarrage (`docs/QUICK-START.fr.md`). Si quelque chose manque (image, modele), il te guide pas a pas sans que tu aies rien a demander. La connexion au modele LLM est geree par ton outil agentique lui-meme.

Ce que tu peux lui demander ensuite :

- ouvrir une affaire : `/case "nom"` (creation ou reprise) - section 2
- lancer l'investigation : `/analyse` - section 2
- "Ou en est l'affaire CASE-2026-0042 ?" (ou `/case CASE-2026-0042` pour switcher)
- "Guide-moi pour capturer la RAM de la machine Y" (mode guidance, section 5)
- "Produis le resume executif de l'affaire" (formats de rapport, section 4)

## 2. Ouvrir une affaire et lancer l'investigation

**Voie normale (recommandee)** - dans l'agent :

```text
/case "Incident serveur web 2026-45"
```

L'agent scaffold l'arborescence, te demande le contexte de l'incident (non bloquant)
et te donne l'identifiant. Tu deposes ensuite tes collectes dans
`cases/<ID>/00_evidence/originals/` - l'agent demande la provenance (une ligne),
empreinte (SHA256), rattache au referentiel d'artefacts et journalise.

Puis :

```text
/analyse
```

Il lance le workflow complet (phases 1 a 6) avec une validation a chaque gate.
`/case` seul : panorama des affaires (reprendre, switcher, en creer une autre).
`/analyse <chemin>` : importer une collection encore hors de l'affaire.

**Voie langage naturel** (tout outil agentique, sans commandes personnalisees) :

```text
> Ouvre une affaire nommee "Incident serveur web 2026-45"
> J'ai depose mes collectes dans originals, importe-les (source : USB du poste 12)
> Conduis l'investigation et produis le rapport
```

Les collections importees vont dans `cases/<ID>/00_evidence/originals/` - jamais modifiees, toujours empreintees.

## 3. Suivre l'enquete

L'investigation suit les 7 phases (`methodologie/workflow.md`) :

| Phase | Ce que produit l'agent | Ton role |
|-------|------------------------|----------|
| 0. Import | manifest.yaml (types, SHA256, artefacts du referentiel) | fournir les collections |
| Ouverture | demande de contexte sur l'incident (question ouverte, non bloquante) | partager ce que tu sais : description, declarant, periode, systemes, mesures deja prises |
| 1. Triage | contexte consigne, type d'affaire, scenario DFIQ, hypotheses | valider le triage |
| 2-4. Analyse | timeline, correlations, hypotheses et questions DFIQ testees | valider a chaque gate |
| 5. Observables | tableau des IOC avec confiance | valider |
| 6. Rapport | rapport final source (contexte + questions d'investigation) | lecture et validation |

Chaque gate : l'agent s'arrete, presente sa synthese, attend ta decision. Le `journal.md` de l'affaire trace chaque action (append-only).

## 4. Recuperer le rapport

```text
cases/<ID>/02_analysis/report/rapport.md
```

Structure en 14 sections (resume executif, description avec contexte analyste et scenario DFIQ, procedure, inventaire avec artefacts, questions d'investigation, actifs, timeline, observables, hypotheses, conclusion, containment, remediation, recommandations, annexes). Chaque conclusion cite sa source (collection + artefact + hash). Formats disponibles a la demande : `full`, `executive`, `technique`. Les observables sont aussi exportables (`02_analysis/ioc/`).

## 5. Mode guidance - les actions hors portee de l'agent

Certaines actions se font sur des machines vivantes - l'agent te guide alors pas a pas (une etape a la fois, commandes pretes a copier, verification de tes retours) :

- **Capture RAM** : outil selon OS, support externe, empreinte immediate (`connaissances/acquisition/capture-ram.md`)
- **Acquisition disque** : image raw/E01, write-blocker, empreinte des deux cotes (`connaissances/disque/acquisition.md`)
- **Live response** : ordre de volatilite, commandes Windows et Linux pretes
- **Deploiement du kit** : demande `/deploy`

Les preuves ramenees sont depositees dans `00_evidence/` et l'investigation reprend en mode autonome.

### Images disque (v2.0)

Les images disque (raw, dd, E01) sont exploitees directement, sans montage :

1. deposer l'image dans `00_evidence/originals/` (ou `00_evidence/images/` pour les gros volumes) - l'ingestion la type (desambiguation `.raw` par magic bytes) et l'empreinte
2. l'agent lance d'abord la super-timeline (`log2timeline` sur l'image, partitions detectees automatiquement), puis l'extraction ciblee des chemins d'artefacts (`referentiels.py artifacts paths` + `disk.py extract`, SHA256 par fichier)
3. garder 3x la taille de la plus grande image libre avant la super-timeline (barriere kit)

Limites documentees au rapport : AFF4 en attente (consigne, non exploite), volumes composites (LVM/RAID), VSS et chiffrement hors perimetre.

### Bases navigateurs (v2.1)

Les bases de profils navigateurs (Chromium `History`/`Cookies`, Firefox
`places.sqlite`/`cookies.sqlite`, Safari `History.db`) sont exploitees en lecture seule :

1. deposer les fichiers dans `00_evidence/originals/` (conserver `-wal`/`-shm` si collecte a chaud) ou les extraire d'une image disque (`referentiels.py artifacts paths ChromiumBasedBrowsersHistoryDatabaseFile` + `disk.py extract`)
2. l'agent lance `browsers.py` (info, visits, downloads, searches, cookies en metadonnees) et fusionne les evenements WEBHIST plaso dans la timeline de l'affaire
3. les valeurs chiffrees (contenu des cookies, Login Data) ne sont jamais lues - metadonnees seules

Limites : downloads Firefox/Safari et IE legacy via plaso ; caches opaques et IndexedDB/LocalStorage hors perimetre.

## 6. Signaux faibles et referentiels

L'agent teste systematiquement les signaux du catalogue (`catalogue/windows.md`, `catalogue/linux.md`, `catalogue/memoire.md`, `catalogue/reseau.md`, `catalogue/disque.md`, `catalogue/navigateurs.md`) et les chaines de correlation (`catalogue/correlation.md`). Le rapport inclut une annexe "signaux testes" (detecte / non detecte / non applicable + evidence) - la base de la reproducibilite de l'analyse.

Deux referentiels amont sont embarques dans l'image a chaque build (details : [docs/REFERENTIALS.fr.md](REFERENTIALS.fr.md)) :

- **ForensicArtifacts** : chaque collection importee est rapprochee automatiquement des definitions de collecte standard (champ `artefacts` du manifest) - le vocabulaire des rapports est celui du referentiel
- **DFIQ** : l'investigation est structuree en scenarios/facets/questions - le rapport trace chaque question (repondue, sourcee / sans donnees / non posee)

## 7. Securite - ce qui est garanti

- `00_evidence/originals/` en lecture seule stricte (montee `:ro` dans les conteneurs)
- SHA256 de chaque collection des l'import, journal append-only
- Conteneurs sans reseau ; parsing de contenu isole de l'hote
- Aucune conclusion sans source citee

## 8. Aide-memoire

| Commande | Role |
|----------|------|
| `opencode` / `claude` | lancer ton outil agentique dans le dossier du kit (accueil et autotest automatiques) |
| `/case "<nom>"` | ouvrir une affaire (creation, contexte, depots) |
| `/case` | panorama des affaires (reprendre, switcher, creer) |
| `/analyse` | investigation complete de l'affaire courante (depots + phases 0-6) |
| `/analyse <collection>` | importer une collection externe puis investiguer |
| `/deploy` | relancer le guidage de deploiement |
| `python3 scripts/doctor.py check\|fix\|test` | sante / provisioning / qualification |
| `python3 scripts/ingest.py <affaire> --scan --provenance "source"` | importer les depots de originals/ (integrite verifiee) |
| `python3 scripts/ingest.py <affaire> <collection>` | importer une collection externe (rapprochement artefacts automatique) |
| `./scripts/dt python3 /work/scripts/referentiels.py artefacts expand <Nom>` | voir les chemins et outils d'un artefact |
| `./scripts/dt python3 /work/scripts/referentiels.py artifacts paths <Nom>` | sortie machine : chemins resolus (piping vers disk.py extract) |
| `./scripts/dt python3 /work/scripts/disk.py info 00_evidence/originals/<image>` | vue d'ensemble image disque (format, partitions, filesystems, barriere) |
| `./scripts/dt python3 /work/scripts/disk.py extract <image> --paths <paths.txt> --out 01_work/disque/extraits` | extraction ciblee avec rapport SHA256 |
| `./scripts/dt python3 /work/scripts/browsers.py info 00_evidence/originals/History` | vue d'ensemble base navigateur (kind, compteurs, periode) |
| `./scripts/dt python3 /work/scripts/browsers.py visits 00_evidence/originals/History --out 01_work/navigateurs/visits.csv` | export des visites (UTC, transitions) |
| `./scripts/dt python3 /work/scripts/referentiels.py dfiq arbre S1008` | arbre de questions d'un scenario DFIQ |
| `./install.sh check\|fix\|test` | alternative manuelle (ops/CI, hors agent) |
