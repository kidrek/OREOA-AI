# Referentiels amont embarques - provenance, tracabilite, mise a jour

Le kit embarque deux referentiels tiers, telecharges et bakes dans l'image a chaque
build. Ce document fait foi sur leur provenance et leur cycle de vie. Les definitions
amont ne sont **jamais modifiees** ; les adaptations kit vont dans `referentiels-kit/`.

| Referentiel | Source | Contenu | Licence |
|-------------|--------|---------|---------|
| ForensicArtifacts | https://github.com/ForensicArtifacts/artifacts | definitions de collecte par plateforme (fichiers, registre, WMI), groupes de triage - 32 fichiers YAML, ~730 definitions | Apache-2.0 |
| DFIQ (Google) | https://github.com/google/dfiq | scenarios -> facets -> questions d'investigation, approches, tags MITRE - 6 / 30 / 90 fichiers YAML | Apache-2.0 |

## Mode d'inclusion

1. **Telechargement au build** : la couche `Dockerfile` execute
   `scripts/fetch_referentiels.py` (ARG `REFERENTIELS_DATE` passe par `doctor fix`
   a chaque build -> invalidation de cache -> fraicheur garantie)
   - ForensicArtifacts : release la plus recente au moment du build
   - DFIQ : branche `main` (commit releve via l'API GitHub, fallback branche)
2. **Verification** : SHA256 de chaque tarball, SHA256 de chaque fichier extrait
   (`MANIFEST.sha256` par referentiel), parsage de chaque YAML (defini sans nom = echec)
3. **Bake** : `/referentiels/{artifacts,dfiq}/data/` + `MANIFEST.sha256` + `LICENSE`
   amont + trace dans `/referentiels/traces/{artifacts,dfiq}.txt`
   (source, version/commit, empreinte tarball, date de build)
4. **Lecture seule** : permissions 644/755, utilisateur analyste non root

## Tracabilite

- **In-image** : traces `/referentiels/traces/` lues par `doctor check` (versions + age)
- **Par affaire** : le manifest recoit le champ `referentiels` a l'ingestion
  (rapprochement artefacts) ; le rapport cite les versions (section 2) - toute
  conclusion peut donc etre rattachee a la version exacte du referentiel
- **Reproductibilite stricte** : bundle air-gap (`docker save` de l'image construite) -
  le bundle embarque les referentiels du build d'origine

## Verification et exploitation a l'execution

```bash
python3 scripts/doctor.py check        # versions + age (seuil : config/tools.yaml)
python3 scripts/doctor.py test         # integrite MANIFEST + corpus + traces
./scripts/dt python3 /work/scripts/referentiels.py artifacts check   # integrite detaillee
./scripts/dt python3 /work/scripts/referentiels.py dfiq check        # integrite + parentes
```

Exploitation : competences `skills/artefacts.md` et `skills/investigation.md`,
commandes `artifacts match|expand|index` et `dfiq arbre|plan|index`.

## Mise a jour

Automatique a chaque `python3 scripts/doctor.py fix` (rebuild systematique, cache
preserve : seule la couche referentiels se reconstruit). Apres un build :

1. Relire les versions affichees par `fix` (digest + referentiels)
2. Regenerer les index : `artefacts index /work/catalogue/artefacts.md` et
   `dfiq index /work/catalogue/dfiq.md` (le mapping redige entre marqueurs est preserve)
3. Relire les diffs des index et ajuster les mappings si l'amont a evolue
4. `doctor test` complet puis commit

## Contributions amont

Un signal du catalogue sans artefact, ou une question DFIQ sans approche utile, sont
des candidats a contribution amont (les deux projets acceptent les PR) - journaliser
en REX. En attendant : definitions kit dans `referentiels-kit/` (formats amont,
noms suffixes `Kit`, ids prefixes `SK`), chargees automatiquement par
`scripts/referentiels.py`.
