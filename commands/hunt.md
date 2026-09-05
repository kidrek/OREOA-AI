---
description: List or run a catalogue hunt (SQL over DuckDB)
argument-hint: list | <H-id> [params]
step: 2
---

With `list`: show the hunt catalogue (mcp-evidence `hunt_list`) filtered
by OS, with DFIQ question ids. With a hunt id: show its header (title, DFIQ,
ATT&CK, OS, params), collect missing params, run it via `hunt_run`. Results go
to `detections` (engine=hunt); present the top rows with matched_record_ids in
French. Hunts are re-runnable (delete-then-insert by rule_id).
