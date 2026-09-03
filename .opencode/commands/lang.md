---
description: View or change the session language
---
Session language: $ARGUMENTS

## Without argument (`/lang`)

State the current language rules and the kit defaults:

- kit default language (config/tools.yaml `language`): deliverables and case journal
- conversation: you mirror the analyst's language (detect it, answer in it)
- if a current case is established, state its `case.language`

## With argument (`/lang fr` or `/lang en`)

1. Set the session conversation language to the requested language
2. If a current case is established, offer to persist: "Souhaitez-vous aussi passer les
   livrables et le journal de l'affaire courante dans cette langue ? (met a jour
   `case.language` du manifest)" - apply only on confirmation, journalize the change
3. Confirm the new state in one line

## Rules

- The knowledge base (skills, methodology, catalogues) stays French - the single source
  of truth; never translate kit knowledge files
- Deliverables (report, timeline, observables) and the case journal follow
  `case.language`; on-demand translation applies immediately to the current deliverable
  and is offered as persistent
- Never interrupt an ongoing investigation to ask about language
