# knowledge/custom/ - definitions internes de la plateforme

Definitions **ecrites par la plateforme OREOA-AI v2** (analyste ou agent), a cote
des sources de connaissance amont pincees (`knowledge/upstream/`, alimentees par
`make update-knowledge`). Les fichiers amont ne sont jamais modifies : toute
adaptation locale va ici.

## Organisation (heritage kit v2.1, a restructurer au fil du work order)

| Dossier | Contenu | Origine kit v2.1 |
|---------|---------|------------------|
| `artifacts/` | definitions d'artefacts kit au format ForensicArtifacts | `referentiels-kit/` (README de conventions conserves ci-dessous) |
| `dfiq/` | objets DFIQ internes (scenarios, facets, questions) | `referentiels-kit/dfiq/` |
| `connaissances/` | base analytique FR (acquisition, memoire, reseau, disque, navigateurs) | `connaissances/` |
| `catalogue/` | signaux faibles SF (66) + chaines de correlation (9) + index generes | `catalogue/` |
| `methodologie/` | workflow 7 phases ISO, arbres de decision, referentiels | `methodologie/` |

## Regles (conventions kit v2.1, reprises par la spec v4)

1. Les definitions kit suivent le format amont exact pour etre chargees sans
   distinction par `mcp-knowledge` ; elles sont marquees internes et jamais
   exportees comme "DFIQ officiel"
2. Collisions : artefacts kit prefixes `custom:` (spec v4 : `custom:<name>`,
   definition dans `knowledge/custom/artifacts/`) ; objets DFIQ internes dans la
   plage `S0xxx`/`F0xxx`/`Q0xxx` avec `is_internal=True` (spec v4 - l'ancienne
   convention kit `SK`/suffixe `Kit` reste documentee pour lecture de l'historique)
3. Discipline de vocabulaire (spec v4) : les valeurs `artifact` proviennent de
   `forensic_artifacts` ou sont `custom:<name>` ; les `technique_ids` viennent de
   `attack` ; les `dfiq_question_ids` de `dfiq` + plage interne - toute valeur hors
   de ces ensembles est une erreur, pas un avertissement
4. `knowledge/custom/connaissances/` est en FR (langue source de la connaissance,
   regle reprise du kit v1.4) ; references kit legacy (dt, doctor, manifest) a
   relire lors de la restructuration en packs OS

## Anciennes conventions (referentiels-kit, conservees pour lecture)

- Artefacts custom : format ForensicArtifacts (`sources`, `conditions`,
  `supported_os`), nommage suffixe `Kit` (ex. `EriInternalLogsKit`) - a convertir
  en prefixe `custom:` lors de la migration vers les packs OS
- DFIQ custom : format DFIQ (`id`, `name`, `parent_ids`, `approaches`), ids
  prefixes `SK` (ex. `SK1001`) - a convertir dans la plage interne `Q0xxx`
- Chargement : l'ancien `scripts/referentiels.py` (kit v2.1, tag `kit-v2.1`)
  chargeait amont + custom ; la plateforme v2 fait l'equivalent via `mcp-knowledge`
