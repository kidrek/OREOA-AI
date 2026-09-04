# OREOA-AI - platform v2 (under construction)

OREOA-AI is being rebuilt as a **containerized DFIR agent platform**: raw forensic
collections (Windows, Linux, macOS) are normalized into a queryable model, triage
signals are produced by deterministic tools only, and a role-based agent team
(OpenCode primary runtime, Claude Code alternate) investigates in dialogue with
the analyst.

## State

| Component | Location | Status |
|-----------|----------|--------|
| Specification v4 | `SPEC.md` on branch [`v2`](../../tree/v2) | founding document |
| Platform v2 build | branch `v2` | work order step 1 |
| Legacy DFIR kit v2.1 | tag [`kit-v2.1`](../../releases/tag/kit-v2.1) | frozen - qualified - AGPL-3.0 |

The previous standalone agent kit (image `oreoa-ai-tools:1.1.0`, manifest-based
cases, single-agent `AGENTS.md` contract, disk images exploited without mounting)
remains fully usable from tag `kit-v2.1` and on already-deployed laptops.
It is no longer maintained.

## Licence

AGPL-3.0 - see [LICENSE](LICENSE) and [NOTICE](NOTICE) for third-party components.
