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
- Question posee : <question initiale de l'investigation>
- Perimetre : <scope declare au triage>
- Referentiels : ISO 27037, ISO 27035, ISO 27043, NIST SP 800-86

## 3. Procedure suivie

| Phase | Actions | Collections exploitees | Outils |
|-------|---------|------------------------|--------|
| 0. Import | scan, empreintes | <collections> | <outils> |
| 1. Triage | typage, principal | <collections> | <outils> |
| ... | ... | ... | ... |

## 4. Inventaire des collections

| Collection | Type | SHA256 | Description |
|-----------|------|--------|-------------|
| <nom> | <type> | <hash> | <description> |

## 5. Actifs affectes

| Actif | Type | Rôle | Source |
|-------|------|------|--------|
| <nom> | systeme | <role> | <collection> |

## 6. Timeline

| Horodate | Evenement | Source (collection + artefact + empreinte) |
|----------|----------|--------------------------------------------|
| <ts> | <evenement> | <source> |

## 7. Observables

| Type | Valeur | Contexte | Source | Confiance |
|------|--------|----------|--------|-----------|
| <type> | <valeur> | <contexte> | <source> | <niveau> |

## 8. Hypotheses

| Hypothesis | Statut | Sources |
|-----------|--------|---------|
| <hypothesis> | validee / invalidee / non conclue | <sources> |

## 9. Conclusion

<reponse a la question posee, chaque affirmation sourcee>

## 10. Mesures de containment

<actions prises ou recommandees, horodatees>

## 11. Remediation

<actions correctives, horodatees>

## 12. Recommandations de securisation

<mesures preventives, par priorite>

## 13. Annexes

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
