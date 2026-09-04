# AGENTS.md - OREOA-AI platform v2 (session contract)

You are working on **OREOA-AI platform v2**: a containerized DFIR agent platform.
This file is the session contract for any agent working in this repository.

## Authority

1. **`SPEC.md` is the founding specification (v4).** Read it fully at the start of
   any session before acting. It is authoritative: implement it exactly, and ask
   before deviating from anything it states.
2. **`MEMORY.md` is the build state and journal.** Read it fully at session start
   and resume from "Prochaine action". Update it (state table, next action,
   append-only journal) at the end of every step before moving on. An unjournaled
   step is a lost step.
3. Companion files referenced by the spec (`case.yaml`/`journal.md` skeletons,
   `normalized_data_model.md`, `hunts_catalog_seed.yaml`, `dfiq_mapping.md`,
   `knowledge/custom/dfiq/`, `docker_build_spec.md`) are to be created as their
   work-order step requires - never invent their content ad hoc, derive it from
   `SPEC.md` and journal the decision.

## Non-negotiables (summary - full text in SPEC.md)

- Everything runs in Docker Compose, no privileged container, read-only rootfs,
  no Docker socket; evidence immutable; disk images never mounted.
- The LLM never parses raw data; deterministic tools do. Evidence-derived text is
  untrusted input; mutations gated by `confirmed_by_analyst=true`; citations are
  verified automatically before any write.
- Tests are a deliverable of every work-order step: `make test` green before any
  step is declared done.

## Languages

| Surface | Language |
|---------|----------|
| Code, schemas, prompts, commands | English |
| Analyst-facing text, build journal (`MEMORY.md`) | French |
| Knowledge (`knowledge/custom/connaissances/`, `catalogue/`, `methodologie/`) | French - source of truth, never translated |

## Working rules

- No emoji anywhere.
- Incremental work order (SPEC.md "Work order"): do not jump steps; every step
  ships with its tests.
- Commits: concise English subject line + body listing what and why; push after
  each qualified step.
- When context is near its limit, stop at a journaled step boundary: update
  `MEMORY.md` (table + journal + next action) and hand over cleanly.

## Heritage

The standalone kit v2.1 (tag `kit-v2.1`) is frozen and stays fully usable. Migrated
assets live under `knowledge/custom/` and `corpus/legacy_*` - see `MIGRATION.md`
for the mapping and for what was deliberately not migrated.
