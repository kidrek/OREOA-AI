# DEPLOY.md - Guide de deploiement multi-laptops

Protocole de reference pour deployer le kit OREOA-AI sur un ou plusieurs laptops d'investigation, depuis un OS vierge jusqu'a la premiere affaire, en profils en-ligne ou air-gap.

**Mode guidance** : ce document est lu par l'agent. Demande simplement a l'agent de te guider pour deployer le kit - il conduit pas a pas, verifie chaque retour et execute lui-meme ce qui ne requiert pas de privileges. Le comportement de guidage est defini dans `skills/deploiement.md`.

## 1. Vue d'ensemble

Le parcours en trois temps :

```
1. Preparer l'hote        Docker, git, Python, groupe docker (analyste, commandes sudo)
2. Deployer et provisionner   dossier du kit -> doctor check / fix / test (agent ou analyste)
3. Configurer le LLM      /connect (cloud) ou bloc provider (passerelle, local)
```

| Acteur | Role |
|--------|------|
| Analyste | actions sudo (installation Docker, groupe), lancement de `/connect`, decisions |
| Agent | diagnostic, provisioning via doctor, tests, guidage pas a pas |
| doctor | mesure de sante, provisioning avec barriere d'espace disque, qualification |

## 2. Prerequis de l'hote (Debian/Ubuntu)

| Composant | Version | Verification |
|-----------|---------|--------------|
| Debian ou Ubuntu | 12+ | `cat /etc/os-release` |
| Docker Engine + CLI | >= 20.10 | `docker version` |
| git | >= 2.30 | `git --version` |
| Python 3 | >= 3.10 | `python3 --version` |
| pyyaml | derniere | `python3 -c "import yaml"` |
| bash | >= 4.2 | integre |

### Installation de Docker

**Voie simple (paquet de la distribution)** :

```bash
sudo apt update
sudo apt install -y docker.io
sudo systemctl enable --now docker
```

**Voie alternative (depot officiel Docker, versions plus recentes)** : suivre la procedure officielle "Install Docker Engine on Debian/Ubuntu" (depot `download.docker.com`) - le kit n'exige pas de version recente, la voie simple suffit.

### Groupe docker (obligatoire)

```bash
sudo usermod -aG docker $USER
```

**Important** : l'appartenance au groupe n'est effective qu'a l'ouverture d'une **nouvelle session** de l'utilisateur. Verifier apres reconnexion : `id -Gn | grep docker`.

### Autres prerequis

```bash
sudo apt install -y git python3 python3-yaml
```

Espace disque recommande : 20 Go libres (la barriere de provisioning refuse toute ecriture sous 3 Go pour un build, 2 Go pour un chargement de bundle - `config/tools.yaml`).

## 3. Acquisition du kit

### Profil en-ligne

```bash
git clone https://github.com/kidrek/OREOA-AI.git
cd OREOA-AI
```

### Profil air-gap

1. Sur une machine connectee : cloner le depot et produire une archive :

```bash
git clone https://github.com/kidrek/OREOA-AI.git
tar czf oreoa-ai-<version>.tar.gz --exclude=.git --exclude=cases OREOA-AI
sha256sum oreoa-ai-<version>.tar.gz
```

2. Transférer l'archive et son empreinte par media amovible.
3. Sur le laptop isole : extraire et **verifier l'empreinte avant toute manipulation**.

## 4. Provisioning

Par l'agent (autonome) ou manuellement :

```bash
python3 scripts/doctor.py check   # sante : prerequis, image, bundle, espace disque
python3 scripts/doctor.py fix     # provisioning : bundle air-gap si present, sinon build
python3 scripts/doctor.py test    # 8 outils + bibliotheques + copyright + E2E
```

Comportements cles :

- **Barriere d'espace disque** : `fix` refuse toute ecriture si l'espace libre sur la partition de stockage Docker est inferieur aux seuils (3 Go build / 2 Go chargement de bundle)
- **Bundle air-gap** : si `tools/oreoa-ai-tools-<tag>.tar.gz` est present, `fix` le charge (`docker load`) sans reseau
- **Referentiels amont au build** : en build en-ligne, `fix` reconstruit systematiquement l'image (cache preserve) pour rafraichir les referentiels embarques (ForensicArtifacts release la plus recente + DFIQ main) - versions affichees apres le build, details dans [REFERENTIALS.fr.md](REFERENTIALS.fr.md)
- **Qualification** : `test` verifie chaque outil pinné, les bibliotheques, la presence des fichiers copyright, l'integrite des referentiels embarques, et execute le test de bout en bout. Verdict `OK` = laptop operationnel

## 5. Configuration LLM

Arbre de decision :

```
Quel LLM ?
├── Cloud standard (Anthropic, OpenAI...) + laptop en ligne
│     -> /connect (opencode) ou /login (claude code)
├── Passerelle OpenAI-compatible d'entreprise + en ligne
│     -> bloc provider dans opencode.json
└── Local (air-gap)
      -> Ollama ou vLLM, bloc provider dans opencode.json
```

### 5.1 Cloud standard - `/connect`

L'analyste lance la commande interactive lui-meme (identifiants stockes dans son home, jamais dans le depot) :

```text
opencode > /connect        # suivre le flux du provider (navigateur)
claude  > /login           # equivalent Claude Code
```

Verification : la conversation avec l'agent fonctionne - c'est la preuve que le LLM repond. Avantage : aucune cle API dans les fichiers, credentials par utilisateur et par machine (instances autonomes).

### 5.2 Passerelle OpenAI-compatible d'entreprise

Bloc `provider` dans `opencode.json` (cle fournie par variable d'environnement, jamais en clair) :

```json
{
  "provider": {
    "entreprise": {
      "npm": "@ai-sdk/openai-compatible",
      "options": { "baseURL": "https://llm-gateway.interne/v1" }
    }
  },
  "model": "entreprise/modele-deployee"
}
```

### 5.3 Local - Ollama (air-gap)

```bash
# machine connectee (preparation) :
ollama pull <modele>
# transferer les modeles par media : repertoire OLLAMA_MODELS (~/.ollama/models)

# laptop isole :
ollama serve               # ecoute localhost:11434
curl -s http://localhost:11434/v1/models | head    # verification
```

```json
{
  "provider": {
    "ollama": {
      "npm": "@ai-sdk/openai-compatible",
      "options": { "baseURL": "http://localhost:11434/v1" },
      "models": { "<modele>": { "name": "<modele> (local)" } }
    }
  },
  "model": "ollama/<modele>"
}
```

### 5.4 Local - vLLM (air-gap, GPU)

```bash
vllm serve <modele> --port 8000
curl -s http://localhost:8000/v1/models | head     # verification
```

```json
{
  "provider": {
    "vllm": {
      "npm": "@ai-sdk/openai-compatible",
      "options": { "baseURL": "http://localhost:8000/v1", "apiKey": "EMPTY" }
    }
  },
  "model": "vllm/<modele>"
}
```

**Regle air-gap** : aucun reseau pendant l'investigation - seul le service LLM local est contacte ; les conteneurs d'outils sont toujours sans reseau (`--network none`).

## 6. Echange d'affaires entre laptops

Chaque instance est autonome : elle ne voit pas les autres. Les echanges sont explicites.

| Flux | Canal | Securite |
|------|-------|----------|
| Code du kit, methodologie, catalogues | depot git | version communes (voir section 7) |
| Evidence, affaires, rapports | media amovible | SHA256 du manifest verifiee a l'import |

Procedure de transfert d'affaire :

1. Exporter le dossier d'affaire complet (`cases/CASE-xxx/`) sur le media
2. A l'import : recalculer les SHA256 des collections et les comparer au `manifest.yaml`
3. Journaliser le transfert dans `journal.md` de l'affaire (date, source, destination, empreintes)

## 7. Maintenance et coherence du parc

Chaque instance est autonome, mais le parc ne reste comparable que si les versions sont alignees.

**Regle d'or : meme commit du depot + meme digest d'image sur toutes les instances.**

Montee de version d'une instance :

```bash
git pull                              # nouvelle version du kit
python3 scripts/doctor.py fix         # rebuild (cache preserve : LABEL en fin de Dockerfile)
python3 scripts/doctor.py test        # requalification complete
```

Le digest de la nouvelle image est journalise dans les affaires traitees apres la montee de version (tracabilite forensique). Affaires en cours : les clore ou les archiver avant la montee de version. Jamais de patch manuel de l'image ou du bundle.

## 8. Checklist laptop neuf

```
[ ] OS Debian/Ubuntu a jour
[ ] Docker installe et demon actif (docker version)
[ ] Utilisateur dans le groupe docker (apres nouvelle session : id -Gn)
[ ] git + python3 + pyyaml installes
[ ] 20 Go libres minimum (barriere doctor : 3 Go build / 2 Go load)
[ ] Kit deploye (clone ou media, empreinte verifiee en air-gap)
[ ] doctor check : verdict OK
[ ] doctor fix : image provisionnee, digest consigne
[ ] doctor test : verdict OK (8 outils + bibliotheques + copyright + E2E)
[ ] LLM configure et verifie (/connect, auth login ou curl local OK)
[ ] Premiere session : outil agentique lance dans le dossier, autotest + accueil affiches
[ ] Premiere affaire de test creee (/case) et journal initie
```

## 9. Premier lancement et mode guidance

Aucun lanceur : l'analyste ouvre son outil agentique directement dans le dossier du kit.

```bash
opencode                      # ou claude, ou tout agent lisant AGENTS.md
```

La connexion au modele LLM est geree par l'outil agentique lui-meme (opencode et
Claude Code ont leur propre flux d'authentification ; configuration avancee - provider
personnalise, air-gap - section 5 ci-dessus). La section "Demarrage" d'`AGENTS.md`
definit le comportement de la premiere reponse :

1. **Sante spontanee** : l'agent lit `MEMORY.md`, execute `doctor check` + `doctor test`, rapporte le verdict en 3 lignes
2. **Routage** : guidage de deploiement si incomplet ; premier lancement (`cases/` sans affaire) -> affichage du guide `docs/QUICK-START.fr.md` puis demande d'intention ; sessions suivantes -> verdict + rappel court
3. **Deux commandes** : `/case "<nom>"` (ouvrir une affaire : creation ou switch, contexte, depots) puis deposer les collectes dans `00_evidence/originals/`, et `/analyse` (investigation complete avec gates)

Commandes rapides dans l'agent :

```text
/analyse chemin/vers/collection   # lancer une investigation complete
/deploy                           # relancer le guidage de deploiement
```

Configuration LLM alternative en ligne de commande : `opencode auth login` (equivalent de `/connect`, identifiants dans `~/.local/share/opencode/auth.json`). Pour un endpoint local (air-gap) : bloc provider dans la config globale `~/.config/opencode/opencode.json` - exemple pret a adapter dans `config/profiles/opencode-airgap.example.json`.
