---
description: List, create or switch the current case
argument-hint: list | new <id> [--type incident|exercice] | <id>
step: 1
---

Manage cases. $ARGUMENTS selects the action: `list`, `new <id>`, or `<id>` (switch).

- `list`: run `oreoa case list` and present the table in French.
- `new <id>`: if the type is not provided, ask the analyst in French whether
  this is an INCIDENT or an EXERCISE, then run
  `oreoa case new <id> --type <type>`. Report the created skeleton and that
  EXERCICE cases get an `answers.yaml` (score layer only).
- `<id>`: run `oreoa case switch <id>`.

Finish with `oreoa banner`. The banner line opens every analyst-facing turn.
