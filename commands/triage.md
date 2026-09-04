---
description: Produce the triage brief for an evidence
argument-hint: <EV-id>
step: 2
---

Run the triage workflow for the evidence $ARGUMENTS via the `triage` role:
default pack hunts (mcp-jobs), `rank_signals`, then write
`derived/triage/<EV-id>_brief.md` (top 10 signals ordered by score, coverage
gaps, 2-3 candidate hypotheses with confidence). The `triage` role writes the
journal `### Triage` section. Summarize the brief in French with score factors.
Triage never promotes anything.
