---
description: Append an analyst note to the journal
argument-hint: <text>
step: 3
---

Append $ARGUMENTS as an entry to the `### Notes` section of journal.md
(append-only, timestamped UTC, signed `[human]` if the analyst wrote it or
`[analyst]` if you summarize). One entry = one fact or decision. Then rewrite
the current-state block if the note changes it.
