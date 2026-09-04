# Docker Build Specification — OREOA-AI (v1, companion to project prompt v4)
 
> Authoritative for everything under `docker/`, `compose.yaml`, `Makefile` and `versions.env`.
> Any deviation from the hardening rules below is a defect, not a choice. Versions are **never** written inline in Dockerfiles: they live in `versions.env` and lock files, resolved by `make pins`.
 
---
 
## 1. Repository layout
 
```
oreoa-ai/
├── CLAUDE.md / AGENTS.md          # project prompt v4 (rendered copy)
├── compose.yaml                   # single compose file, profiles for optional pieces
├── compose.local-llm.yaml         # override: host.docker.internal wiring, no proxy for LLM
├── .env.example                   # runtime settings (models, endpoints, case root)
├── versions.env                   # ALL pinned versions (images, tools, rule sets)
├── Makefile
├── docker/
│   ├── base/Dockerfile            # python 3.12, non-root user, tini, common libs
│   ├── agent/Dockerfile           # base + Node LTS + OpenCode (+ Claude Code optional)
│   ├── worker-fast/Dockerfile     # base + Dissect + quick parsers + Sigma engines + YARA + ClamAV
│   ├── worker-deep/Dockerfile     # worker-fast + plaso + Volatility 3 + capa/FLOSS/DIE + unified-log parser
│   ├── mcp/Dockerfile             # base + mcp servers (one image, 4 entrypoints)
│   ├── proxy/                     # tinyproxy config template + entrypoint
│   └── seccomp/                   # default-strict profile shared by all services
├── agents/  commands/  hunts/  mappings/  packs/  knowledge/  scoring.yaml
├── src/oreoa/                     # python package: models, ingest, hunts runner, mcp servers, cli
├── tests/                         # pytest incl. infra tests (see §9)
└── cases/                         # bind-mounted case root (outside the image)
```
 
## 2. Compose topology
 
```
                       ┌──────────────┐    LLM endpoints only
   analyst TTY ──────► │    agent     │ ──► proxy ──► (internet allow-list)
                       │ OpenCode/CC  │
                       └──────┬───────┘
          MCP (streamable HTTP, internal network only)
   ┌──────────┬───────────────┼───────────────┬──────────────┐
mcp-evidence  mcp-knowledge  mcp-case       mcp-jobs ──► redis ──► worker-fast (x1, conc. 2)
   │              │             │                                 worker-deep (x1, conc. 1)
   └──── read derived/ ─────────┘                                   │
                                            cases/<id>/evidence (ro), derived (rw), extracted (rw, noexec)
```
 
| Service | Image | Networks | Mounts | Purpose |
|---|---|---|---|---|
| `agent` | `oreoa/agent` | `egress`, `internal` | `cases/` rw (evidence subtree ro), `knowledge/` ro, `agents/ commands/` ro | Runs OpenCode (or Claude Code) TUI for the analyst; talks to MCP servers and to `proxy` |
| `proxy` | `oreoa/proxy` | `egress`, `external` | none | Allow-list forward proxy; the only service with internet access |
| `redis` | `redis:<pin>-alpine` | `internal` | tmpfs | RQ broker + job status |
| `worker-fast` | `oreoa/worker-fast` | `internal` | `cases/` (evidence ro, derived rw), `knowledge/` ro | fast lane jobs |
| `worker-deep` | `oreoa/worker-deep` | `internal` | same | deep lane jobs, resource-capped |
| `mcp-evidence` | `oreoa/mcp` | `internal` | `cases/` ro (derived), `knowledge/` ro | DuckDB queries, hunts, search, get_raw |
| `mcp-knowledge` | `oreoa/mcp` | `internal` | `knowledge/` ro | DFIQ, artifacts, Sigma, ATT&CK, YARA index |
| `mcp-case` | `oreoa/mcp` | `internal` | `cases/<id>/{case.yaml,journal.md,state}` rw | gated mutations, citation check |
| `mcp-jobs` | `oreoa/mcp` | `internal` | none (talks to redis) | enqueue/status/cancel/wait/extract/unlock/fetch_symbol |
| `fetcher` (profile `symbol-fetch`) | `oreoa/fetcher` | `internal`, `external` | `knowledge/custom/volatility_symbols/` rw | Downloads Windows kernel PDBs from two allow-listed hosts on a confirmed job, converts to ISF. The only service besides `proxy` with internet, and only to those hosts. |
 
Networks: `internal` (`internal: true` — no default route), `egress` (agent ↔ proxy only), `external` (proxy only). Workers and MCP servers are on `internal` exclusively: **they cannot reach the internet by construction**, not by configuration.
 
Profiles: `local-llm` (adds `extra_hosts: host.docker.internal:host-gateway` to `agent`, LLM traffic bypasses `proxy` for that host only), `claude-code` (installs/enables the alternate runtime), `symbol-fetch` (adds the `fetcher` service; off by default).
 
## 3. Images
 
### 3.1 `base`
- `python:3.12-slim-bookworm@sha256:<pin>` (digest-pinned).
- Creates user `oreoa` uid/gid `10001`, home `/home/oreoa`, no shell login for others.
- `tini` as PID 1. `PYTHONDONTWRITEBYTECODE=1`, `PIP_NO_CACHE_DIR=1`, `UMASK=027`.
- System libs only: `libmagic1`, `libewf2`, `zstd`, `ca-certificates`, `tzdata`. No compilers in the final stage (multi-stage: `builder` compiles wheels, `runtime` copies them).
- Installs `src/oreoa` as a wheel with pinned `requirements.lock` (pip-tools / uv lock).
### 3.2 `agent`
- `base` + Node.js LTS (from `nodesource` at pinned major, or the official `node:<pin>-bookworm-slim` as a copy source).
- OpenCode installed globally from npm at `OPENCODE_VERSION`; Claude Code (`@anthropic-ai/claude-code`) only under profile `claude-code`.
- `make runtime-config` output baked at build **and** regenerated at container start from the mounted `agents/` and `commands/` (so editing a role prompt does not need a rebuild).
- Entrypoint: renders banner, checks `cases/<id>` exists, exports `HTTPS_PROXY=http://proxy:8888`, execs the runtime TUI in the case directory.
- Also contains the `oreoa` CLI (`/case`, `/ingest`, `/status`… are thin wrappers that the runtime's slash commands call).
### 3.3 `worker-fast`
- `base` + Python: `dissect` (target/evidence/hypervisor/cstruct/…), `zircolite`, `yara-python`, `pyclamd` client, `duckdb`, `pyarrow`, `rq`.
- Binaries from GitHub releases (checksum-verified, pinned in `versions.env`): `hayabusa`, `chainsaw`.
- `clamav-daemon` runs **inside the worker** as a sidecar process under supervisord? No — keep one process per container: `clamd` is a separate service `clamav` on `internal`, workers use `clamdscan --stream`. Database snapshotted at build (`freshclam` in builder stage) and refreshed only by `make update-knowledge`.
- Rule sets are **not** in the image: mounted from `knowledge/upstream/` ro. The image only carries engines.
### 3.4 `worker-deep`
- `worker-fast` + `plaso` (pip, heavy — reason for a separate image), `volatility3` + symbol packs (mounted from `knowledge/`), `capa` and `floss` (release binaries), `diec` (Detect It Easy CLI, Linux release), macOS unified-log parser (`unifiedlog_iterator` from mandiant/macos-UnifiedLogs, built in the builder stage from a pinned tag).
- Same user, same hardening; larger `mem_limit`. `VOLATILITY_SYMBOL_DIRS=/knowledge/upstream/volatility_symbols:/knowledge/custom/volatility_symbols` (ro); `volatility3` remote symbol lookup disabled by config (and unreachable anyway: no egress).
### 3.5 `mcp`
- `base` only. Four entrypoints selected by `command:` in compose. Serve MCP over **streamable HTTP** on `:8000`, bound to the container interface, no auth needed because the network is closed — but every request carries the case id and the server refuses paths outside `cases/<id>`.
### 3.6 `fetcher` (profile `symbol-fetch`)
- `base` + `volatility3` (for `pdbconv`) + `requests`. Runs an RQ worker on queue `fetch` only. Outbound HTTP restricted at two levels: its own egress goes through a second tinyproxy instance (`proxy-fetch`) whose allow-list is hard-coded to `msdl.microsoft.com:443` and `downloads.volatilityfoundation.org:443`, and the code refuses any URL not built from the validated `pdb_name`/`guid`. Writes only under `knowledge/custom/volatility_symbols/`, with a `<file>.provenance.json` (source URL, sha256, job id, confirmed_by, timestamp). Same hardening anchor as every service.
### 3.7 `proxy`
- `tinyproxy` at pinned version on Alpine. `FilterDefaultDeny Yes`, `Filter /etc/tinyproxy/allow.list` generated from `LLM_ENDPOINTS` in `.env` at start; `ConnectPort` limited to 443; `DisableViaHeader Yes`; logs to stdout. A request to a non-listed host is denied and logged (this is what the egress test asserts).

> **Deviation (2026-09-04, arbitrated with the architect, journalized in `docs/journal.md`)**: the Alpine `tinyproxy` package is built **without** the filter module (the `Filter` directive is unavailable, verified in-container). The proxy and proxy-fetch images therefore use **`debian:bookworm-slim`** (digest-pinned in `versions.env`) with Debian's `tinyproxy` (built with filter support). Everything else in this section is unchanged.
## 4. Hardening (applied to every service)
 
```yaml
x-hardened: &hardened
  user: "10001:10001"
  read_only: true
  cap_drop: [ALL]
  security_opt:
    - no-new-privileges:true
    - seccomp:./docker/seccomp/oreoa-default.json
  pids_limit: 512
  tmpfs:
    - /tmp:rw,noexec,nosuid,size=1g
  init: true
  restart: unless-stopped
  logging: {driver: json-file, options: {max-size: "50m", max-file: "5"}}
```
 
Additional per service:
- `worker-*`: `mem_limit`, `cpus` from `.env`; `ulimits: {nofile: 65536, fsize: <cap>}`; `/tmp` sized for archive extraction; `cases/<id>/derived/<EV>/extracted` mounted with `noexec,nosuid,nodev` (declared as a named volume with `o: bind,noexec` or via `tmpfs`-backed scratch + copy).
- `agent`: `/home/oreoa` as tmpfs (runtime caches), writable only `cases/`.
- `proxy`: `cap_drop: [ALL]`, listens on 8888 unprivileged.
- **Nothing** sets `privileged`, `cap_add`, `devices`, `network_mode: host` or mounts `/var/run/docker.sock`. `make lint-compose` fails the build if any appears.
Evidence read-only is enforced twice: the bind mount is `:ro` **and** the ingest code opens files `O_RDONLY` and refuses to run if the evidence directory is writable (defence against a misconfigured compose override).
 
## 5. Volumes and case root
 
- `.env` → `OREOA_CASES=/path/on/host/cases`. Mounted as `/cases` in every service that needs it.
- Per service mount granularity (compose `volumes:` with subpaths):
  - `/cases/<id>/evidence` → `:ro` everywhere.
  - `/cases/<id>/derived` → rw for workers, ro for `mcp-evidence`, absent for `agent` (the agent reads derived data only through MCP).
  - `/cases/<id>/{case.yaml,journal.md,state}` → rw for `mcp-case` and `agent`, **except `state/keys/`**, which is mounted `:ro` into `worker-fast`/`worker-deep` only, rw for the `oreoa` CLI (`/key add` runs in the command layer, not in the agent's MCP path), and absent from every MCP server.
- `knowledge/` → ro everywhere; the upstream snapshot is part of the repo checkout on the host, not of the image.
- Large temporary scratch for workers: `OREOA_SCRATCH` bind (SSD), `noexec`.
## 5b. Redis + RQ operating rules
 
Redis is a buffer, never a source of truth (`manifest.json` and `state/phase.json` are). Configuration:
- `redis-server --save "" --appendonly no --maxmemory 256mb --maxmemory-policy noeviction --protected-mode yes`, data on tmpfs. A restart loses queued jobs; `/ingest` is idempotent and re-enqueues what is missing.
- ACL: one user `rq` restricted to the command set RQ needs (no `CONFIG`, `DEBUG`, `FLUSH*`, `MODULE`, `SCRIPT`); password from a docker secret; default user disabled.
- Reachable only by `mcp-jobs` and the workers (infra test #8).
- RQ: queues `fast` (2 workers, concurrency via two `rq worker` processes in `worker-fast`) and `deep` (1). `job_timeout` per step type set in `packs/<os>/pipeline.yaml` (e.g. hash 10m, extract 60m, plaso 6h, volatility 2h), `result_ttl=600`, `failure_ttl=86400` so `/jobs` can show the failure reason for a day, `job.meta` used for progress, `send_stop_job_command` for `/jobs cancel`. Every job payload is a Pydantic model validated in `mcp-jobs` **before** enqueue (case id, ev_id, step, params; any path outside `cases/<id>` rejected — MCP contract test).
| Mode | Runtime | Path | Config |
|---|---|---|---|
| Remote OpenAI-compatible | OpenCode | `agent → proxy → https://<endpoint>` | `LLM_ENDPOINTS="api.example.com:443"`, key via docker secret `llm_api_key` |
| Anthropic API | Claude Code / OpenCode | same via proxy | `LLM_ENDPOINTS="api.anthropic.com:443"` |
| Local LM Studio / Ollama | either | `agent → host.docker.internal:<port>` (profile `local-llm`) | `NO_PROXY=host.docker.internal`, no egress entry |
 
Per-role models (`LLM_MODEL_ANALYST`, `LLM_MODEL_TRIAGE`, `LLM_MODEL_REVIEWER`) are read by `make runtime-config` and rendered into the runtime config; the banner reads them from the same file. API keys are docker secrets mounted as files, never environment variables in `compose.yaml`.
 
## 7. `versions.env` and `make pins`
 
Single file, one line per pin, consumed by Dockerfiles as `ARG`s and by `make update-knowledge`:
 
```
PYTHON_IMAGE_DIGEST=sha256:…
NODE_MAJOR=…
OPENCODE_VERSION=…
CLAUDE_CODE_VERSION=…
DISSECT_VERSION=…          # pip
PLASO_VERSION=…            # pip
VOLATILITY3_VERSION=…      # pip
ZIRCOLITE_VERSION=…        # pip
HAYABUSA_VERSION=…  HAYABUSA_SHA256=…
CHAINSAW_VERSION=…  CHAINSAW_SHA256=…
CAPA_VERSION=…      CAPA_SHA256=…
FLOSS_VERSION=…     FLOSS_SHA256=…
DIE_VERSION=…       DIE_SHA256=…
UNIFIEDLOGS_TAG=…
TINYPROXY_VERSION=…  REDIS_VERSION=…  CLAMAV_VERSION=…
# knowledge pins (commit sha or tag) — mirrored into knowledge/snapshot.json
DFIQ_COMMIT=…  FORENSIC_ARTIFACTS_COMMIT=…  ATTACK_VERSION=…  SIGMA_COMMIT=…
HAYABUSA_RULES_COMMIT=…  CHAINSAW_RULES_COMMIT=…  YARA_ELASTIC_COMMIT=…  SIGNATURE_BASE_COMMIT=…
LOLBAS_COMMIT=…  GTFOBINS_COMMIT=…  LOOBINS_COMMIT=…  HIJACKLIBS_COMMIT=…  LOLDRIVERS_COMMIT=…  LOLRMM_COMMIT=…
VOL_SYMBOLS_WINDOWS_SHA256=…  VOL_SYMBOLS_MAC_SHA256=…  VOL_SYMBOLS_LINUX_SHA256=…
```
 
`make pins` resolves "latest" to concrete values **interactively**, prints the diff, and writes the file; it is the only tool allowed to edit it. Every release binary is downloaded in a builder stage and verified against its `*_SHA256` before being copied to the runtime stage.
 
## 8. Makefile targets
 
| Target | Does |
|---|---|
| `build` | `docker compose build` all images with BuildKit, `--pull` for base digests |
| `pins` | resolve/refresh `versions.env` (interactive, shows diff) |
| `update-knowledge` | on the host: fetch pinned upstream sources into `knowledge/upstream/`, write `knowledge/snapshot.json`, refresh ClamAV db. **Minimal profile by default.** Options: `--full-symbols` (official Volatility packs), `--nsrl` (curated subset), `--symbol <os> <identifier>` (one ISF on demand: PDB→ISF for Windows, `dwarf2json` guidance for Linux/macOS), `--symbols-for <memory-image>` (identify the kernel first, then the same) |
| `runtime-config` | render `opencode.json`, `.opencode/command/*.md`, `.claude/` from `agents/`, `commands/`, `.env` |
| `up` / `down` | start/stop the stack (`--profile local-llm`, `--profile claude-code` as flags) |
| `shell CASE=<id>` | attach the analyst TUI: `docker compose run --rm agent <id>` |
| `case-new ID=<id>` | create the case skeleton on the host (dirs, `case.yaml`, `journal.md`, permissions 750) |
| `test` | unit + hunt tests on the synthetic corpus (runs inside `worker-fast`) |
| `test-infra` | §9 assertions |
| `lint-compose` | fails if privileged/cap_add/devices/docker.sock/host network appear in the resolved config |
| `sbom` / `scan` | syft SBOM per image, grype/trivy scan, fails on critical CVEs in runtime stages |
| `clean-derived CASE=<id>` | delete `derived/` (rebuildable), never touches `evidence/` |
 
## 9. Infra tests (`tests/infra/`, run by `make test-infra`)
 
1. `docker compose config` contains no `privileged`, `cap_add`, `devices`, `/var/run/docker.sock`, `network_mode: host`.
2. From `worker-fast`: `curl https://example.com` fails (no route); from `agent`: `curl https://example.com` is denied by proxy (403 logged), `curl https://<allowed-endpoint>` reaches the proxy.
3. `touch /cases/<id>/evidence/x` fails in every service (read-only).
4. A script written to `derived/<EV>/extracted/` cannot be executed (`noexec`).
5. All services run as uid 10001; `id -u` ≠ 0 everywhere.
6. Ingest refuses to start if `evidence/` is writable (simulated with an override file).
7. An archive containing `../../etc/passwd` (zip-slip) and a 10 GB→10 KB bomb are rejected with a logged reason.
8. Redis is unreachable from `agent` (only `mcp-jobs` may talk to it).
9. MCP servers refuse a request whose case id does not match their mounted case.
9b. `state/keys/` is not visible from any MCP server container; a planted key string never appears in MCP responses, `journal.md`, `reports/` or `derived/exports/` (grep assertion after a full corpus run).
10. Image SBOM exists for every image and `scan` passes the policy.
11. (profile `symbol-fetch`) From `fetcher`: `curl https://example.com` denied; `curl https://msdl.microsoft.com` reaches `proxy-fetch`; a `fetch_symbol` job without `confirmed_by_analyst=true` or with a malformed GUID is refused before any network call.
## 10. Analyst workflow on the image
 
```
make update-knowledge            # once per snapshot, on the host
make build                       # once per versions.env change
make case-new ID=2026-09-INC-042
cp <archives/images> cases/2026-09-INC-042/evidence/
make up
make shell CASE=2026-09-INC-042  # TUI: banner, /ingest, /status, /triage, /analyse …
```
 
Nothing else is required from the analyst; in particular no `sudo`, no mount, no environment variable beyond `.env`.
 
## 11. Build order (aligned with the work order of the project prompt)
 
1. `base`, `mcp`, `proxy`, `redis`, hardening anchors, `lint-compose`, `test-infra` items 1–5, 8, 9 — **before any forensic tool**, so the security posture is the first thing that exists and cannot regress.
2. `worker-fast` with Dissect + Sigma engines + YARA/ClamAV; `agent` with OpenCode and `runtime-config`. Windows end-to-end milestone runs on this.
3. `worker-deep`; `claude-code` profile.
4. `sbom`/`scan` in CI; release tagging (`oreoa/<image>:<git-tag>`), images exported as a tarball for air-gapped installs (`make export-images`).
## 12. Disk footprint (framework only, evidence excluded)
 
| Profile | Content | Disk |
|---|---|---|
| Minimal (default, analyst) | images (~3.5 GB) + essential `knowledge/` (~1 GB) | ~5 GB |
| Standard | + on-demand symbols (per kernel, MBs) or full packs (~2 GB) + NSRL subset (1–5 GB) | 8–12 GB |
| Developer | + BuildKit cache (4–6 GB, prunable) + corpus (1–3 GB) + agent fixtures | 15–20 GB |
 
`make image-sizes` prints `docker system df -v` per image in CI; `worker-deep` and `knowledge/` are the two lines to watch.
 
## 13. Explicit non-goals
 
No Kubernetes, no Swarm, no web UI, no multi-tenant, no image registry requirement (tarball export covers offline), no GPU passthrough for local LLMs (they run on the host, the stack only talks to them).

