"""T0 synthetic corpus generators (SPEC testing strategy, work-order step 1.6).

This package turns declarative scenario files (``corpus/scenarios/*.yaml``)
into deterministic synthetic evidence:

- ``velociraptor.py``  Velociraptor offline-collector archive (results/*.json
  JSONL + uploads/) - the fast-lane source of truth at S1.6;
- ``kape.py``          KAPE-style archive (Module_Output CSVs for the step-2
  quick parsers: MFT, USN, Amcache);
- ``ntfs.py``          raw NTFS disk image v0: one-shot pinned container
  (mkntfs + ntfscp, no mounting) + host-side MFT patcher;
- ``builder.py``       orchestration + ``corpus/corpus_manifest.json``.

Every generator is deterministic: fixed timestamps from the scenario window,
sorted entries, fixed zip metadata. The committed manifest pins the sha256 of
each artifact; tests fail if the hash drifts without a scenario change
(SPEC T0). Deferred to the deep-lane sub-step (locked decision 5, S1.6
arbitration): memory sample + ISF, E01, BitLocker/LUKS2, VSS, raw EVTX/hive/
.pf binaries inside the KAPE archive (the fast-lane signal travels in the
Velociraptor JSONL; those binaries have no consumer before plaso lands).
"""

from oreoa.corpus_gen.scenario import Scenario, load_scenario

__all__ = ["Scenario", "load_scenario"]
