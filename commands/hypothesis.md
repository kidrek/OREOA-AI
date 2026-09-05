---
description: Add, confirm or refute a hypothesis (gated mutation)
argument-hint: add|confirm|refute <H-id> [statement]
step: 3
---

Mutate hypotheses in `case.yaml` through mcp-case. `add` takes a
statement, confidence, ATT&CK ids and stop criteria (what would confirm or
refute). `confirm`/`refute` set the status with the supporting/contradicting
findings. Every mutation requires `confirmed_by_analyst=true` - set only by
this command layer after the analyst's explicit confirmation - and every cited
record_id must resolve, else the write is blocked and journaled as a
hallucination event. Present the resulting state in French.
