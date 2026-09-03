# USER-GUIDE - analyst handbook

Daily use of the OREOA-AI kit, once deployment is done. The installation protocol is
in `docs/DEPLOY.md`; this document covers what you do next. French version:
[USER-GUIDE.fr.md](USER-GUIDE.fr.md).

## 1. Daily routine

Launch your agent tool directly in the kit folder:

```bash
opencode        # or claude, or any agent reading AGENTS.md
```

The agent automatically checks tool health (doctor check + test) and welcomes you. At
first launch it displays the quick-start guide (`docs/QUICK-START.md`). If something
is missing (image, model), it guides you step by step without you asking. LLM
connection is handled by your agent tool itself.

What you can ask next:

- open a case: `/case "name"` (create or resume) - section 2
- run the investigation: `/analyse` - section 2
- "Where does case CASE-2026-0042 stand?" (or `/case CASE-2026-0042` to switch)
- "Guide me to capture the RAM of machine Y" (guidance mode, section 5)
- "Produce the case executive summary" (report formats, section 4)
- `/lang fr` : switch the session language

## 2. Open a case and run the investigation

**Normal path (recommended)** - in the agent:

```text
/case "Web server incident 2026-45"
```

The agent scaffolds the tree, asks for the incident context (non-blocking) and gives
you the ID. You then drop your collections into
`cases/<ID>/00_evidence/originals/` - the agent asks for provenance (one line),
hashes (SHA256), matches the artifact referential and journalizes.

Then:

```text
/analyse
```

It runs the full workflow (phases 1 to 6) with validation at every gate.
`/case` alone: case panorama (resume, switch, create another).
`/analyse <path>`: import a collection still outside the case.

**Natural language path** (any agent tool, without custom commands):

```text
> Open a case named "Web server incident 2026-45"
> I dropped my collections into originals, ingest them (source: USB from workstation 12)
> Run the investigation and produce the report
```

> Collections go into `cases/<ID>/00_evidence/originals/` - never modified, always
> hashed. Every scan re-verifies recorded hashes: any drift is an integrity alert.

## 3. Following the investigation

The investigation follows the 7 phases (`methodologie/workflow.md`):

| Phase | What the agent produces | Your role |
|-------|--------------------------|-----------|
| 0. Import | manifest.yaml (types, SHA256, referential artifacts) | provide the collections |
| Opening | incident context request (open question, non-blocking) | share what you know: description, reporter, period, systems, actions taken |
| 1. Triage | recorded context, case type, DFIQ scenario, hypotheses | validate the triage |
| 2-4. Analysis | timeline, correlations, tested hypotheses and DFIQ questions | validate at every gate |
| 5. Observables | IOC table with confidence | validate |
| 6. Report | sourced final report (context + investigation questions) | read and validate |

Every gate: the agent stops, presents its synthesis, waits for your decision. The case
`journal.md` traces every action (append-only, in the case language).

## 4. Getting the report

```text
cases/<ID>/02_analysis/report/rapport.md
```

Structure in 14 sections (executive summary, description with analyst context and DFIQ
scenario, procedure, inventory with artifacts, investigation questions, assets,
timeline, observables, hypotheses, conclusion, containment, remediation,
recommendations, appendices). Every conclusion cites its source (collection + artifact
+ hash). Formats available on request: `full`, `executive`, `technique`. Observables
are also exportable (`02_analysis/ioc/`). Report language follows `case.language` -
`/lang` or a direct request changes it (persistence offered).

## 5. Guidance mode - actions outside the agent's reach

Some actions happen on live machines - the agent then guides you step by step (one
step at a time, ready-to-copy commands, verification of your outputs):

- **RAM capture**: tool per OS, external support, immediate hashing (`connaissances/acquisition/capture-ram.md`)
- **Disk acquisition**: raw/E01 image, write-blocker, hash on both sides (`connaissances/disque/acquisition.md`)
- **Live response**: volatility order, ready-made Windows and Linux commands
- **Kit deployment**: ask `/deploy`

Evidence brought back goes into `00_evidence/` and the investigation resumes in
autonomous mode.

### Disk images (v2.0)

Disk images (raw, dd, E01) are exploited directly, without mounting:

1. drop the image in `00_evidence/originals/` (or `00_evidence/images/` for large
   volumes) - ingestion types it (disk magic disambiguation for `.raw`) and hashes it
2. the agent runs the super-timeline first (`log2timeline` on the image, plaso
   auto-detects partitions), then targeted extraction of artifact paths
   (`referentiels.py artifacts paths` + `disk.py extract`, SHA256 per file)
3. keep 3x the largest image size free before the super-timeline (kit barrier)

Limits documented in the report: AFF4 pending (recorded, not exploited), composite
volumes (LVM/RAID), VSS and encryption out of scope.

## 6. Weak signals and referentials

The agent systematically tests the catalogue signals (`catalogue/windows.md`,
`catalogue/linux.md`, `catalogue/memoire.md`, `catalogue/reseau.md`,
`catalogue/disque.md`) and the correlation chains (`catalogue/correlation.md`). The
report includes a "tested signals" appendix (detected / not detected / not applicable +
evidence) - the basis of analysis reproducibility.

Two upstream referentials are baked into the image at every build (details:
[docs/REFERENTIALS.md](REFERENTIALS.md)):

- **ForensicArtifacts**: every imported collection is automatically matched against
  standard collection definitions (`artifacts` manifest field) - report vocabulary is
  the referential's
- **DFIQ**: the investigation is structured in scenarios/facets/questions - the report
  traces every question (answered, sourced / no data / not in scope)

## 7. Security - what is guaranteed

- `00_evidence/originals/` deposits immutable after import (mounted `:ro` in containers)
- SHA256 of every collection at ingestion, provenance recorded, append-only journal
- Network-less containers; content parsing isolated from the host
- No conclusion without a cited source

## 8. Cheat sheet

| Command | Role |
|---------|------|
| `opencode` / `claude` | launch your agent tool in the kit folder (welcome and self-test automatic) |
| `/case "<name>"` | open a case (creation, context, deposits) |
| `/case` | case panorama (resume, switch, create) |
| `/analyse` | full investigation of the current case (deposits + phases 0-6) |
| `/analyse <collection>` | import an external collection then investigate |
| `/lang fr` / `/lang en` | session language (deliverable persistence offered) |
| `/deploy` | restart deployment guidance |
| `python3 scripts/doctor.py check\|fix\|test` | health / provisioning / qualification |
| `python3 scripts/ingest.py <case> --scan --provenance "source"` | ingest originals/ deposits (integrity verified) |
| `python3 scripts/ingest.py <case> <collection>` | import an external collection (automatic artifact matching) |
| `./scripts/dt python3 /work/scripts/referentiels.py artifacts expand <Name>` | see an artifact's paths and tools |
| `./scripts/dt python3 /work/scripts/referentiels.py artifacts paths <Name>` | machine output: resolved paths (piping to disk.py extract) |
| `./scripts/dt python3 /work/scripts/disk.py info 00_evidence/originals/<image>` | disk image overview (format, partitions, filesystems, barrier) |
| `./scripts/dt python3 /work/scripts/disk.py extract <image> --paths <paths.txt> --out 01_work/disque/extraits` | targeted extraction with SHA256 report |
| `./scripts/dt python3 /work/scripts/referentiels.py dfiq arbre S1008` | question tree of a DFIQ scenario |
| `./install.sh check\|fix\|test` | manual alternative (ops/CI, agent-less) |
