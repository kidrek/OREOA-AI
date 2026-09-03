# Skill investigation - structure DFIQ de l'investigation

## Mission

Structurer l'investigation avec le referentiel DFIQ (scenarios -> facets -> questions) :
choisir le scenario au triage, deriver les questions de la phase 4, resoudre les
approches vers les artefacts et les outils kit, tracer chaque reponse dans le rapport.

## Referentiel

- Corpus amont : bake dans l'image (`/referentiels/dfiq/data`) a chaque build
  (`doctor fix`) - branche main, jamais editee localement ; langue anglaise
- Corpus kit : `referentiels-kit/dfiq/` (prefixe d'id `SK`) - questions et approches
  propres au kit ou au SI analyse
- Index lisible + mapping types d'affaire : `catalogue/dfiq.md` (regenere apres build)
- Corpus jeune : seulement une partie des questions a des approches executables ; les
  autres se traitent par le catalogue SF et les skills, l'ecart est documente

## Commandes (execution conteneurisee via dt)

```bash
dt python3 /work/scripts/referentiels.py dfiq arbre S1008   # arbre scenario -> questions
dt python3 /work/scripts/referentiels.py dfiq plan Q1020    # plan de reponse detaille
dt python3 /work/scripts/referentiels.py dfiq index /work/catalogue/dfiq.md
dt python3 /work/scripts/referentiels.py dfiq check         # integrite + coherence parentale
```

## Usage par phase

- **Phase 1 (triage)** : selectionner le scenario a partir du type d'affaire et du
  contexte analyste (mapping catalogue/dfiq.md). Citer le scenario et ses facets comme
  structure d'investigation. Aucun scenario correspondant : le dire explicitement,
  travailler par catalogue SF
- **Phase 4 (investigation)** : les questions du scenario deviennent les hypotheses
  testables ; pour chaque question avec approches, `dfiq plan <Q-id>` fournit les
  etapes stagees (collection/processing/analysis) et resout les steps
  `ForensicArtifact` vers les chemins et les outils kit (moteur commun avec
  skills/artefacts.md). Les resultats alimentent timeline et observables
- **Phase 6 (rapport)** : section 5 "Questions d'investigation" - chaque question du
  scenario tracee : `repondue` (reponse sourcee), `sans donnees` (ecart), ou `non posee`
  (hors perimetre declare). Ne jamais resoudre une question par speculation

## Regles

1. Le scenario guide, il ne contraint pas : une question hors perimetre declare reste
   "non posee" (le perimetre du triage fait foi)
2. Une approche executable cite ses couvertures (`covered`/`not_covered`) : toute
   conclusion precise le perimetre reellement couvert
3. Les questions repondues citent : collection + artefact referentiel + hash
4. Une question sans approche dans le corpus = traitement kit (catalogue SF, skills),
   ecart documente ; si la question est utile en REX, ecrire une approche custom dans
   `referentiels-kit/dfiq/` ou contribuer amont (PR) - journaliser
5. Toute manipulation d'affaire reste tracee dans `journal.md` (commande exacte + cible)
