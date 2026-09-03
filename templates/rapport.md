# Template rapport d'affaire

Structure standard du rapport d'affaire. Chaque section est obligatoire ; une section non applicable est marquee "non applicable (motif)".

---

```markdown
# Rapport d'investigation -- <ID>

Affaire : <nom>
Periode : <debut> -- <fin>
Date : <date du rapport>
Format : <full | executive | technique>

## 1. Resume executif

<synthese de l'affaire en 5-10 lignes : ce qui s'est passe, actifs affectes,
conclusion principale, mesures recommandées>

## 2. Description de l'affaire

- Contexte : <contexte de l'affaire>
- Contexte analyste : <synthese de la section `contexte` du manifest (declarant, signalement, periode, systemes, mesures deja prises) - ou "aucun contexte fourni a l'ouverture">
- Question posee : <question initiale de l'investigation>
- Scenario DFIQ : <id - nom> (axes : <facets explores>)
- Perimetre : <scope declare au triage>
- Referentiels : ISO 27037, ISO 27035, ISO 27043, NIST SP 800-86 ; referentiels amont : ForensicArtifacts <version>, DFIQ <commit> (consignes dans le manifest, champ `referentiels`)

## 3. Procedure suivie

| Phase | Actions | Collections exploitees | Outils |
|-------|---------|------------------------|--------|
| 0. Import | scan, empreintes | <collections> | <outils> |
| 1. Triage | typage, principal | <collections> | <outils> |
| ... | ... | ... | ... |

## 4. Inventaire des collections

| Collection | Type | SHA256 | Artefacts (referentiel) | Description |
|-----------|------|--------|-------------------------|-------------|
| <nom> | <type> | <hash> | <noms d'artefacts ou -> | <description> |

## 5. Questions d'investigation

Structure DFIQ du scenario (skills/investigation.md). Toute question sans donnees est
presentee comme ecart, jamais resolue par speculation.

| Facet | Question | Statut | Reponse (sourcee) |
|-------|----------|--------|-------------------|
| <F-id> | <Q-id - nom> | repondue / sans donnees / non posee | <reponse + collection + artefact + hash ou motif d'ecart> |

## 6. Actifs affectes

| Actif | Type | Rôle | Source |
|-------|------|------|--------|
| <nom> | systeme | <role> | <collection> |

## 7. Timeline

| Horodate | Evenement | Source (collection + artefact + empreinte) |
|----------|----------|--------------------------------------------|
| <ts> | <evenement> | <source> |

## 8. Observables

| Type | Valeur | Contexte | Source | Confiance |
|------|--------|----------|--------|-----------|
| <type> | <valeur> | <contexte> | <source> | <niveau> |

## 9. Hypotheses

| Hypothesis | Statut | Sources |
|-----------|--------|---------|
| <hypothesis> | validee / invalidee / non conclue | <sources> |

## 10. Conclusion

<reponse a la question posee, chaque affirmation sourcee>

## 11. Mesures de containment

<actions prises ou recommandees, horodatees>

## 12. Remediation

<actions correctives, horodatees>

## 13. Recommandations de securisation

<mesures preventives, par priorite>

## 14. Annexes

- Empreintes completes : voir manifest.yaml
- Journal d'actions : voir journal.md
- Details techniques : <references>
```

---

## Regles de redaction

1. Chaque affirmation du resume executif est detaillee dans le corps
2. Chaque conclusion cite sa source (collection + artefact + empreinte)
3. Les hypotheses sont presentees avec leur statut, jamais comme conclusions
4. Les observables sont presents dans le tableau final, avec leur confiance
