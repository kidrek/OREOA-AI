---
description: Show or change the per-role model configuration
argument-hint: '[analyst|triage|reviewer] <model>'
step: 3
---

With no argument: show the per-role models (LLM_MODEL_ANALYST,
LLM_MODEL_TRIAGE, LLM_MODEL_REVIEWER) and the endpoint from the environment,
plus the knowledge snapshot in use. With arguments: record the new model in
the session (mcp-case, gated) and tell the analyst to run
`make runtime-config` (host) to apply it to the runtime config. French output.
