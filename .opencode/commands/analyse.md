---
description: Lancer l'investigation complete de l'affaire courante ou d'une collection
---
Lance une investigation numerique complete : $ARGUMENTS

## Affaire courante

Trois formes d'appel :

1. **`/analyse` sans argument** : operates on the current case of the session (set by
   `/case`). If no current case: do not guess - propose `/case "<name>"` (creation) or
   `/case` (panorama to switch), then stop
2. **`/analyse <path>`** : collection external to the case (share, local folder) -
   import by copy then same workflow. Target case: the current one, or asked
3. **First use**: the quick-start guide `docs/QUICK-START.md` is displayed at the end
   of the response (first launch only - `cases/` with no case)

## Procedure

1. **Collection ingestion**:
   - deposits in `cases/<ID>/00_evidence/originals/` not yet recorded ->
     ask for provenance (one line: where the collections come from) then
     `python3 scripts/ingest.py cases/<ID> --scan --provenance "<source>"` -
     SHA256 hashes, manifest, artifact matching, journalized
   - if the scan reports an **INTEGRITY ALERT** (hash drifted since import):
     stop, journalize, ask for the analyst decision - never continue without one
   - already ingested (manifest up to date): go straight to the workflow
2. **Context intake** (if the `context` section of the manifest is empty):
   ask the analyst for the incident context - open question, targeted follow-ups if
   provided, non-blocking if nothing (journalized). If already filled (via `/case` or
   a previous session): do not ask again, recall it at triage
3. Run phases 1 to 6 (skills/triage.md, skills/analyse.md, skills/reporting.md):
   - set the case type, the main collection and the working hypotheses (validation
     gate) leaning on the recorded context and the matching DFIQ scenario
     (catalogue/dfiq.md, skills/investigation.md)
   - analysis, correlation, hypothesis investigation, observables; use the artifact
     matching of the manifest (`artifacts` field) and the weak-signal catalogue
     (catalogue/)
4. Journalize every action in journal.md (append-only, in the case language
   `case.language`); cite artifact + collection + hash for every conclusion
5. Produce the final report in 02_analysis/report/rapport.md (full format), in the case
   language (`templates/rapport.md` FR or `templates/rapport-en.md` EN), with the case
   background section, the DFIQ investigation questions table and the tested-signals
   appendix
