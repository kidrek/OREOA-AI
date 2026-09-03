# Skill triage - Phase 1

## Mission

Identifier le type d'affaire, selectionner la collection principale et formuler les hypotheses de travail.

## Procedure

1. Lire le contexte consigne : section `contexte` du manifest (intake analyste a
   l'ouverture via /analyse). Si aucun contexte n'est consigne, rappeler a l'analyste
   qu'il peut en fournir - sans bloquer (l'absence est journalisee)
2. Lire le `manifest.yaml` : inventaire des collections, champ `artefacts` (rapprochement
   referentiel) et `referentiels` (versions)
3. Caracteriser chaque collection (structures, periodes, couverture)
4. Identifier le type d'affaire (intrusion, malware, exfiltration, abus interne, inconnu)
   puis le scenario DFIQ correspondant (mapping : catalogue/dfiq.md ; commandes :
   `dt ... referentiels.py dfiq arbre <S-id>`) - si aucun scenario ne correspond, le
   dire explicitement et travailler par catalogue SF
5. Verifier la couverture : artefacts attendus pour le scenario vs collections presentes
   (champ `artefacts` du manifest) - les artefacts absents sont un plan d'acquisition
   complementaire (mode guidance : skills/deploiement.md et connaissances/acquisition/)
6. Selectionner la collection principale
7. Formuler les hypotheses de travail (notees comme hypotheses) en t'appuyant sur le
   contexte, le scenario DFIQ et ses facets

## Verifications

- [ ] Contexte analyste consigne au manifest, ou absence journalisee
- [ ] Toutes les collections sont caracterisees
- [ ] Type d'affaire pose (ou marque inconnu)
- [ ] Scenario DFIQ selectionne (ou hors corpus, dit explicitement)
- [ ] Couverture artefacts evaluee (presentes / absentes = plan d'acquisition)
- [ ] Collection principale identifiee
- [ ] Hypotheses formulees et notees comme hypotheses

## Regles de triage

1. **Perimetre declare** : le scope de l'affaire est pose explicitement
2. **Collection principale d'abord** : la collection la plus riche pour la question posee
3. **Croisement ensuite** : les autres collections confirment ou infirment
4. **Ecart documente** : tout ecart (absence, periode muette, artefact non collecte) est documente
5. **Hypotheses explicites** : chaque hypothesis est formulee de facon testable
6. **Scenario trace** : le scenario DFIQ et ses facets servent de structure d'investigation
   dans le rapport (section 5 - questions d'investigation)

## Livrable

Section triage du rapport : type d'affaire, scenario DFIQ, collection principale, collections secondaires, couverture artefacts, hypotheses de travail.

Voir `methodologie/workflow.md` pour le detail des phases.
