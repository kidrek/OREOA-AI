# DEPLOY.md - multi-laptop deployment guide

Reference protocol to deploy the OREOA-AI kit on one or several investigation laptops,
from a bare OS to the first case, in online or air-gap profiles. French version:
[DEPLOY.fr.md](DEPLOY.fr.md).

**Guidance mode**: this document is read by the agent. Simply ask the agent to guide
you through the kit deployment - it drives step by step, verifies every output and
executes itself whatever does not require privileges. Guidance behavior is defined in
`skills/deploiement.md`.

## 1. Overview

The three-step path:

```
1. Prepare the host        Docker, git, Python, docker group (analyst, sudo commands)
2. Deploy and provision    kit folder -> doctor check / fix / test (agent or analyst)
3. Configure the LLM       tool auth flow (cloud) or provider block (gateway, local)
```

| Actor | Role |
|-------|------|
| Analyst | sudo actions (Docker install, group), tool auth flow, decisions |
| Agent | diagnosis, provisioning via doctor, tests, step-by-step guidance |
| doctor | health measurement, provisioning with disk-space barrier, qualification |

## 2. Host prerequisites (Debian/Ubuntu)

| Component | Version | Verification |
|-----------|---------|--------------|
| Debian or Ubuntu | 12+ | `cat /etc/os-release` |
| Docker Engine + CLI | >= 20.10 | `docker version` |
| git | >= 2.30 | `git --version` |
| Python 3 | >= 3.10 | `python3 --version` |
| pyyaml | latest | `python3 -c "import yaml"` |
| bash | >= 4.2 | built-in |

### Docker installation

**Simple path (distribution package)**:

```bash
sudo apt update
sudo apt install -y docker.io
sudo systemctl enable --now docker
```

**Alternative path (official Docker repository, newer versions)**: follow the official
"Install Docker Engine on Debian/Ubuntu" procedure (`download.docker.com` repository) -
the kit does not require a recent version, the simple path is enough.

### Docker group (mandatory)

```bash
sudo usermod -aG docker $USER
```

**Important**: group membership only takes effect at the opening of a **new session**.
Verify after re-login: `id -Gn | grep docker`.

### Other prerequisites

```bash
sudo apt install -y git python3 python3-yaml
```

Recommended disk space: 20 GB free (the provisioning barrier refuses any write below
3 GB for a build, 2 GB for a bundle load - `config/tools.yaml`).

## 3. Kit acquisition

### Online profile

```bash
git clone https://github.com/kidrek/OREOA-AI.git
cd OREOA-AI
```

### Air-gap profile

1. On a connected machine: clone the repository and produce an archive:

```bash
git clone https://github.com/kidrek/OREOA-AI.git
tar czf oreoa-ai-<version>.tar.gz --exclude=.git --exclude=cases OREOA-AI
sha256sum oreoa-ai-<version>.tar.gz
```

2. Transfer the archive and its hash via removable media.
3. On the isolated laptop: extract and **verify the hash before any manipulation**.

## 4. Provisioning

By the agent (autonomous) or manually:

```bash
python3 scripts/doctor.py check   # health: prerequisites, image, bundle, disk space
python3 scripts/doctor.py fix     # provisioning: air-gap bundle if present, else build
python3 scripts/doctor.py test    # 8 tools + libraries + copyright + E2E
```

Key behaviors:

- **Disk-space barrier**: `fix` refuses any write if free space on the Docker storage
  partition is below the thresholds (3 GB build / 2 GB bundle load)
- **Air-gap bundle**: if `tools/oreoa-ai-tools-<tag>.tar.gz` is present, `fix` loads it
  (`docker load`) without network
- **Upstream referentials at build**: in online build, `fix` systematically rebuilds
  the image (cache preserved) to refresh the embedded referentials (ForensicArtifacts
  latest release + DFIQ main) - versions displayed after the build, details in
  [REFERENTIALS.md](REFERENTIALS.md)
- **Qualification**: `test` verifies every pinned tool, the libraries, the copyright
  files, the integrity of the embedded referentials, and runs the end-to-end test.
  `OK` verdict = operational laptop

## 5. LLM configuration

Decision tree:

```
Which LLM?
├── Standard cloud (Anthropic, OpenAI...) + online laptop
│     -> tool auth flow (opencode /connect or claude /login)
├── Corporate OpenAI-compatible gateway + online
│     -> provider block in opencode.json
└── Local (air-gap)
      -> Ollama or vLLM, provider block in opencode.json
```

### 5.1 Standard cloud - tool auth flow

The analyst runs the interactive flow (credentials stored in their home, never in the
repository):

```text
opencode > /connect        # follow the provider flow (browser)
claude  > /login           # Claude Code equivalent
```

Verification: the conversation with the agent works - that is the proof the LLM
answers. Advantage: no API key in files, per-user per-machine credentials (autonomous
instances).

### 5.2 Corporate OpenAI-compatible gateway

`provider` block in `opencode.json` (key provided through environment variable, never
in clear):

```json
{
  "provider": {
    "corporate": {
      "npm": "@ai-sdk/openai-compatible",
      "options": { "baseURL": "https://llm-gateway.internal/v1" }
    }
  },
  "model": "corporate/deployed-model"
}
```

### 5.3 Local - Ollama (air-gap)

```bash
# connected machine (preparation):
ollama pull <model>
# transfer the models via media: OLLAMA_MODELS directory (~/.ollama/models)

# isolated laptop:
ollama serve               # listens on localhost:11434
curl -s http://localhost:11434/v1/models | head    # verification
```

```json
{
  "provider": {
    "ollama": {
      "npm": "@ai-sdk/openai-compatible",
      "options": { "baseURL": "http://localhost:11434/v1" },
      "models": { "<model>": { "name": "<model> (local)" } }
    }
  },
  "model": "ollama/<model>"
}
```

### 5.4 Local - vLLM (air-gap, GPU)

```bash
vllm serve <model> --port 8000
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
  "model": "vllm/<model>"
}
```

**Air-gap rule**: no network during the investigation - only the local LLM service is
contacted; tool containers are always network-less (`--network none`).

## 6. Case exchange between laptops

Every instance is autonomous: it sees no other. Exchanges are explicit.

| Flow | Channel | Security |
|------|---------|----------|
| Kit code, methodology, catalogues | git repository | common versions (see section 7) |
| Evidence, cases, reports | removable media | manifest SHA256 verified at import |

Case transfer procedure:

1. Export the full case directory (`cases/CASE-xxx/`) to the media
2. At import: recompute collection SHA256s and compare with `manifest.yaml`
3. Journalize the transfer in the case `journal.md` (date, source, destination, hashes)

## 7. Maintenance and fleet consistency

Every instance is autonomous, but the fleet only stays comparable if versions are
aligned.

**Golden rule: same repository commit + same image digest on every instance.**

Instance version upgrade:

```bash
git pull                              # new kit version
python3 scripts/doctor.py fix         # rebuild (cache preserved: LABEL at the end of the Dockerfile)
python3 scripts/doctor.py test        # full requalification
```

The digest of the new image is journalized in the cases processed after the upgrade
(forensic traceability). Cases in progress: close or archive them before the upgrade.
Never hand-patch the image or the bundle.

## 8. New laptop checklist

```
[ ] Debian/Ubuntu OS up to date
[ ] Docker installed and daemon active (docker version)
[ ] User in the docker group (after new session: id -Gn)
[ ] git + python3 + pyyaml installed
[ ] 20 GB free minimum (doctor barrier: 3 GB build / 2 GB load)
[ ] Kit deployed (clone or media, hash verified in air-gap)
[ ] doctor check: OK verdict
[ ] doctor fix: image provisioned, digest recorded
[ ] doctor test: OK verdict (8 tools + libraries + copyright + E2E)
[ ] LLM configured and verified (/connect, auth login or local curl OK)
[ ] First session: agent tool launched in the folder, self-test + welcome displayed
[ ] First test case created (/case) and journal initialized
```

## 9. First launch and guidance mode

No launcher: the analyst opens their agent tool directly in the kit folder.

```bash
opencode                      # or claude, or any agent reading AGENTS.md
```

LLM connection is handled by the agent tool itself (OpenCode and Claude Code have
their own auth flows; advanced configuration - custom provider, air-gap - section 5
above). The "Demarrage" section of `AGENTS.md` defines the first-response behavior:

1. **Spontaneous health**: the agent reads `MEMORY.md`, runs `doctor check` +
   `doctor test`, reports the verdict in 3 lines
2. **Routing**: deployment guidance if incomplete; first launch (`cases/` with no
   case) -> display of the `docs/QUICK-START.md` guide then intention request;
   following sessions -> verdict + short reminder
3. **Two commands**: `/case "<name>"` (open a case: creation or switch, context,
   deposits) then drop the collections into `00_evidence/originals/`, and `/analyse`
   (full investigation with gates)

Quick commands in the agent:

```text
/case "case name"                 # open or switch a case
/analyse                          # full investigation of the current case
/deploy                           # restart deployment guidance
```

Alternative LLM configuration on the command line: `opencode auth login` (equivalent
of `/connect`, credentials in `~/.local/share/opencode/auth.json`). For a local
endpoint (air-gap): provider block in the global `~/.config/opencode/opencode.json`
config - ready-to-adapt example in `config/profiles/opencode-airgap.example.json`.
