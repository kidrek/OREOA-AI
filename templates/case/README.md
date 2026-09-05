# Case skeleton templates

Scaffold sources for `/case new` (work-order step 1). Kept verbatim from the
architect's v2 reflection (archived in the vault) as the reference of the expected
case state, including a worked example (case `2026-09-INC-042`).

- `case.yaml`   - declarative case state (schema v2): case, context, machines,
  hypotheses (confidence + stop_criteria), findings (validated only), gaps, sessions.
- `journal.md`  - append-only journal + rewritten `Current state` block (the only
  rewritten section), role-tagged entries, every technical claim carries a proof
  reference (evidence id, artifact, record_id, timestamp).

`/case new` derives EMPTY skeletons from these files; the worked example content is
documentation, never a starting case. Writing rules per SPEC.md amendment A1:
`case.yaml` only through the `mcp-case` gate (or hand-edited by the analyst);
`journal.md` append-only by roles, `Current state` rewritten by `analyst` only.
