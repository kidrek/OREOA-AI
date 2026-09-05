---
description: Read-only SQL over the case DuckDB
argument-hint: <sql>
step: 2
---

Run $ARGUMENTS as read-only SQL over `case.duckdb` through mcp-evidence
`query`. Guards: SELECT only, row cap, string truncation, no `raw` column in
results. Show the query (collapsed), then results in French with record_ids
when present. Prefer catalogue hunts when one fits.
