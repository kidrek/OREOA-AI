---
description: 'Pipeline jobs: queued, running, failed (with reasons)'
argument-hint: ''
step: 2
---

List pipeline jobs through `mcp-jobs` (`status`): id, queue (fast|deep),
step, state, duration. Failures show their failure reason (kept 24h by
`failure_ttl`). French output, one line per job.
