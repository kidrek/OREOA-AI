---
description: Decryption keys for encrypted evidence (never displayed)
argument-hint: add|list|remove <EV-id> [type] [value|path]
step: 2
---

Manage decryption keys for $ARGUMENTS evidence (`add|list|remove`).

- `add <EV-id> <type> <value|path>` (types: password, recovery_key, bek,
  keyfile, clear): store in `state/keys/<EV-id>.yaml` (mode 0600), then
  re-enqueue the `unlock` step (mcp-jobs unlock). Success or failure is a
  manifest status; the key value is never echoed back, never journaled, never
  exported, never present in any MCP result.
- `list`: show evidence ids and key types only - never values.
- `remove <EV-id>`: delete the stored key file.

If unlock cannot proceed (TPM-only protector without recovery key, LUKS
without passphrase/keyfile, FileVault without password), say so in French and
state the documented alternatives (live collection, memory image for FVEK
recovery - best effort).
