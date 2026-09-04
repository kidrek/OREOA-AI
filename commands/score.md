---
description: Score an EXERCICE case against its answers (command layer only)
argument-hint: '[--nl]'
step: 5
---

EXERCICE cases only: read `answers.yaml` (ground truth) at the command
layer - this file is never mounted into any MCP server and never readable by
any role - and compare against the case state: precision, recall, invented
items (things present in the case state that answers.yaml does not contain).
With `--nl`: run the 20-question NL-to-SQL benchmark against expected result
sets. Results append to `evaluation/history.jsonl` (model, endpoint, snapshot,
git sha); regressions beyond `evaluation/thresholds.yaml` fail the run.
For an INCIDENT case: refuse in French.
