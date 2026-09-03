# OREOA-AI -- DFIR Agent Kit

Kit d'investigation numerique (DFIR) agentique, autoportant et deployable. Un agent d'intelligence artificielle lance dans le kit identifie les collections de donnees, conduit une investigation normalisee et produit un rapport d'affaire complet.

**Licence : AGPL-3.0** - usage professionnel autorise ; toute version modifiee distribuee ou offerte en service doit partager ses sources. Voir [LICENSE](LICENSE) et [docs/NOTICE](docs/NOTICE) pour les licences tierces.

## Description

Le kit repose sur un depot git embarquant deux couches inseparables :

- **Une couche outillage** : les outils forensiques sont pinnes dans une image Docker versionnee (`oreoa-ai-tools`). Aucune installation de paquets sur l'hote, aucun reseau requis a l'execution, aucun root requis.
- **Une couche methodologique** : instructions d'agent, competences, methodologie, catalogues de signaux faibles, templates de livrables. Le contenu a ete concu et valide a l'avance : l'agent n'improvise pas, il applique.

Le resultat produit pour chaque affaire est un rapport complet : description de l'affaire, procedure suivie, inventaire des collections avec empreintes, description des actifs affectes, timeline, observables, mesures de containment, remediation, recommandations de securisation. Chaque conclusion est sourcee par un artefact, une collection et un hash.

Un exemple de rendu est fourni : [docs/exemple-rapport.md](docs/exemple-rapport.md) (donnees 100% synthetiques).

## Principes

1. **Autonomie totale** - le kit ne reference aucune ressource externe : deployable en reseau isole, fonctionnel hors ligne, synchronisable par cle USB
2. **Integrite forensique** - evidence en lecture seule, SHA256 systematique, journal d'actions append-only, aucune conclusion sans source
3. **Conteneurisation** - chaque outil s'execute dans un conteneur sans reseau, evidence montee en lecture seule, sortie produite dans le dossier d'affaire
4. **Deux modes** - autonome (traitement de bout en bout) et guidance (accompagnement pas a pas d'un analyste)
5. **Sante de l'outillage** - commande `doctor` : verification de sante, provisioning autonome, tests fonctionnels par outil sur echantillons embarques
6. **Memoire de session** - `MEMORY.md` lu en debut de session et mis a jour a chaque etape : le travail reprend exactement ou il s'est arrete

## Demarrage : trois gestes, aucun script

```bash
git clone https://github.com/kidrek/OREOA-AI.git
cd OREOA-AI
opencode              # ou claude, ou tout agent lisant AGENTS.md
```

A la premiere reponse, l'agent verifie la sante du kit (doctor) et affiche le guide de
demarrage. Ensuite, trois gestes suffisent :

| Geste | Commande | Ce qui se passe |
|-------|----------|-----------------|
| 1. Ouvrir une affaire | `/case "Incident serveur web"` | l'agent cree l'arborescence, te demande le contexte de l'incident (non bloquant) et te donne l'ID |
| 2. Deposer tes collectes | copier tes fichiers dans `cases/<ID>/00_evidence/originals/` | l'agent detecte les depots, demande la provenance, empreinte (SHA256) et rattache au referentiel d'artefacts |
| 3. Lancer l'investigation | `/analyse` | workflow complet (triage, analyse, correlation, investigation, observables, rapport) avec validation a chaque etape cle |

Le rapport final est source : chaque conclusion cite sa collection, son artefact et son
empreinte. La sante du kit est verifiee a chaque session (doctor) - si quelque chose
manque (image, modele LLM), l'agent te guide pour corriger avant toute investigation.
L'alternative manuelle pour un humain ou la CI : `./install.sh check|fix|test` -
protocole complet dans [docs/DEPLOY.md](docs/DEPLOY.md).

## Prerequis

| Composant | Version | Usage |
|-----------|---------|-------|
| git | >= 2.30 | depot, partage, sync |
| Docker | >= 24, daemon actif | build image, execution des outils |
| bash | >= 4.2 | scripts |
| Python 3 | >= 3.10 + pyyaml | scripts du kit |
| Agent | OpenCode ou Claude Code | pilotage |

L' utilisateur executant les commandes docker doit etre membre du groupe `docker` (efficace a l'ouverture d'une nouvelle session).

Acces reseau requis uniquement pour : le premier `docker build`, le telechargement des modeles LLM. Une fois ces elements presents, tout fonctionne hors ligne.

## Creation d'une affaire

Tout se fait en conversation : `/case "Incident serveur web 2026-45"` (identifiant
auto-numerote) - l'agent scaffold l'arborescence, pose le contexte de l'incident, puis
detecte les depots de collectes. `/case` seul affiche le panorama des affaires
(reprendre une affaire, en ouvrir une autre). Sans commandes personnalisees (autre
outil agentique), demande-le en langage naturel : il suit la procedure documentee dans
`AGENTS.md` (section "Structure du dossier d'affaire").

Scaffold produit :

```
cases/CASE-2026-0042/
├── 00_evidence/                 # preuves - non versionnes
│   ├── originals/               # depot de l'analyste (collectes brutes) - immuables apres import
│   ├── exports/                 # extractions et transcodages empreintes
│   └── images/                  # images disque, RAM, dumps
├── 01_work/                     # espace de travail (copies de traitement)
├── 02_analysis/
│   ├── logs/                    # journal d'actions par phase
│   ├── timeline/                # timeline consolidee
│   ├── ioc/                     # observables
│   └── report/                  # rapport en cours de redaction
├── manifest.yaml                # inventaire des collections + SHA256 + contexte
└── journal.md                   # journal d'actions append-only
```

## Lancement de l'agent

```bash
opencode                        # dans le dossier du kit
> /case "Incident serveur web"
> (deposer les collectes dans cases/CASE-2026-0042/00_evidence/originals/)
> /analyse
```

L'agent lit `AGENTS.md`, charge les competences, execute la methodologie, journalise
chaque action et redige le rapport a partir des templates. La connexion au modele LLM
est geree par ton outil agentique (opencode et Claude Code ont leur propre flux
d'authentification) - le guide de configuration avancee (provider, air-gap) est dans
[docs/DEPLOY.md](docs/DEPLOY.md) section 5.

## Architecture

Deux couches dans un depot unique :

- **Couche hote (legere)** : scanner, verificateur d'integrite, wrappers - fonctionne sur tout laptop equipe de Docker
- **Couche outils (conteneurisee)** : image `oreoa-ai-tools:1.1.0` - plaso (log2timeline, psort), volatility3, The Sleuth Kit (fls, icat), tshark, suricata (ET Open trie + regles kit), yara, regipy, evtx, bibliotheque artifacts - le tout pine par version, construit depuis le `Dockerfile` du kit
- **Referentiels amont bakes dans l'image a chaque build** : ForensicArtifacts (definitions de collecte, Apache-2.0) et DFIQ (scenarios/facets/questions d'investigation, Apache-2.0) - telecharges par le `Dockerfile` (ARG cache-bust, verification SHA256, traces bakees), exploitables via `scripts/referentiels.py` (voir [docs/REFERENTIELS.md](docs/REFERENTIELS.md))

Regles d'execution : conteneurs sans reseau (`--network none`), `00_evidence` monte en lecture seule, sortie sous l'identite de l'analyste (pas de root), tous les appels passent par le wrapper `scripts/dt`.

Profils de deploiement :

| Profil | Comportement |
|--------|--------------|
| [online](config/profiles/online.md) | build de l'image depuis les sources officielles, LLM via endpoint compatible OpenAI |
| [air-gap](config/profiles/airgap.md) | chargement du bundle `tools/oreoa-ai-tools-1.1.0.tar.gz` (`docker load`), modele LLM local (Ollama/vLLM), aucun acces reseau |

Deploiement multi-laptops :

1. Depot git partage (serveur interne ou GitHub)
2. Image `oreoa-ai-tools` construite localement ou partagée en bundle (voir profil air-gap)
3. Modeles LLM telecharges vers un cache partage ou installes localement
4. Echange de dossiers d'affaire par depot git (metadonnees) + media amovible (evidence)

## Workflow en 7 phases

| Phase | Competence | Produit |
|-------|-----------|---------|
| 0. Import | `ingestion` | collections scannees, types, SHA256, rapprochement artefacts, manifest.yaml |
| 1. Triage | `triage` | contexte analyste, type d'affaire, scenario DFIQ, collection principale, hypotheses |
| 2. Analyse initiale | `analyse` | actifs affectes, chronologie initiale |
| 3. Correlation | `analyse` | timeline consolidee, croisements multi-collections |
| 4. Investigation | `analyse` + `investigation` | hypotheses et questions DFIQ testees, ecarts explores |
| 5. Observables | `analyse` | tableau des IOC avec niveau de confiance |
| 6. Rapport | `reporting` | rapport final : full, executive ou technique |

Le mode `guidance` couvre quant a lui les actions manuelles d'investigation : capture memoire, acquisition disque, live response - l'agent guide l'analyste etape par etape (voir [skills/guidance.md](skills/guidance.md) et [connaissances/](connaissances/)). Le dump obtenu est ensuite exploite par le kit (volatility3, v1.1).

## Catalogue des signaux faibles

Le coeur analytique du kit : pour chaque famille d'artefact, des signaux faibles formalises, recherchables et corrigeables.

Format d'une fiche (exemple) :

```text
SF-W-030 - Acces memoire de lsass
artefact     : Sysmon 10 (ProcessAccess, TargetImage lsass.exe)
logique      : GrantedAccess 0x1010 / 0x1410 / 0x1fffff par processus non systeme
attaque      : T1003.001 (LSASS Memory) - MITRE ATT&CK
severite     : critique
fiabilite    : haute
faux positifs: antivirus et EDR legitimes
```

- [catalogue/windows.md](catalogue/windows.md) - 14 signaux (persistance, execution, mouvement lateral, credentials, anti-forensique)
- [catalogue/linux.md](catalogue/linux.md) - 12 signaux (authentification, execution, persistance, anti-forensique)
- [catalogue/memoire.md](catalogue/memoire.md) - 10 signaux SF-M (processus masque, injection, reseau vivant, credentials, persistance, rootkit Linux)
- [catalogue/reseau.md](catalogue/reseau.md) - 10 signaux SF-R (beaconing, DNS C2 et exfiltration, transferts, scans, SMB lateral, TLS, alertes suricata)
- [catalogue/correlation.md](catalogue/correlation.md) - chaines d'investigation multi-signaux (C-W-01/02, C-L-01/02, C-M-01, C-R-01, correlations croisees R-01 a R-09)

Chaque signal teste en investigation est enregistre (detecte / non detecte / non applicable + evidence citee) - le rapport inclut l'annexe des signaux testes.

## Securite et garde-fous

| Regle | Application |
|-------|-------------|
| Evidence lecture seule | `00_evidence/originals/` jamais modifie, monte `:ro` dans les conteneurs |
| Integrite | SHA256 de chaque collection des l'import, verification avant traitement |
| Journal d'actions | `journal.md` append-only, chaque action sourcee |
| Pas de reseau | conteneurs `--network none`, profils air-gap sans acces |
| Tracabilite | toute conclusion cite collection + artefact + hash ; digest de l'image consigne |
| Barriere disque | provisioning refuse si espace libre insuffisant (aucune ecriture) |

## Etat v1

| Module | Etat |
|--------|------|
| Ingestion (detection de type, SHA256, rapprochement artefacts, manifest) | operationnel |
| Verificateur d'integrite (doctor check / fix / test, referentiels) | operationnel |
| Chaine d'outils conteneurisee (8 outils + 4 bibliotheques) | operationnel |
| Catalogue de signaux faibles (46 signaux + 7 chaines) | operationnel |
| Memoire volatile (volatility3 outille, catalogue SF-M, connaissances dediees) | operationnel |
| Reseau (tshark + suricata offline, triage ET Open, catalogue SF-R) | operationnel |
| Referentiels amont (ForensicArtifacts + DFIQ bakes au build, moteur referentiels.py) | operationnel |
| Intake de contexte a l'ouverture d'affaire (/analyse) | operationnel |
| Competences d'agent (9 skills) | operationnelles |
| Templates de livrables (5 templates) | operationnels |
| Deploiement multi-laptops (profils online / air-gap) | operationnel |

## Roadmap

- **v1.1 Memoire volatile** : livree - exploitation volatility3 outillee en affaire (wrapper `dt`), catalogue SF-M, connaissances dediees, acquisition RAM en guidance (deja documentee)
- **v1.2 Reseau** : livree - tshark + suricata offline (ET Open trie + regles kit), catalogue SF-R, echantillons pcap synthetiques, triage validable en E2E
- **v1.3 Referentiels amont** : livree - ForensicArtifacts + DFIQ telecharges et bakes a chaque build, moteur `referentiels.py` (rapprochement, expansion, plans DFIQ), intake de contexte a l'ouverture d'affaire
- **v2.0 Disque complet** : acquisition image (E01/AFF4/raw), The Sleuth Kit et plaso sur images, collection par artefacts (`--artifact_filters`)
- **v2.1 Navigateurs** : historiques, caches, sessions (adosse a webbrowser.yaml + DFIQ Q1020)
- **v2.2 Conteneurs** : docker/containerd/kubernetes.yaml, journaux d'orchestrateurs
- **v2.3 Cloud** : cloud_services.yaml (cadre DFIQ S1005), gaps documentes
- **Mobile** : hors referentiels amont (pas de definitions Android/iOS) - artefacts kit dedies a produire

## Licences

- **Kit OREOA-AI (ce depot)** : [AGPL-3.0](LICENSE) - Copyright le ou les auteurs du projet
- **Outils embarques dans l'image** : ils conservent leurs licences propres (Apache-2.0, MIT, BSD-3-Clause, GPL, Volatility Software License v1.0) - agregation simple, aucune relicence. Details et mentions : [docs/NOTICE](docs/NOTICE)
- L'usage commercial du kit et des outils embarques est permis par leurs licences respectives, avec obligation de partage des modifications (copyleft) - voir le cas particulier volatility3 dans NOTICE

## Verification de sante

```bash
python3 scripts/doctor.py check     # sante : prerequis, image, bundle, disque
python3 scripts/doctor.py fix       # provisioning : bundle air-gap ou build
python3 scripts/doctor.py test      # outils du conteneur + tests fonctionnels + E2E
```
