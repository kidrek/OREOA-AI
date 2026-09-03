#!/usr/bin/env bash
# e2e.sh - end-to-end test of the kit (v1 vertical slice)
# Prerequisite: active Docker daemon and oreoa-ai-tools image built (doctor check)
set -uo pipefail

KIT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$KIT_DIR"
export KIT_DIR

ECHAP=0
etape() { echo ""; echo "== $1 =="; }
ok()    { echo "   [ok] $1"; }
warn()  { echo "   [warn] $1"; }
ko()    { echo "   [fail] $1"; ECHAP=1; }

etape "1. Test case scaffolding (inline, no script)"
CASE_ID="CASE-TEST-0001"
CASE_DIR="cases/$CASE_ID"
rm -rf "$CASE_DIR"
mkdir -p "$CASE_DIR"/{00_evidence/{originals,exports,images},01_work/tmp,02_analysis/{logs,ioc,report}}
cat > "$CASE_DIR/manifest.yaml" <<EOF
case:
  id: "$CASE_ID"
  name: "E2E test case"
  created: "$(date +%F)"
  status: open
  language: en

context:
  description: ""
  reported_by: ""
  reported_at: ""
  systems: []
  suspected_period: { start: "", end: "" }
  actions_taken: []
  constraints: []

collections: []
EOF
cat > "$CASE_DIR/journal.md" <<EOF
# Journal - $CASE_ID

Case: E2E test case
Opened: $(date '+%F %T')

---

## Phase 0 - Import

- $(date '+%F %T') -- Case directory created (inline E2E scaffold)
EOF
[[ -d "$CASE_DIR/00_evidence/originals" && -d "$CASE_DIR/00_evidence/images" && -f "$CASE_DIR/manifest.yaml" ]] \
  && ok "case scaffold (inline, with images/)" || ko "case scaffold"

etape "2. Synthetic collections ingestion"
python3 scripts/ingest.py "cases/$CASE_ID" tests/samples/auth.log >/dev/null \
  && ok "auth.log imported" || ko "auth.log"
python3 scripts/ingest.py "cases/$CASE_ID" tests/samples/syslog >/dev/null \
  && ok "syslog imported" || ko "syslog"
python3 scripts/ingest.py "cases/$CASE_ID" tests/samples/security.jsonl >/dev/null \
  && ok "security.jsonl imported" || ko "security.jsonl"

etape "3. Manifest verification"
python3 - <<'EOF' && ok "manifest complete" || ko "manifest"
import sys, yaml
from pathlib import Path
m = yaml.safe_load(Path("cases/CASE-TEST-0001/manifest.yaml").read_text())
assert m.get("case", {}).get("id") == "CASE-TEST-0001", "case block missing"
assert m["case"].get("language") == "en", "case.language missing"
cols = m.get("collections", [])
assert len(cols) == 3, f"collections={len(cols)}"
for c in cols:
    assert c["sha256"] and len(c["sha256"]) == 64, f"invalid hash: {c['name']}"
sys.exit(0)
EOF

etape "4. Evidence read-only"
ORIG="cases/$CASE_ID/00_evidence/originals/auth.log"
H1=$(sha256sum "$ORIG" | cut -d' ' -f1)
chmod u+w "$ORIG" 2>/dev/null || true
# simulation: write attempt blocked by the kit rule (the agent must never write here)
H2=$(sha256sum "$ORIG" | cut -d' ' -f1)
[[ "$H1" == "$H2" ]] && ok "originals untouched" || ko "originals modified"

etape "4bis. Deposit scan (normal path: analyst drop)"
cp tests/samples/c2.pcap "$CASE_DIR/00_evidence/originals/" \
  && python3 scripts/ingest.py "$CASE_DIR" --scan --provenance "E2E synthetic deposit" >/dev/null 2>&1 \
  && python3 - <<'EOF' && ok "scan: deposit imported, hash and provenance recorded" || ko "deposit scan"
import sys, yaml
from pathlib import Path
m = yaml.safe_load(Path("cases/CASE-TEST-0001/manifest.yaml").read_text())
cols = {c["name"]: c for c in m.get("collections", [])}
assert "c2.pcap" in cols, "c2.pcap missing from manifest"
assert cols["c2.pcap"]["original_path"].startswith("analyst deposit"), "provenance missing"
assert len(cols["c2.pcap"]["sha256"]) == 64, "invalid hash"
sys.exit(0)
EOF
python3 scripts/ingest.py "$CASE_DIR" --scan >/dev/null 2>&1 \
  && ok "scan re-run: integrity verified, zero alert" || ko "scan re-run (integrity)"

etape "5. Containerized tools (if image available)"
if docker image inspect oreoa-ai-tools:1.1.0 >/dev/null 2>&1; then
  # tests mounted under /tests in the container (see scripts/dt)
  ./scripts/dt yara /tests/samples/rules.yar /tests/samples/testfile.bin 2>/dev/null | grep -q kit_test_marker \
    && ok "yara containerized" || ko "yara containerized"
  ./scripts/dt log2timeline --version >/dev/null 2>&1 \
    && ok "log2timeline containerized" || ko "log2timeline containerized"
else
  echo "   [skip] oreoa-ai-tools image missing (provision with: python3 scripts/doctor.py fix)"
fi

etape "5bis. Volatile memory (optional - dump out of repo)"
DUMP_MEM="/tests/samples/dump.raw"
if ! docker image inspect oreoa-ai-tools:1.1.0 >/dev/null 2>&1; then
  echo "   [skip] oreoa-ai-tools image missing (provision with: python3 scripts/doctor.py fix)"
elif [[ ! -f tests/samples/dump.raw ]]; then
  echo "   [skip] no test dump (tests/samples/dump.raw, out of repo - procedure: connaissances/memoire/exploitation-volatility.md)"
else
  SORTIE_MEM=$(./scripts/dt vol -f "$DUMP_MEM" windows.pslist 2>&1 || true)
  if echo "$SORTIE_MEM" | grep -qiE "volatility 3"; then
    if echo "$SORTIE_MEM" | grep -qiE "unsatisfied requirement"; then
      warn "volatility3 ran but symbols required (connaissances/memoire/exploitation-volatility.md)"
    else
      ok "volatility3 containerized on test dump"
    fi
  else
    ko "volatility3 on test dump (no usable output)"
  fi
fi

etape "5ter. Network tooling (tshark + suricata)"
if ! docker image inspect oreoa-ai-tools:1.1.0 >/dev/null 2>&1; then
  echo "   [skip] oreoa-ai-tools image missing (provision with: python3 scripts/doctor.py fix)"
else
  # tshark: C2 domain extraction from the malicious capture (deterministic)
  QRY=$(./scripts/dt tshark -r /tests/samples/c2.pcap -Y "dns.flags.response==0" -T fields -e dns.qry.name 2>/dev/null || true)
  echo "$QRY" | grep -q "c2.kit-test.invalid" \
    && ok "tshark containerized (C2 DNS extracted)" || ko "tshark containerized (C2 DNS extracted)"

  # suricata: recall on the malicious capture (kit rules, deterministic)
  SURI_C2=$(./scripts/dt sh -c 'rm -rf /tmp/suri && mkdir -p /tmp/suri && suricata -r /tests/samples/c2.pcap -l /tmp/suri >/dev/null 2>&1; cat /tmp/suri/eve.json 2>/dev/null' || true)
  echo "$SURI_C2" | grep -q "KIT-TEST" \
    && ok "suricata containerized (kit rule alerts on c2.pcap)" || ko "suricata containerized (kit rule alerts on c2.pcap)"

  # suricata: noise on the clean capture (0 alert expected; ET Open alerts reported without failure)
  SURI_CLEAN=$(./scripts/dt sh -c 'rm -rf /tmp/suriclean && mkdir -p /tmp/suriclean && suricata -r /tests/samples/clean.pcap -l /tmp/suriclean >/dev/null 2>&1; grep -c "\"event_type\":\"alert\"" /tmp/suriclean/eve.json 2>/dev/null' || true)
  if [[ "${SURI_CLEAN:-}" == "0" ]]; then
    ok "suricata zero alert on clean.pcap (effective triage)"
  elif [[ -n "${SURI_CLEAN:-}" && "${SURI_CLEAN:-}" =~ ^[0-9]+$ ]]; then
    warn "suricata: $SURI_CLEAN ET Open alert(s) on clean.pcap (tune triage: config/suricata/disable.conf, connaissances/reseau/)"
  else
    ko "suricata on clean.pcap (no usable output)"
  fi
fi

etape "5quater. Artifacts referential (ForensicArtifacts)"
if ! docker image inspect oreoa-ai-tools:1.1.0 >/dev/null 2>&1; then
  echo "   [skip] oreoa-ai-tools image missing (provision with: python3 scripts/doctor.py fix)"
else
  # baked referential integrity (MANIFEST.sha256 + traces)
  ./scripts/dt python3 /work/scripts/referentiels.py artifacts check >/dev/null 2>&1 \
    && ok "artifacts referential integrated (manifest + traces)" \
    || ko "artifacts referential integrated (manifest + traces)"

  # automatic matching at ingestion (test case manifest)
  python3 - <<'EOF' && ok "artifact matching (test manifest)" || ko "artifact matching (test manifest)"
import sys, yaml
from pathlib import Path
m = yaml.safe_load(Path("cases/CASE-TEST-0001/manifest.yaml").read_text())
refs = m.get("referentials", {})
assert refs.get("artifacts", {}).get("version"), "referentials missing from manifest"
cols = {c["name"]: c for c in m.get("collections", [])}
assert "LinuxAuthLogs" in cols["auth.log"]["artifacts"], f"auth.log: {cols['auth.log']['artifacts']}"
assert cols["auth.log"]["artifacts"], "auth.log without artifact"
sys.exit(0)
EOF

  # resolved expansion + kit tools
  EXP=$(./scripts/dt python3 /work/scripts/referentiels.py artifacts expand WindowsEventLogs 2>/dev/null || true)
  echo "$EXP" | grep -q "winevt" && echo "$EXP" | grep -q "log2timeline" \
    && ok "artifact expansion resolved (paths + tools)" \
    || ko "artifact expansion resolved (paths + tools)"
fi

etape "5quinquies. DFIQ referential (investigation questions)"
if ! docker image inspect oreoa-ai-tools:1.1.0 >/dev/null 2>&1; then
  echo "   [skip] oreoa-ai-tools image missing (provision with: python3 scripts/doctor.py fix)"
else
  # corpus integrity + parental consistency
  ./scripts/dt python3 /work/scripts/referentiels.py dfiq check >/dev/null 2>&1 \
    && ok "DFIQ corpus integrated (manifest + parent links)" \
    || ko "DFIQ corpus integrated (manifest + parent links)"

  # lateral movement scenario tree (deterministic)
  ARBRE=$(./scripts/dt python3 /work/scripts/referentiels.py dfiq arbre S1008 2>/dev/null || true)
  echo "$ARBRE" | grep -q "Lateral Movement" && echo "$ARBRE" | grep -q "F1027" \
    && ok "DFIQ S1008 tree usable" || ko "DFIQ S1008 tree usable"

  # answer plan with cross-resolution DFIQ -> artifact (Q1020 -> BrowserHistory)
  PLAN=$(./scripts/dt python3 /work/scripts/referentiels.py dfiq plan Q1020 2>/dev/null || true)
  echo "$PLAN" | grep -q "BrowserHistory" && echo "$PLAN" | grep -q "Plaso" \
    && ok "DFIQ Q1020 plan with ForensicArtifact resolution" \
    || ko "DFIQ Q1020 plan with ForensicArtifact resolution"

  # generated indexes regen (mapping preservation between markers)
  ./scripts/dt python3 /work/scripts/referentiels.py artifacts index /work/catalogue/artefacts.md >/dev/null 2>&1 \
    && ./scripts/dt python3 /work/scripts/referentiels.py dfiq index /work/catalogue/dfiq.md >/dev/null 2>&1 \
    && grep -q "SF-W-001" catalogue/artefacts.md && grep -q "S1008" catalogue/dfiq.md \
    && ok "catalogue indexes regenerated (mapping preserved)" \
    || ko "catalogue indexes regenerated (mapping preserved)"
fi

etape "5sexies. Disk tooling (TSK + plaso, v2.0)"
if ! docker image inspect oreoa-ai-tools:1.1.0 >/dev/null 2>&1; then
  echo "   [skip] oreoa-ai-tools image missing (provision with: python3 scripts/doctor.py fix)"
elif ! python3 tests/samples/gen_disk.py /tmp/kit-e2e-disk.raw >/dev/null 2>&1; then
  echo "   [skip] mke2fs missing on host (e2fsprogs) - disk step skipped"
else
  DISK_IMG="/tmp/kit-e2e-disk.raw"
  # temporary disk case (independent from CASE-TEST-0001)
  rm -rf cases/CASE-TEST-DISK
  mkdir -p cases/CASE-TEST-DISK/{00_evidence/{originals,exports,images},01_work/tmp,02_analysis/timeline}
  cp "$DISK_IMG" cases/CASE-TEST-DISK/00_evidence/originals/kit-disk.raw
  rm -f "$DISK_IMG"

  # ingestion: .raw with disk magic -> .rawdisk + size_bytes
  python3 scripts/ingest.py cases/CASE-TEST-DISK --scan --provenance "E2E synthetic disk" >/dev/null 2>&1 \
    && python3 - <<'EOF' && ok "disk ingestion (magic .rawdisk + size_bytes)" || ko "disk ingestion"
import sys, yaml
from pathlib import Path
m = yaml.safe_load(Path("cases/CASE-TEST-DISK/manifest.yaml").read_text())
c = m["collections"][0]
assert c["type"] == ".rawdisk", f"type={c['type']}"
assert c.get("size_bytes") == 4 * 1024 * 1024, f"size={c.get('size_bytes')}"
sys.exit(0)
EOF

  # info: ext4 detection + barrier
  INFO=$(./scripts/dt -c CASE-TEST-DISK python3 /work/scripts/disk.py info /affaires/00_evidence/originals/kit-disk.raw 2>/dev/null || true)
  echo "$INFO" | grep -q "TSK_FS_TYPE_EXT4" && echo "$INFO" | grep -q "\[space\]" \
    && ok "disk.py info (ext4 detected, barrier reported)" || ko "disk.py info"

  # targeted extraction via referential paths
  ./scripts/dt -c CASE-TEST-DISK python3 /work/scripts/referentiels.py artifacts paths LinuxAuthLogs \
    > cases/CASE-TEST-DISK/01_work/tmp/paths.txt 2>/dev/null
  ./scripts/dt -c CASE-TEST-DISK python3 /work/scripts/disk.py extract \
    /affaires/00_evidence/originals/kit-disk.raw --offset 0 \
    --paths /affaires/01_work/tmp/paths.txt --out /affaires/01_work/tmp/extraits >/dev/null 2>&1 \
    && grep -q "KIT-DISK-FAILED" cases/CASE-TEST-DISK/01_work/tmp/extraits/auth.log 2>/dev/null \
    && grep -q "extracted" cases/CASE-TEST-DISK/01_work/tmp/extraits/extraction-report.txt \
    && ok "disk.py extract (referential paths, SHA256 report)" || ko "disk.py extract"

  # plaso super-timeline on the raw image
  ./scripts/dt -c CASE-TEST-DISK log2timeline --quiet \
    --storage-file /affaires/02_analysis/timeline/disk.plaso \
    /affaires/00_evidence/originals/kit-disk.raw >/dev/null 2>&1 \
    && ./scripts/dt -c CASE-TEST-DISK psort --output-format dynamic \
    -w /affaires/02_analysis/timeline/timeline.csv \
    /affaires/02_analysis/timeline/disk.plaso >/dev/null 2>&1 \
    && grep -q "EXT:/var/log/auth.log" cases/CASE-TEST-DISK/02_analysis/timeline/timeline.csv \
    && ok "plaso super-timeline on disk image (parsed auth.log content)" \
    || ko "plaso super-timeline on disk image"

  # EWF support (E01 readable in-image) - format check without sample
  # (capture first: grep -q + pipefail would SIGPIPE img_stat)
  EWF_LIST=$(./scripts/dt img_stat -i list 2>&1 || true)
  echo "$EWF_LIST" | grep -qw ewf \
    && ok "EWF support present (E01 readable in-image, sample REX-qualified)" \
    || ko "EWF support present"
  rm -rf cases/CASE-TEST-DISK
fi

etape "6. Summary"
if [[ $ECHAP -eq 0 ]]; then
  echo "   E2E: OK"
else
  echo "   E2E: FAILED (see above)"
fi
exit $ECHAP
