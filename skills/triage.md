# Skill triage - Phase 1

## Mission

Identifier le type d'affaire, selectionner la collection principale et formuler les hypotheses de travail.

## Procedure

1. Lire le `manifest.yaml` : inventaire des collections disponibles
2. Caracteriser chaque collection (structures, periodes, couverture)
3. Identifier le type d'affaire (intrusion, malware, exfiltration, abus interne, inconnu)
4. Selectionner la collection principale
5. Formuler les hypotheses de travail (notees comme hypotheses)

## Verifications

- [ ] Toutes les collections sont caracterisees
- [ ] Type d'affaire pose (ou marque inconnu)
- [ ] Collection principale identifiee
- [ ] Hypotheses formulees et notees comme hypotheses

## Regles de triage

1. **Perimetre declare** : le scope de l'affaire est pose explicitement
2. **Collection principale d'abord** : la collection la plus riche pour la question posee
3. **Croisement ensuite** : les autres collections confirment ou infirment
4. **Ecart documente** : tout ecart (absence, periode muette) est documenté
5. **Hypotheses explicites** : chaque hypothesis est formulee de facon testable

## Livrable

Section triage du rapport : type d'affaire, collection principale, collections secondaires, hypotheses de travail.

Voir `methodologie/workflow.md` pour le detail des phases.
