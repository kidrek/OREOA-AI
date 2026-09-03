# Case report template (EN)

Standard case report structure. Every section is mandatory; a non-applicable section is
marked "not applicable (reason)". Language: follow `case.language` of the manifest -
use `templates/rapport.md` for the French version.

---

```markdown
# Investigation report -- <ID>

Case: <name>
Period: <start> -- <end>
Date: <report date>
Format: <full | executive | technical>

## 1. Executive summary

<5-10 line synthesis of the case: what happened, affected assets, main conclusion,
recommended measures>

## 2. Case background

- Context: <case context>
- Analyst context: <synthesis of the manifest `context` section (reported_by,
  reporting date, period, systems, actions already taken) - or "no context provided
  at opening">
- Question asked: <initial investigation question>
- DFIQ scenario: <id - name> (axes: <explored facets>)
- Scope: <scope declared at triage>
- Referentials: ISO 27037, ISO 27035, ISO 27043, NIST SP 800-86; upstream
  referentials: ForensicArtifacts <version>, DFIQ <commit> (recorded in the manifest,
  `referentials` field)

## 3. Procedure

| Phase | Actions | Collections used | Tools |
|-------|---------|------------------|-------|
| 0. Import | scan, hashes | <collections> | <tools> |
| 1. Triage | typing, main | <collections> | <tools> |
| ... | ... | ... | ... |

## 4. Collection inventory

| Collection | Type | SHA256 | Artifacts (referential) | Description |
|-----------|------|--------|-------------------------|-------------|
| <name> | <type> | <hash> | <artifact names or -> | <description> |

## 5. Investigation questions

DFIQ structure of the scenario (skills/investigation.md). Any question without data is
presented as a gap, never resolved by speculation.

| Facet | Question | Status | Answer (sourced) |
|-------|----------|--------|------------------|
| <F-id> | <Q-id - name> | answered / no data / not in scope | <answer + collection + artifact + hash or gap reason> |

## 6. Affected assets

| Asset | Type | Role | Source |
|-------|------|------|--------|
| <name> | system | <role> | <collection> |

## 7. Timeline

| Timestamp | Event | Source (collection + artifact + hash) |
|-----------|-------|----------------------------------------|
| <ts> | <event> | <source> |

## 8. Observables

| Type | Value | Context | Source | Confidence |
|------|-------|---------|--------|------------|
| <type> | <value> | <context> | <source> | <level> |

## 9. Hypotheses

| Hypothesis | Status | Sources |
|-----------|--------|---------|
| <hypothesis> | validated / invalidated / inconclusive | <sources> |

## 10. Conclusion

<answer to the question asked, every statement sourced>

## 11. Containment measures

<actions taken or recommended, timestamped>

## 12. Remediation

<corrective actions, timestamped>

## 13. Security hardening recommendations

<preventive measures, by priority>

## 14. Appendices

- Full hashes: see manifest.yaml
- Action journal: see journal.md
- Technical details: <references>
```

---

## Redaction rules

1. Every statement of the executive summary is detailed in the body
2. Every conclusion cites its source (collection + artifact + hash)
3. Hypotheses are presented with their status, never as conclusions
4. Observables are listed in the final table, with their confidence
