# OREOA-AI - agentic digital forensics kit

**OREOA-AI** is the agentic branch of the OREOA project: a self-contained digital
forensics (DFIR) kit deployable on multiple investigation laptops, where an agent
(OpenCode, Claude Code, or any agent reading `AGENTS.md`) identifies the collections,
runs a standardized investigation (ISO 27037, ISO 27035, ISO 27043, NIST SP 800-86)
and produces a complete report (timeline, affected assets, observables, containment,
remediation). French documentation: [README.fr.md](README.fr.md).

## Getting started: three gestures, no scripts

```bash
git clone https://github.com/kidrek/OREOA-AI.git
cd OREOA-AI
opencode              # or claude, or any agent reading AGENTS.md
```

At the first response, the agent checks kit health (doctor) and displays the
quick-start guide. Then three gestures are enough:

| Gesture | Command | What happens |
|---------|---------|--------------|
| 1. Open a case | `/case "Web server incident"` | the agent scaffolds the tree, asks for the incident context (non-blocking) and gives you the ID |
| 2. Drop your collections | copy your files into `cases/<ID>/00_evidence/originals/` | the agent detects the deposits, asks for provenance, hashes (SHA256) and matches the artifact referential |
| 3. Run the investigation | `/analyse` | full workflow (triage, analysis, correlation, investigation, observables, report) with validation at every key step |

The final report is sourced: every conclusion cites its collection, its artifact and
its hash. Kit health is verified at every session (doctor) - if something is missing
(image, LLM), the agent guides you through the fix before any investigation. The
manual alternative for a human or CI: `./install.sh check|fix|test` - full protocol in
[docs/DEPLOY.md](docs/DEPLOY.md).

## Languages

The kit is bilingual. The knowledge base (skills, methodology, catalogues) stays French
(single source of truth); the agent conversation mirrors the analyst's language;
case deliverables and journal follow `case.language` of the manifest (default
English, from `config/tools.yaml`). Command `/lang` views or changes the session
language. Machine schema (manifest keys) and script messages are English.
French docs: [README.fr.md](README.fr.md), [docs/USER-GUIDE.fr.md](docs/USER-GUIDE.fr.md),
[docs/DEPLOY.fr.md](docs/DEPLOY.fr.md).

## Prerequisites

| Component | Version | Usage |
|-----------|---------|-------|
| git | >= 2.30 | repo, sharing, sync |
| Docker | >= 24, active daemon | image build, tool execution |
| bash | >= 4.2 | scripts |
| Python 3 | >= 3.10 + pyyaml | kit scripts |
| Agent | OpenCode or Claude Code (or any AGENTS.md reader) | driving |

The user running docker commands must be a member of the `docker` group (effective at
next session opening).

Network access is required only for: the first `docker build`, LLM model downloads.
Once these are present, everything runs offline.

## Opening a case

Everything happens in conversation: `/case "Web server incident 2026-45"` (auto-numbered
ID) - the agent scaffolds the tree, asks for the incident context, then detects evidence
deposits. `/case` alone shows the case panorama (resume a case, switch, open another).
Without custom commands (another agent tool), ask in natural language: it follows the
procedure documented in `AGENTS.md` (section "Structure du dossier d'affaire").

Produced scaffold:

```
cases/CASE-2026-0042/
├── 00_evidence/                 # evidence - not versioned
│   ├── originals/               # analyst drop zone (raw collections) - immutable after import
│   ├── exports/                 # extractions and transcodes, hashed
│   └── images/                  # disk images, RAM, dumps
├── 01_work/                     # working space (processing copies)
├── 02_analysis/
│   ├── logs/                    # per-phase action journal
│   ├── timeline/                # consolidated timeline
│   ├── ioc/                     # observables
│   └── report/                  # report being written
├── manifest.yaml                # collection inventory + SHA256 + context
└── journal.md                   # append-only action journal
```

## Launching the agent

```bash
opencode                        # in the kit folder
> /case "Web server incident"
> (drop the collections into cases/CASE-2026-0042/00_evidence/originals/)
> /analyse
```

The agent reads `AGENTS.md`, loads the skills, runs the methodology, journalizes every
action and writes the report from the templates. LLM connection is handled by your
agent tool itself (OpenCode and Claude Code have their own auth flows) - advanced
configuration (provider, air-gap) in [docs/DEPLOY.md](docs/DEPLOY.md) section 5.

## Architecture

Two layers in a single repository:

- **Host layer (light)**: scanner, integrity checker, wrappers - runs on any laptop with Docker
- **Tool layer (containerized)**: image `oreoa-ai-tools:1.1.0` - plaso (log2timeline, psort), volatility3, The Sleuth Kit (fls, icat, mmls, fsstat), tshark, suricata (ET Open triaged + kit rules), yara, regipy, evtx, artifacts library, pytsk3 + libewf (raw/E01 disk images) - all pinned by version, built from the kit `Dockerfile`
- **Upstream referentials baked into the image at every build**: ForensicArtifacts (collection definitions, Apache-2.0) and DFIQ (scenarios/facets/questions, Apache-2.0) - downloaded by the `Dockerfile` (cache-bust ARG, SHA256 verification, baked traces), usable via `scripts/referentiels.py` (see [docs/REFERENTIALS.md](docs/REFERENTIALS.md))

Execution rules: network-less containers (`--network none`), `00_evidence` mounted
read-only, output under the analyst identity (no root), all calls through the
`scripts/dt` wrapper.

Deployment profiles:

| Profile | Behavior |
|---------|----------|
| [online](config/profiles/online.md) | image build from official sources, LLM via OpenAI-compatible endpoint |
| [air-gap](config/profiles/airgap.md) | bundle loading `tools/oreoa-ai-tools-1.1.0.tar.gz` (`docker load`), local LLM (Ollama/vLLM), no network access |

Multi-laptop deployment:

1. Shared git repository (internal server or GitHub)
2. `oreoa-ai-tools` image built locally or shared as a bundle (see air-gap profile)
3. LLM models downloaded to a shared cache or installed locally
4. Case exchange through git repository (metadata) + removable media (evidence)

## 7-phase workflow

| Phase | Skill | Output |
|-------|-------|--------|
| 0. Import | `ingestion` | collections scanned, typed, hashed, artifact-matched, manifest.yaml |
| 1. Triage | `triage` | analyst context, case type, DFIQ scenario, main collection, hypotheses |
| 2. Initial analysis | `analyse` | affected assets, initial chronology |
| 3. Correlation | `analyse` | consolidated timeline, multi-collection crossings |
| 4. Investigation | `analyse` + `investigation` | tested hypotheses and DFIQ questions, explored gaps |
| 5. Observables | `analyse` | IOC table with confidence level |
| 6. Report | `reporting` | final report: full, executive or technical |

The `guidance` mode covers manual investigation actions: RAM capture, disk
acquisition, live response - the agent guides the analyst step by step (see
[skills/guidance.md](skills/guidance.md) and [connaissances/](connaissances/)). The
collected dump is then processed by the kit (volatility3).

## Weak-signal catalogue

The analytical core of the kit: for each artifact family, formalized, searchable and
cross-checkable weak signals.

Signal sheet format (example):

```text
SF-W-030 - lsass memory access
- artifact: Sysmon EventID 10 (lsass target)
- logic: granted access 0x1010 / 0x147a by a non-managed process
- attack: T1003.001 (LSASS Memory)
- severity: high | confidence: high
- false positives: managed EDR/backup dumpers (allowlist)
```

| Catalogue | Content |
|-----------|---------|
| [catalogue/windows.md](catalogue/windows.md) | Windows signals (SF-W) |
| [catalogue/linux.md](catalogue/linux.md) | Linux signals (SF-L) |
| [catalogue/memoire.md](catalogue/memoire.md) | volatile memory signals (SF-M) |
| [catalogue/reseau.md](catalogue/reseau.md) | network signals (SF-R) |
| [catalogue/disque.md](catalogue/disque.md) | disk signals (SF-D, v2.0: raw/dd/E01 images) |
| [catalogue/correlation.md](catalogue/correlation.md) | multi-signal correlation rules (C-XX chains) |
| [catalogue/artefacts.md](catalogue/artefacts.md) | generated ForensicArtifacts index + signal/artifact mapping |
| [catalogue/dfiq.md](catalogue/dfiq.md) | generated DFIQ index + scenario/case-type mapping |

## Built-in safeguards

| Safeguard | Mechanism |
|-----------|-----------|
| Evidence immutable after import | deposits in `originals/` hashed at ingestion; every scan re-verifies the hashes - any drift is an integrity alert |
| No network | containers `--network none`, air-gap profiles without access |
| Traceability | every conclusion cites collection + artifact + hash; image digest recorded |
| Disk barrier | provisioning refused if free space is insufficient (nothing written) |

## State v2.0

| Module | State |
|--------|-------|
| Ingestion (typing, SHA256, provenance, artifact matching, manifest, disk magic disambiguation) | operational |
| Integrity checker (doctor check / fix / test, referentials) | operational |
| Containerized toolchain (11 tools + 6 libraries) | operational |
| Weak-signal catalogue (56 signals + 8 chains) | operational |
| Volatile memory (volatility3 tooled, SF-M catalogue, dedicated knowledge) | operational |
| Network (tshark + suricata offline, ET Open triage, SF-R catalogue) | operational |
| Full disk (raw/dd/E01, TSK without mounting + plaso super-timeline, targeted artifact extraction, SF-D catalogue) | operational |
| Upstream referentials (ForensicArtifacts + DFIQ baked at build, referentiels.py engine) | operational |
| Case context intake at opening (/case) | operational |
| Languages (schema EN, scripts EN, knowledge FR, deliverables per case language) | operational |
| Agent skills (10 skills) | operational |
| Deliverable templates (6 templates) | operational |
| Multi-laptop deployment (online / air-gap profiles) | operational |

## Roadmap

- **v1.1 Volatile memory**: delivered - tooled volatility3 exploitation in cases (wrapper `dt`), SF-M catalogue, dedicated knowledge, RAM acquisition in guidance
- **v1.2 Network**: delivered - tshark + suricata offline (triaged ET Open + kit rules), SF-R catalogue, synthetic pcap samples, E2E-testable triage
- **v1.3 Upstream referentials**: delivered - ForensicArtifacts + DFIQ downloaded and baked at every build, `referentiels.py` engine (matching, expansion, DFIQ plans), case context intake
- **v1.3bis Simplified launch**: delivered - agent.sh removed, `/case` command (create/switch/panorama), analyst deposits with integrity-verified scan, first-launch guide
- **v1.4 Internationalization**: delivered - EN schema and scripts, EN-primary docs, language rules + /lang
- **v2.0 Full disk**: delivered - raw/dd/E01 images, The Sleuth Kit without mounting (`disk.py`: info/verify/listing/bodyfile/extract), plaso super-timeline, targeted artifact extraction, 3x-image disk barrier, SF-D catalogue; AFF4 and composite/encrypted volumes documented as gaps
- **v2.1 Browsers**: history, caches, sessions (backed by webbrowser.yaml + DFIQ Q1020)
- **v2.2 Containers**: docker/containerd/kubernetes.yaml, orchestrator logs
- **v2.3 Cloud**: cloud_services.yaml (DFIQ S1005 frame), documented gaps
- **Mobile**: outside upstream referentials (no Android/iOS definitions) - dedicated kit artifacts to produce

## Licenses

- **OREOA-AI kit (this repo)**: [AGPL-3.0](LICENSE) - Copyright the project authors
- **Tools embedded in the image**: they keep their own licenses (Apache-2.0, MIT, BSD-3-Clause, GPL, Volatility Software License v1.0) - simple aggregation, no relicensing. Details and notices: [docs/NOTICE](docs/NOTICE)
- **Upstream referentials**: ForensicArtifacts and DFIQ (Apache-2.0) - downloaded at build, never edited, provenance in [docs/REFERENTIALS.md](docs/REFERENTIALS.md)
- Commercial use of the kit and embedded tools is permitted by their respective licenses, with share-alike obligations (copyleft) - see the volatility3 special case in NOTICE

## Health check

```bash
python3 scripts/doctor.py check     # health: prerequisites, image, bundle, disk
python3 scripts/doctor.py fix       # provisioning: air-gap bundle or build
python3 scripts/doctor.py test      # container tools + functional tests + E2E
```
