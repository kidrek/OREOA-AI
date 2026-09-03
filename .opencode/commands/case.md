---
description: Open, switch or list investigation cases
---
Case management: $ARGUMENTS

## Behavior per argument

### A. Name or identifier provided (`/case "Web server incident"` or `/case CASE-2026-0042`)

**Search for an existing case** (by exact id, then by name):
- single match -> **switch**: load the full case state (`manifest.yaml`: status,
  collections + artifacts, context; `journal.md`: latest entries; current phase per
  `methodologie/workflow.md`; products in `02_analysis/`) and present a **resume
  brief**: id, name, status, what was done, current phase, next step. The case becomes
  the **current case of the session** (logical anchor: subsequent commands - ingest,
  dt, analyses - apply to it, run from the kit root with its explicit ID; never a
  physical `cd` into the case directory)
- several matches -> candidate table (id + name + status) and ask which one
- none -> **creation** (below), with confirmation if the argument looks like something
  else (path, question...)

**Creation**: scaffold the case without any script, exactly like this:
1. `ID` = CASE-<year>-<free 4-digit number> (scan `cases/`)
2. `mkdir -p "cases/<ID>"/{00_evidence/{originals,exports,images},01_work/tmp,02_analysis/{logs,ioc,report}}`
3. Write `cases/<ID>/manifest.yaml` (schema EN, kit contract):

```yaml
case:
  id: "<ID>"
  name: "<name>"
  created: "<today>"
  status: open
  language: en            # default from config/tools.yaml `language`; deliverables + journal follow it

context:
  description: ""
  reported_by: ""
  reported_at: ""
  systems: []
  suspected_period: { start: "", end: "" }
  actions_taken: []
  constraints: []

collections: []
```

4. Write `cases/<ID>/journal.md` in the case language (default English): title
   `# Journal - <ID>`, case + date, `## Phase 0 - Import` section with the timestamped
   creation entry
5. Report the assigned ID clearly. The created case becomes the current case of the session

Do not ask the language: apply the default (config `language`, English) - the analyst
can request a translation at any time; offer then to persist it in `case.language`.

### B. After creation or switch (in both cases)

1. **Context intake** (only if `context` is empty): ask the analyst whether they have
   context to share about the incident - open question, targeted follow-ups if provided
   (description, reported_by, period, systems, actions already taken, constraints),
   non-blocking if nothing (journalize "no context provided"). Record in the `context`
   section of the manifest + journal entry
2. **Deposit detection**: list the content of `00_evidence/originals/`:
   - files present not yet recorded in the manifest -> ask for the **provenance** (one
     line: where the collections come from, who copied them) then propose
     `python3 scripts/ingest.py cases/<ID> --scan --provenance "<declared source>"`
   - already recorded -> remind they are ingested (the scan re-verifies their integrity)
3. Close the turn: case state + THE command to investigate once the collections are
   deposited: `/analyse` (or `/analyse <path>` for a collection outside the case)

### C. No argument (`/case`)

**Case panorama**: table read from `cases/*/manifest.yaml`
(id, name, status, date, collection count, context filled or not)
then propose: switch to one (choice -> A-switch behavior) or create a new one.
If `cases/` is empty: present the quick-start guide `docs/QUICK-START.md` and propose
creating the first case.

## Rules

- One current case per session; switching happens anytime with a new `/case`
- Never write into `00_evidence/originals/` (deposits come from the analyst)
- Every creation/switch/scan is journalized in `journal.md` (append-only, timestamped)
