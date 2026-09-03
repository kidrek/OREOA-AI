---
description: Lancer une investigation complete sur une collection de preuves
---
Lance une investigation numerique complete sur la collection suivante : $ARGUMENTS

Procedure :
1. Si aucune affaire n'est mentionnee, demande le nom de l'affaire a l'analyste, puis cree-la : ./create_case.sh "<nom>"
2. Demande le contexte de l'incident a l'analyste AVANT toute ingestion :
   - question ouverte : "Avez-vous du contexte a partager sur cet incident ? (description de ce qui s'est passe, qui a signale, periode, systemes concernes, mesures deja prises, contraintes)"
   - si l'analyste apporte du contexte : reformule-le, fais-le valider, consigne-le dans manifest.yaml (section `contexte`) puis journalise dans journal.md
   - si l'analyste n'a rien a partager ("non", "pas pour l'instant") : consigne "aucun contexte fourni" dans journal.md et continue - ne bloque pas, ne relance pas
   - si le manifest contient deja un `contexte` renseigne : ne redemande pas ; propose seulement de le completer si l'analyste le souhaite
   - le contexte alimente ensuite le triage (type d'affaire, hypotheses) et la section "Contexte de l'affaire" du rapport
3. Importe la collection : python3 scripts/ingest.py cases/<ID> <collection> - SHA256 et manifest mis a jour, rapprochement des artefacts du referentiel embarque (scripts/referentiels.py via dt), journalise l'import
4. Conduis les phases 1 a 6 (skills/triage.md, skills/analyse.md, skills/reporting.md) :
   - pose le type d'affaire, la collection principale et les hypotheses (gate de validation) en t'appuyant sur le contexte consigne et le scenario DFIQ correspondant (catalogue/dfiq.md, skills/investigation.md)
   - analyse, correlation, investigation des hypotheses, observables ; exploite le rapprochement artefacts du manifest (champ `artefacts`) et le catalogue des signaux faibles (catalogue/)
5. Journalise chaque action dans journal.md (append-only) ; cite artefact + collection + hash pour chaque conclusion
6. Produis le rapport final dans 02_analysis/report/rapport.md (format full), avec la section contexte, le tableau des questions d'investigation DFIQ et l'annexe des signaux testes
