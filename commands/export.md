---
description: One-way export of events (timesketch, csv)
argument-hint: timesketch|csv [EV-id]
step: 5
---

Export `events` one-way to `derived/exports/` per $ARGUMENTS: timesketch
(plaso-compatible JSONL importing cleanly into a stock Timesketch) or csv.
`record_id` travels as a field; the tool never reads anything back. No key
material, no `state/keys/` content, ever. Report row counts and path in
French.
