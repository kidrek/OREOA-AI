---
description: 'Volatility symbols on demand: identifier + ready-to-paste command'
argument-hint: <EV-id>
step: 4
---

For memory evidence $ARGUMENTS, show the required kernel identifier
(Windows: PDB name + GUID; Linux: banner; macOS: version/KDK id) from the
manifest, then print the ready-to-paste workstation command from a template:
`make update-knowledge --symbol <os> <identifier>` (air-gapped command mode).
Under profile `symbol-fetch`, offer the gated `fetch_symbol` job instead - it
requires explicit analyst confirmation (confirmed_by_analyst=true) and only
the kernel GUID leaves the machine. A missing symbol is a gap
(`symbols_required`), never a crash.
