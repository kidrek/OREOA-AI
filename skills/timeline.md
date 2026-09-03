# Skill timeline - consolidation de la chronologie

## Mission

Produire et tenir la timeline consolidee de l'affaire : fusion horodatee des evenements issus de toutes les collections, chaque entree sourcee, dans `02_analysis/timeline/timeline.md`.

## Sources par collection

| Collection | Evenements | Outil |
|-----------|------------|-------|
| journaux Windows (evtx/jsonl) | authentification, execution, services, effacement | log2timeline/psort, lecture directe |
| registre (ruches) | persistance, USB, executions utilisateur | regipy |
| journaux Linux (auth.log, syslog, wtmp) | connexions, sudo, cron, purge | lecture directe |
| memoire volatile | processus vivants, connexions actives, consoles | volatility3 (v1.1) |
| capture reseau | resolutions DNS, connexions, transfers | tshark + suricata (v1.2) |

## Regles

1. **Un evenement = une ligne** : horodatage (UTC si possible), actif, description, source complete (collection + artefact + empreinte) - l'artefact cite le nom standard du referentiel (champ `artefacts` du manifest)
2. **Normalisation horaire** : toutes les horloges converties en un seul referentiel ; les decalages d'horloge observes sont documentes, jamais corrigees silencieusement
3. **Periodes couvertes explicites** : la timeline porte les bornes de chaque collection (debut/fin) ; une periode sans source est un ecart, pas un silence innocents
4. **Grain honnete** : un evenement RAM (instantane) ne se melange pas a un evenement journal (continu) sans mention du grain
5. **Edition append-only** : la timeline se construit par phases ; chaque modification majeure est journalisee dans `journal.md`

## Procedure

1. Extraire les evenements de la collection principale (triage, phase 1)
2. Extraire les evenements des collections secondaires au fil des phases 2-4
3. Fusionner et trier chronologiquement
4. Marquer les chaines de correlation (C-W, C-L, C-M, C-R) au fil des maillons confirmes
5. Documenter les ecarts : periodes muettes, horloges douteuses, evenements attendus absents
6. Verifier les criteres de sortie de chaque phase (methodologie/workflow.md)

## Fichier produit

| Fichier | Contenu |
|---------|---------|
| `02_analysis/timeline/timeline.md` | timeline consolidee (table chronologique + ecarts + sources) |

## Lien avec les catalogues

Les chaines de correlation structurent la lecture de la timeline : `catalogue/correlation.md` (C-W-01/02, C-L-01/02, C-M-01, C-R-01, R-01 a R-09). Les signaux sources : `catalogue/windows.md`, `catalogue/linux.md`, `catalogue/memoire.md`, `catalogue/reseau.md`.
