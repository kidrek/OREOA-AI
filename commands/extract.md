---
description: Unitary extraction of a path from a disk image
argument-hint: <EV-id> <path>
step: 4
---

Request a unitary extraction of $ARGUMENTS (`<EV-id> <path>`) through
`mcp-jobs extract`. The result lands in `derived/<EV-id>/extracted/` (noexec)
with `extracted_manifest.json` (original path, timestamps, hashes) and the file
enters `files_of_interest`. Report the job and result in French. Full-disk
scans are never performed.
