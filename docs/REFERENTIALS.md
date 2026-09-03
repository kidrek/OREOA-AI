# Embedded upstream referentials - provenance, traceability, update

The kit embeds two upstream third-party referentials, downloaded and baked into the
image at every build. This document is the reference for their provenance and life
cycle. Upstream definitions are **never modified**; kit adaptations go into
`referentiels-kit/`. French version: [REFERENTIALS.fr.md](REFERENTIALS.fr.md).

| Referential | Source | Content | License |
|-------------|--------|---------|---------|
| ForensicArtifacts | https://github.com/ForensicArtifacts/artifacts | collection definitions per platform (files, registry, WMI), triage groups - 32 YAML files, ~730 definitions | Apache-2.0 |
| DFIQ (Google) | https://github.com/google/dfiq | scenarios -> facets -> investigation questions, approaches, MITRE tags - 6 / 30 / 90 YAML files | Apache-2.0 |

## Inclusion mode

1. **Download at build**: the `Dockerfile` layer runs `scripts/fetch_referentiels.py`
   (ARG `REFERENTIELS_DATE` passed by `doctor fix` at every build -> cache
   invalidation -> guaranteed freshness)
   - ForensicArtifacts: latest release at build time
   - DFIQ: `main` branch (commit read through the GitHub API, branch fallback)
2. **Verification**: SHA256 of every tarball, SHA256 of every extracted file
   (`MANIFEST.sha256` per referential), parsing of every YAML (unnamed definition = failure)
3. **Bake**: `/referentiels/{artifacts,dfiq}/data/` + `MANIFEST.sha256` + upstream
   `LICENSE` + trace in `/referentiels/traces/{artifacts,dfiq}.txt`
   (source, version/commit, tarball hash, build date)
4. **Read-only**: permissions 644/755, non-root analyst user

## Traceability

- **In-image**: traces `/referentiels/traces/` read by `doctor check` (versions + age)
- **Per case**: the manifest receives the `referentials` field at ingestion
  (artifact matching); the report cites the versions (section 2) - every conclusion
  can therefore be tied to the exact referential version
- **Strict reproducibility**: air-gap bundle (`docker save` of the built image) -
  the bundle carries the referentials of its build

## Runtime verification and exploitation

```bash
python3 scripts/doctor.py check        # versions + age (threshold: config/tools.yaml)
python3 scripts/doctor.py test         # MANIFEST integrity + corpus + traces
./scripts/dt python3 /work/scripts/referentiels.py artifacts check   # detailed integrity
./scripts/dt python3 /work/scripts/referentiels.py dfiq check        # integrity + parent links
```

Exploitation: skills `skills/artefacts.md` and `skills/investigation.md`, commands
`artifacts match|expand|index` and `dfiq arbre|plan|index`.

## Update

Automatic at every `python3 scripts/doctor.py fix` (systematic rebuild, cache
preserved: only the referentials layer rebuilds). After a build:

1. Read back the versions displayed by `fix` (digest + referentials)
2. Regenerate the indexes: `artifacts index /work/catalogue/artefacts.md` and
   `dfiq index /work/catalogue/dfiq.md` (the hand-written mapping between markers is preserved)
3. Read back the index diffs and adjust the mappings if upstream evolved
4. Full `doctor test` then commit

## Upstream contributions

A catalogue signal without an artifact, or a DFIQ question without a useful approach,
are candidates for upstream contribution (both projects accept PRs) - journalize as
REX. Meanwhile: kit definitions in `referentiels-kit/` (upstream formats, dedicated
naming), loaded automatically by `scripts/referentiels.py`.
