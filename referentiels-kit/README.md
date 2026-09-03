# referentiels-kit - espaces custom du kit OREOA-AI

Ce dossier contient les definitions **ecrites par le kit** (analyste ou agent),
a cote des referentiels amont bakes dans l'image (`/referentiels/`). Les fichiers
amont ne sont jamais modifies : toute adaptation locale va ici.

## Contenu attendu

| Sous-dossier | Format | Usage |
|--------------|--------|-------|
| `artifacts/` | definitions d'artefacts au format ForensicArtifacts (sources, conditions, supported_os) | artefacts specifiques au SI analyse (chemins applicatifs internes, journaux proprietaires) |
| `dfiq/` | scenarios, facets, questions au format DFIQ (id, name, parent_ids, approaches) | questions d'investigation kit et approches detaillees manquantes dans le corpus amont |

## Regles

1. Les definitions kit suivent le format amont exact (nom, doc, sources / id, parent_ids) pour que `scripts/referentiels.py` les charge sans distinction ; elles sont marquees par l'origine `kit` dans les sorties de l'outil
2. Les sids/id kit ne doivent pas entrer en collision avec l'amont : prefixer les id DFIQ kit par `SK` (ex. `SK1001`) et suffixer les noms d'artefacts kit par `Kit` (ex. `EriInternalLogsKit`)
3. Les espaces kit sont montes en read-only par `dt` (`/referentiels-kit/`) ; l'amont reste dans l'image
4. Mise a jour du referentiel amont = rebuild (doctor fix) - jamais d'edition locale de l'amont

## Chargement

`scripts/referentiels.py` charge automatiquement `/referentiels` (amont, in-image)
et `/referentiels-kit` (custom, monte par `dt`). Un artefact ou une question kit
apparaissent dans les sorties avec la mention `[kit]`.
