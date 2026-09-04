# OREOA-AI - plateforme v2 (en construction)

OREOA-AI est reconstruit en **plateforme d'agent DFIR conteneurisee** : les
collections forensiques brutes (Windows, Linux, macOS) sont normalisees en un
modele requetable, les signaux de triage sont produits par des outils
deterministes uniquement, et une equipe d'agents par roles (runtime principal
OpenCode, alternatif Claude Code) conduit l'investigation en dialogue avec
l'analyste.

## Etat

| Composant | Emplacement | Statut |
|-----------|-------------|--------|
| Specification v4 | `SPEC.md` sur la branche [`v2`](../../tree/v2) | document fondateur |
| Construction plateforme v2 | branche `v2` | etape 1 du work order |
| Kit DFIR legacy v2.1 | tag [`kit-v2.1`](../../releases/tag/kit-v2.1) | gele - qualifie - AGPL-3.0 |

Le kit agentique autonome precedent (image `oreoa-ai-tools:1.1.0`, affaires par
manifest, contrat `AGENTS.md` mono-agent, images disque exploitees sans montage)
reste pleinement utilisable depuis le tag `kit-v2.1` et sur les laptops deja
deployes. Il n'est plus maintenu.

## Licence

AGPL-3.0 - voir [LICENSE](LICENSE) et [NOTICE](NOTICE) pour les composants tiers.
