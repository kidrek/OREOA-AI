# Quick start - OREOA-AI kit

Welcome to your digital forensics kit. An agent runs the investigation, you provide
the evidence and validate each step. Three gestures are enough:

## 1. Open a case

```text
/case "Your case name"
```

The agent scaffolds the directory, asks for the incident context (what happened, who
reported it, period, affected systems) and gives you the case ID.

## 2. Drop your collections

Copy your collections (logs, captures, dumps...) into the case folder:

```text
cases/<ID>/00_evidence/originals/
```

Tell the agent where they come from (one line is enough): it hashes them (SHA256),
matches them against the artifact referential and journalizes the import.

## 3. Run the investigation

```text
/analyse
```

The agent runs the full workflow (triage, analysis, correlation, investigation,
observables, report) and stops at every key step for your validation. The final report
is sourced: every conclusion cites its collection, its artifact and its hash.

## Also useful

- `/case` alone: panorama of your cases (resume one, open another)
- `/analyse <path>`: import a collection still outside the case
- `/deploy`: deploy the kit to another laptop (online or air-gap)
- Guidance mode: RAM capture, disk acquisition, live response - the agent walks you
  through it step by step when the action happens on a live machine
- `/lang fr`: switch the session language (French guide: `docs/QUICK-START.fr.md`)

Kit health is verified automatically at every session (doctor). If something is
missing, the agent guides you through the fix before any investigation.
