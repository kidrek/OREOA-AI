---
description: Send a lead to the reviewer before promotion
argument-hint: <lead-id>
step: 3
---

Send the lead $ARGUMENTS to the `reviewer` role. The reviewer verifies
citations, searches the benign explanation (context: parent, arguments, user,
time, path, prevalence of the behaviour tuple - legitimacy of a binary is not
a benign explanation for a behaviour-based lead), checks baseline halves and
flags injection strings. It returns accept|challenge|reject with reasons,
written to the journal `### Revue` section. On accept, request promotion from
the analyst. Present the verdict in French.
