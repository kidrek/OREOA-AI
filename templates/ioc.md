# Template ioc.md - tableau des observables

# Observables - <ID>

Affaire : <nom>
Date : <date>

## Observables confirms

| Type | Valeur | Contexte | Source | Confiance |
|------|--------|----------|--------|-----------|
| ip | <valeur> | <contexte> | <collection + artefact> | <niveau> |
| compte | <valeur> | <contexte> | <collection + artefact> | <niveau> |
| fichier | <valeur> | <contexte> | <collection + artefact> | <niveau> |
| hash | <valeur> | <contexte> | <collection + artefact> | <niveau> |
| domaine | <valeur> | <contexte> | <collection + artefact> | <niveau> |

## Hypotheses non conclues

| Type | Valeur | Contexte | Source | Raison non conclue |
|------|--------|----------|--------|-------------------|
| <type> | <valeur> | <contexte> | <collection + artefact> | <raison> |

---

## Regles

1. Chaque observable cite sa source (collection + artefact + empreinte)
2. La confiance est declaree : elevee, moyenne, faible
3. Les hypotheses non conclues sont presentees separement, jamais confondues avec les confirms
