# Skill artefacts - exploitation du referentiel ForensicArtifacts

## Mission

Exploiter le referentiel d'artefacts bake dans l'image pour rattacher les collections
aux definitions standard, guider la collecte et citer les sources en vocabulaire amont
dans les rapports.

## Referentiel

- Definitions amont : bakes dans l'image (`/referentiels/artifacts/data`) a chaque build
  (`doctor fix`) - release la plus recente, jamais editee localement
- Definitions kit : `referentiels-kit/artifacts/*.yaml` (monte en ro par `dt`,
  suffixe de nom `Kit`) - artefacts specifiques au SI analyse
- Versions : trace in-image `/referentiels/traces/artifacts.txt` et champ `referentiels`
  du manifest d'affaire (consigne a l'ingestion)
- Index lisible + mapping signaux : `catalogue/artefacts.md` (regenere apres build,
  mapping redige preserve entre marqueurs)

## Commandes (execution conteneurisee via dt)

```bash
dt python3 /work/scripts/referentiels.py artefacts match  <manifest>     # rapprochement collections
dt python3 /work/scripts/referentiels.py artefacts expand <NomArtefact>  # sources resolues + outils
dt python3 /work/scripts/referentiels.py artefacts index  /work/catalogue/artefacts.md
dt python3 /work/scripts/referentiels.py artefacts check                  # integrite
```

Le rapprochement `match` est automatique a chaque `ingest.py` (champ `artefacts`
par collection). Regle de precision sur fichiers isoles (sans arborescence OS) :

- base de pattern **exacte ou prefixee** (`auth.log`, `auth*`, `u_ex*.log`) -> rapprochement
- base **generique** a prefixe wildcard (`*.log`, `*.*`) -> rapprochee seulement si
  l'extension est specifique (`.evtx`, `.pcap`, `.pcapng`, `.reg`, `.e01`, `.aff4`) ;
  pour les extensions banales (.log, .json...), le pattern generique est ignore
  (trop ambigu hors arborescence) - les chemins exacts restent visibles via `expand`
- un nom de collection ne matchant aucune definition est un signal d'acquisition
  atypique, pas une erreur

## Usage par phase

- **Phase 0 (import)** : rapprochement automatique ; verifier la presence du champ
  `referentiels` (tracabilite des versions utilisees)
- **Phase 1 (triage)** : couverture - artefacts attendus pour le scenario vs presents ;
  les absents fondent le plan d'acquisition complementaire (mode guidance)
- **Phases 2-5 (analyse)** : `expand <NomArtefact>` donne les chemins resolus et les
  outils kit par type de source (FILE/PATH -> log2timeline, fls/icat ; REGISTRY_KEY ->
  regipy) ; les journaux exporthes (evtx/jsonl) s'analysent par les skills dedies
- **Phase 6 (rapport)** : citer les noms d'artefacts standard dans l'inventaire des
  collections (section 4) et chaque conclusion

## Regles

1. Le referentiel decrit **ou collecter**, pas comment detecter : la logique de
   detection reste dans les catalogues SF et les chaines de correlation
2. Un artefact reference par un signal du catalogue mais absent de la collecte est un
   **ecart** documente - jamais une preuve d'absence de compromission
3. Ne jamais modifier l'amont : un besoin local va dans `referentiels-kit/artifacts/`
   (format amont, nom suffixe `Kit`) ; un signal du catalogue sans artefact correspondant
   est un candidat a contribution amont (PR) - journaliser en REX
4. Toute manipulation d'affaire reste tracee dans `journal.md` (commande exacte + cible)
