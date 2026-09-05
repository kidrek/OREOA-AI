---
description: Full-text search (FTS BM25, regex, ILIKE) across the case
argument-hint: <pattern>
step: 2
---

Search $ARGUMENTS via mcp-evidence `search` (FTS BM25 on events.summary
plus regex/ILIKE on path_norm, cmdline, message, url, value_data; capped).
Present hits grouped by family with ts, host, record_id. Use `get_raw` only
when the analyst asks and the case type allows it (capped at 20 records).
