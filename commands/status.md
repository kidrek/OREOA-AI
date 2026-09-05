---
description: 'Current case state: phases, gaps, detections, hypotheses'
argument-hint: ''
step: 2
---

Report the current state, opening with the banner line.

Compose from: `state/phase.json` and `derived/manifest.json` (via MCP reads),
`mcp-jobs` running/queued jobs, `case.yaml` hypotheses and gaps (mcp-case
read), top detections by score. Present in French: a compact phase table per
evidence, running jobs, gaps with status, top 5 signals, open hypotheses.
