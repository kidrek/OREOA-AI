---
description: Ingest evidence and drive the pipeline (delta rules)
argument-hint: '[--force]'
step: 2
---

Ingest evidence. $ARGUMENTS may contain `--force` (rerun every step).

Compare `evidence/` against `derived/manifest.json` with the delta rules:
new -> process; unchanged -> skip (or rerun failed steps); hash mismatch ->
block + alert; missing -> flag. Enqueue and wait through `mcp-jobs`.
The run is idempotent: a second `/ingest` performs no work. The `ingest`
role writes the journal `### Ingest` section and summarizes coverage and
failures in French; it never reasons about case content.
