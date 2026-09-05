# T0 Synthetic corpus (work-order step 1.6)

Declarative scenarios in `scenarios/*.yaml` are the single source of truth;
`make corpus` turns them into deterministic synthetic evidence and pins the
sha256 of every artifact in `corpus_manifest.json` (committed - tests fail
if the hash drifts without a scenario change, SPEC T0).

## Layout

- `scenarios/`          declarative scenarios (host, users, planted events,
  expected detections, traps) - see `src/oreoa/corpus_gen/scenario.py`
- `out/`                build output (gitignored): per scenario
  `<name>.velociraptor.zip` (fast lane), `<name>.kape.zip` (step-2 quick
  parsers), `<name>.disk.img` (raw NTFS v0)
- `corpus_manifest.json` committed build manifest (scenario + artifact hashes)
- `legacy_generators/`, `legacy_samples/` frozen kit v2.1 assets (absorbed by
  the scenarios over time - see `MIGRATION.md`)

## Scenarios

- `win-workstation-01` - compromised host covering the `test:` line of every
  Windows-applicable detection hunt of `hunts_catalog_seed.yaml` v0.3 that is
  reachable in the fast lane, plus the SPEC T0 traps (LOLBin certutil,
  timestomping, hallucination record id, prompt-injection set, zip-slip,
  archive bomb, hash-mismatch tamper)
- `clean-host-01` - benign-only host, zero expected detections (false-positive
  yardstick for T2)

## S1.6 scope decisions (journalized in docs/journal.md)

- Deferred to the deep-lane sub-step: memory sample + ISF, E01, BitLocker/LUKS2,
  VSS, raw EVTX/hive/.pf binaries inside the KAPE archive (the fast-lane
  signal travels in the Velociraptor JSONL; those binaries have no consumer
  before plaso lands)
- Disk image v0: files at the image root (ntfs-3g has no mkfs-side mkdir);
  the directory tree stays declarative in MFT.csv and is exercised by the
  deep-lane image parsing (work-order step 4)
- Determinism: mkntfs/ntfscp wall-clock artifacts are normalized by the MFT
  patcher (serial, timestamps, INDX buffers); the image hash is reproducible
- The one-shot `oreoa/corpus-ntfs` image (debian-slim + pinned ntfs-3g) is
  built by `make corpus-image`; no privileged container, no mounting
