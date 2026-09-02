# DFIR Agent Kit

Kit d'investigation numerique (DFIR) agentique, autoportant et deployable. Un agent d'intelligence artificielle lance dans le kit identifie les collections de donnees, conduit une investigation normalisee et produit un rapport d'affaire complet.

## Description

Le kit repose sur un depot git embarquant deux couches inseparables :

- **Une couche outillage** : les outils forensiques sont pinees dans une image Docker versionnee. Aucune installation de paquets sur l'hote, aucun reseau requis a l'execution, aucun root requis.
- **Une couche methodologique** : instructions d'agent, competences, methodologie, catalogues de signaux faibles, templates de livrables. Le contenu a ete concu et valide a l'avance : l'agent n'improvise pas, il applique.

Le resultat produit pour chaque affaire est un rapport complet : description de l'affaire, procedure suivie, inventaire des collections avec empreintes, description des actifs affectes, timeline, observables, mesures de containment, remediation, recommandations de securisation. Chaque conclusion est sourcee par un artefact, une collection et un hash.

## Principes

1. **Autonomie totale** - le kit ne reference aucune ressource externe : deployable en reseau isole, fonctionnel hors ligne, synchronisable par cle USB
2. **Integrite forensique** - evidence en lecture seule, SHA256 systematique, journal d'actions append-only, aucune conclusion sans source
3. **Conteneurisation** - chaque outil s'execute dans un conteneur sans reseau, volume evidence monte en lecture seule, sortie produite dans le dossier d'affaire
4. **Deux modes** - autonome (traitement de bout en bout) et guidance (accompagnement pas a pas d'un analyste)
5. **Sante de l'outillage** - commande `doctor` : verification de sante, reparation, tests fonctionnels sur echantillons embarques
6. **Tranche verticale** - methode entrainee sur un perimetre cible et fini (affaire Windows et logique Linux), puis elargissement progressif par couches

## Prerequis

| Composant | Version | Usage |
|-----------|---------|-------|
| git | >= 2.30 | depot, partage, sync |
| Docker | >= 24, daemon actif | build image, execution des outils |
| bash | >= 4.2 | scripts |
| SHA256sum | systeme | integrite |
| Agent | OpenCode ou Claude Code | pilotage |

Acces reseau requis uniquement pour : premier `docker build`, telechargement des modeles LLM (phase `install.sh`), verification des signatures. Une fois ces elements telecharges, tout fonctionne hors ligne.

## Quick start

### 1. Bootstrap

```bash
cd "DFIR Agent Kit"
./install.sh check          # sante de l'environnement (docker, git, scripts)
./install.sh test           # tests fonctionnels de bout en bout
```

### 2. Creation d'une affaire

```bash
./create_case.sh "Incident serveur web 2026-45"        # affaire nommee
./create_case.sh --id CASE-2026-0042 "Analyse compromise"   # identifiant impose
```

Scaffold produit :

```
cases/CASE-2026-0042/
├── 00_evidence/                 # preuves - cotes non versionnes
│   ├── originals/               # preuves brutes, jamais modifiees
│   ├── exports/                 # extractions et transcodages
│   └── images/                  # images disque et memoire (E01, AFF4, raw)
├── 01_work/                     # espace de travail
│   ├── tmp/                     # montages et stockage temporaire
│   └── extracts/                # extractions travaillees
├── 02_analysis/                 # produits d'analyse
│   ├── logs/                    # journal d'actions
│   ├── timeline/                # produits de timeline
│   ├── ioc/                     # observables
│   └── report/                  # rapport en cours de redaction
├── manifest.yaml                # inventaire des collections + SHA256
└── journal.md                   # journal d'actions append-only
```

### 3. Lancement de l'agent

```bash
opencode                       # dans le dossier du kit
> Importe la collection dans cases/CASE-2026-0042/00_evidence/originals/
> Conduis l'investigation de l'affaire et produis le rapport
```

L'agent lit `AGENTS.md`, charge les competences, execute la methodologie, journalise chaque action, et redige le rapport a partir des templates.

## Architecture

Deux couches dans un depot unique :

- **Couche hote (ligere)** : scanner, verificateur d'integrite, scripts de simulation - fonctionne sur tout laptop equipe de Docker
- **Couche outils (lourde)** : image Docker `dfir-tools` contenant la chaine d'outils forensiques (log2timeline/plaso, volatility3, The Sleuth Kit, tshark, ruleset Sigma) - construite par `install.sh`, executables uniquement via les wrappers

Regles d'installation (profils en-ligne et air-gap) :

| Profil | Comportement |
|--------|--------------|
| `online` | telecharge les modeles LLM et les outils depuis les sources officielles, avec verification de sante (`doctor`) |
| `airgap` | charge le bundle `tools/` depuis un media amovible, sans aucun acces reseau |

Deploiement multi-laptops :

1. Repo git partage (serveur interne ou remote chifffre)
2. Image `dfir-tools` versionnee et partagee (registre interne ou `docker save/load` sur USB)
3. Modeles LLM telecharges par `install.sh` vers un cache partagé (Ollama, vLLM)
4. Echange de dossiers d'affaire par depot git (metadonnees) + media amovible (evidence)

## Workflow en 7 phases

| Phase | Competence | Produit |
|-------|-----------|---------|
| 0. Import | `ingestion` | collections scannees, SHA256, manifest.yaml |
| 1. Reception/triage | `triage` | type d'affaire, collection principale, collections secondaires |
| 2. Analyse initiale | `analyse` | actifs affectes, chronologie initiale |
| 3. Correlation | `analyse` | timeline consolidee, compte rendu |
| 4. Investiguer | `analyse` | resume d'investigation |
| 5. Observer | `analyse` | tableau d'observables |
| 6. Reporting | `reporting` | rapport final : full, executive, technique |

Progression par tranches verticales (perimetre elargi a chaque itération).

### Catalogue des signaux faibles

Format de chaque fiche catalogue :

```
ID:            SF-WIN-001
Nom:           Lateral movement - PsExec
Plateforme:    windows
Severite:       haute
Confiance:      elevée
Type:           detection
Artefact:       evenement 7045 + 4688, Security.evtx
Collections:    logs/windows/security.evtx
Regles:         sigma/lateral_movement_psexec.yml
Correlation:    SF-WIN-012, SF-WIN-034
Faux positifs:   admin legitime, deployment planifie
Sources:        [[DFIR -- Windows]] §lateral movement
```

Categories couvertes en v1 : Windows (evenementiel Security + Sysmon, persistent, lateral movement, credential access) ; Linux (auth, syslog, wtmp/btmp, cron, ssh) ; correlation multi-signaux (chaine de compromise, regles d'assemblage).

## Securite et garde-fous

| Regle | Application |
|-------|-------------|
| Evidence lecture seule | volumes `00_evidence/originals/` montes `:ro` dans les conteneurs |
| Integrite | SHA256 sur chaque collection, verification avant traitement, journal des ecarts |
| Journal d'actions | `journal.md` append-only, chaque action sourcee |
| Pas de reseau | conteneurs `--network none` sauf profils explicites |
| Tracabilite | toute conclusion cite collection + artefact + hash |

## Perimetre v1

| Module | Etat |
|--------|------|
| Scanner de collections (detection de type, hashage, manifest) | planifie |
| Verificateur d'integrite (doctor check / fix / test) | planifie |
| Simulation de preuves (generateur d'echantillons de test) | planifie |
| Chaine d'outils forensiques conteneurisee | planifie |
| Catalogue de signaux faibles | planifie |
| Competences d'agent | planifie |
| Templates de rapport | planifie |
| Deploiement multi-laptops | planifie |

## Roadmap

Les couches suivantes viennent s'ajouter au kit sans changer sa structure :

- **v1.1 Memoire volatile** : acquisition RAM (guidance), analyse volatility3, catalogues et competences dedies
- **v1.2 Reseau** : capture et analyse reseau, regles de correlation
- **v2 Disque complet** : acquisition image, montage, The Sleuth Kit, plaso
- **v2.1 Cloud et conteneurs** : journaux cloud, artefacts d'orchestrateurs
- **v2.2 Navigateurs** : historiques, caches, sessions

## Etat de l'outillage

Le kit suit son propre etat de sante via `doctor` :

```bash
./scripts/doctor.py check     # sante : prerequis, scripts, permissions
./scripts/doctor.py fix       # reparation des problemes corretables
./scripts/doctor.py test      # tests fonctionnels sur echantillons embarques
```

---

Projet de recherche et d'outillage interne - kit autoportant concu pour investigation numerique sur laptops d'investigation, en reseau ou en air-gap.
