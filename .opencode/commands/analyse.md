---
description: Lancer l'investigation complete de l'affaire courante ou d'une collection
---
Lance une investigation numerique complete : $ARGUMENTS

## Affaire courante

Trois formes d'appel :

1. **`/analyse` sans argument** : opere sur l'affaire courante de la session (etablie
   par `/case`). Si aucune affaire courante : ne devine pas - propose `/case "<nom>"`
   (creation) ou `/case` (panorama pour switcher), puis arrete-toi
2. **`/analyse <chemin>`** : collection externe a l'affaire (partage, dossier local) -
   import par copie puis meme workflow. L'affaire cible : la courante, ou demandee
3. **Premiere utilisation** : le guide `docs/DEMARRAGE-RAPIDE.md` est affiche a la fin
   de la reponse (premier lancement uniquement - `cases/` sans affaire)

## Procedure

1. **Ingestion des collectes** :
   - depots dans `cases/<ID>/00_evidence/originals/` non encore enregistres ->
     demande la provenance (une ligne : d'ou viennent ces collectes) puis
     `python3 scripts/ingest.py cases/<ID> --scan --provenance "<source>"` -
     empreintes SHA256, manifest, rapprochement des artefacts, journalise
   - si le scan signale une **ALERTE INTEGRITE** (empreinte derivee depuis l'import) :
     arrete-toi, journalise, demande la decision de l'analyste - jamais de suite sans decision
   - deja integre (manifest a jour) : passe directement au workflow
2. **Intake de contexte** (si la section `contexte` du manifest n'est pas renseignee) :
   demande a l'analyste le contexte de l'incident - question ouverte, relances ciblees
   si apport, non bloquant si rien (journalise). Si deja renseigne (via `/case` ou
   session precedente) : ne redemande pas, rappelle-le au triage
3. Conduis les phases 1 a 6 (skills/triage.md, skills/analyse.md, skills/reporting.md) :
   - pose le type d'affaire, la collection principale et les hypotheses (gate de
     validation) en t'appuyant sur le contexte consigne et le scenario DFIQ correspondant
     (catalogue/dfiq.md, skills/investigation.md)
   - analyse, correlation, investigation des hypotheses, observables ; exploite le
     rapprochement artefacts du manifest (champ `artefacts`) et le catalogue des
     signaux faibles (catalogue/)
4. Journalise chaque action dans journal.md (append-only) ; cite artefact + collection +
   hash pour chaque conclusion
5. Produis le rapport final dans 02_analysis/report/rapport.md (format full), avec la
   section contexte, le tableau des questions d'investigation DFIQ et l'annexe des
   signaux testes
