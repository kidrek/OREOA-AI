# Skill reporting - Phase 6

## Mission

Rediger le rapport final de l'affaire a partir des produits d'analyse, dans la langue
de l'affaire (`case.language` du manifest).

## Langue du rapport

- `case.language` du manifest fait foi (defaut : `language` de `config/tools.yaml`, en)
- Template : `templates/rapport-en.md` (en) ou `templates/rapport.md` (fr)
- Traduction a la demande : si l'analyste demande le rapport dans une autre langue,
  produis-le immediatement dans cette langue et propose de persister `case.language`
  (confirmation puis journalisation)
- Le journal d'affaire suit la meme langue que le rapport

## Formats de rapport

| Format | Usage | Public |
|--------|-------|--------|
| `full` | rapport complet | equipe d'investigation |
| `executive` | resume executif | direction |
| `technique` | details techniques | equipe technique |

## Structure du rapport

Le rapport suit le template selectionne par `case.language` (`templates/rapport-en.md`
ou `templates/rapport.md`) :

1. **Resume executif** -- synthese de l'affaire
2. **Description de l'affaire** -- contexte (dont contexte analyste consigne au manifest, champ `context`), question posee, scenario DFIQ, perimetre, referentiels (versions consignees)
3. **Procedure suivie** -- phases 0-6, collections exploitees, outils utilises
4. **Inventaire des collections** -- collections, hashes, artefacts (referentiel, champ `artifacts`), descriptions
5. **Questions d'investigation** -- structure DFIQ du scenario : facet, question, statut, reponse sourcee (ou ecart)
6. **Actifs affectes** -- systemes, comptes, services
7. **Timeline** -- chronologie consolidee des evenements
8. **Observables** -- tableau des IOC
9. **Hypotheses** -- hypotheses formulees et leur statut
10. **Conclusion** -- reponse a la question posee
11. **Mesures de containment** -- actions prises ou recommandees
12. **Remediation** -- actions correctives
13. **Recommandations de securisation** -- mesures preventives
14. **Annexes** -- details techniques, empreintes, sources

## Verifications de sortie

- [ ] Toutes les conclusions sont sourcees (collection + artefact + empreinte)
- [ ] Le resume executif est present en tete
- [ ] Le contexte analyste est raporte (ou son absence journalisee)
- [ ] Les questions d'investigation DFIQ sont tracees (repondues / sans donnees / non posees)
- [ ] Les hypotheses sont presentes avec leur statut
- [ ] Les observables sont presents dans le tableau final
- [ ] La chaine de conservation est complete

## Lien avec les templates

Le rapport est redige a partir de `templates/rapport.md`. Les observables sont produits a partir de `templates/ioc.md`. La chaine de conservation est produite a partir de `templates/chaine-conservation.md`.
