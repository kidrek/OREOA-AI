# Skill analyse - Phases 2 a 5

## Mission

Analyser les collections, identifier les actifs affectes, consolider la timeline, tester les hypotheses et produire les observables.

## Phases couvertes

| Phase | Nom | Produit |
|-------|-----|---------|
| 2 | Analyse initiale | actifs affectes, chronologie initiale |
| 3 | Correlation | croisement multi-collections, timeline consolidee |
| 4 | Investiguer | hypotheses testees, ecarts explores |
| 5 | Observer | tableau des observables (IOC) |

## Regles

1. Toute analyse s'effectue sur des copies, jamais sur les originals
2. Chaque evenement de la timeline cite sa source (collection, artefact, empreinte)
3. Chaque conclusion est sourcee : collection + artefact + empreinte
4. Les hypotheses non validees sont presentees comme hypotheses, jamais comme conclusions
5. Les ecarts (periodes muettes, evenements attendus absents) sont documentes

## Produits attendus

1. **Timeline consolidee** : evenements horodates, sourcés, ordonnés
2. **Actifs affectes** : systemes, comptes, services identifies
3. **Hypotheses** : formulees, testees, validees, invalidees ou non conclues
4. **Observables** : tableau final (type, valeur, contexte, source, confiance)

## Fichiers produits

| Fichier | Contenu |
|---------|---------|
| `02_analysis/timeline/timeline.md` | timeline consolidee |
| `02_analysis/ioc/ioc.md` | tableau des observables |
| `02_analysis/logs/analyse.md` | journal d'analyse |

## Lien avec le catalogue

Les signaux faibles detects lors de l'analyse sont croises avec `catalogue/` :

- `catalogue/windows.md` -- signaux Windows
- `catalogue/linux.md` -- signaux Linux
- `catalogue/correlation.md` -- regles de correlation multi-signaux
