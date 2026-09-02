---
description: Lancer une investigation complete sur une collection de preuves
---
Lance une investigation numerique complete sur la collection suivante : $ARGUMENTS

Procedure :
1. Si aucune affaire n'est mentionnee, demande le nom de l'affaire a l'analyste, puis cree-la : ./create_case.sh "<nom>"
2. Importe la collection : python3 scripts/ingest.py cases/<ID> <collection> - SHA256 et manifest mis a jour, journalise l'import
3. Conduis les phases 1 a 6 (skills/triage.md, skills/analyse.md, skills/reporting.md) :
   - pose le type d'affaire, la collection principale et les hypotheses (gate de validation)
   - analyse, correlation, investigation des hypotheses, observables
   - applique les signaux faibles du catalogue (catalogue/) et les chaines de correlation
4. Journalise chaque action dans journal.md (append-only) ; cite artefact + collection + hash pour chaque conclusion
5. Produis le rapport final dans 02_analysis/report/rapport.md (format full), avec l'annexe des signaux testes
