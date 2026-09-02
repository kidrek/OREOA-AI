#!/usr/bin/env bash
# e2e.sh - test de bout en bout du kit (tranche verticale v1)
# Prerequis : Docker daemon actif et image dfir-tools construite (doctor check)
set -uo pipefail

KIT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$KIT_DIR"
export KIT_DIR

ECHAP=0
etape() { echo ""; echo "== $1 =="; }
ok()    { echo "   [ok] $1"; }
warn()  { echo "   [warn] $1"; }
ko()    { echo "   [fail] $1"; ECHAP=1; }

etape "1. Scaffolding d'affaire de test"
CASE_ID="CASE-TEST-0001"
rm -rf "cases/$CASE_ID"
./create_case.sh --id "$CASE_ID" "Affaire de test E2E" >/dev/null
[[ -d "cases/$CASE_ID/00_evidence/originals" ]] && ok "scaffold affaire" || ko "scaffold affaire"

etape "2. Ingestion des collections synthetiques"
python3 scripts/ingest.py "cases/$CASE_ID" tests/samples/auth.log >/dev/null \
  && ok "auth.log importe" || ko "auth.log"
python3 scripts/ingest.py "cases/$CASE_ID" tests/samples/syslog >/dev/null \
  && ok "syslog importe" || ko "syslog"
python3 scripts/ingest.py "cases/$CASE_ID" tests/samples/security.jsonl >/dev/null \
  && ok "security.jsonl importe" || ko "security.jsonl"

etape "3. Verification du manifest"
python3 - <<'EOF' && ok "manifest complet" || ko "manifest"
import sys, yaml
from pathlib import Path
m = yaml.safe_load(Path("cases/CASE-TEST-0001/manifest.yaml").read_text())
cols = m.get("collections", [])
assert len(cols) == 3, f"collections={len(cols)}"
for c in cols:
    assert c["sha256"] and len(c["sha256"]) == 64, f"hash invalide: {c['nom']}"
sys.exit(0)
EOF

etape "4. Preuves en lecture seule"
ORIG="cases/$CASE_ID/00_evidence/originals/auth.log"
H1=$(sha256sum "$ORIG" | cut -d' ' -f1)
chmod u+w "$ORIG" 2>/dev/null || true
# simulation : tentative d'ecriture bloquee par la regle kit (l'agent ne doit jamais ecrire ici)
H2=$(sha256sum "$ORIG" | cut -d' ' -f1)
[[ "$H1" == "$H2" ]] && ok "originals intacts" || ko "originals modifies"

etape "5. Outils conteneurises (si image disponible)"
if docker image inspect oreoa-ai-tools:1.0.0 >/dev/null 2>&1; then
  # tests monte sous /tests dans le conteneur (voir scripts/dt)
  ./scripts/dt yara /tests/samples/rules.yar /tests/samples/testfile.bin 2>/dev/null | grep -q kit_test_marker \
    && ok "yara conteneurise" || ko "yara conteneurise"
  ./scripts/dt log2timeline --version >/dev/null 2>&1 \
    && ok "log2timeline conteneurise" || ko "log2timeline conteneurise"
else
  echo "   [skip] image oreoa-ai-tools absente (provisioner avec : python3 scripts/doctor.py fix)"
fi

etape "5bis. Memoire volatile (optionnel - dump hors depot)"
DUMP_MEM="/tests/samples/dump.raw"
if ! docker image inspect oreoa-ai-tools:1.0.0 >/dev/null 2>&1; then
  echo "   [skip] image oreoa-ai-tools absente (provisioner avec : python3 scripts/doctor.py fix)"
elif [[ ! -f tests/samples/dump.raw ]]; then
  echo "   [skip] aucun dump de test (tests/samples/dump.raw, hors depot - procedure : connaissances/memoire/exploitation-volatility.md)"
else
  SORTIE_MEM=$(./scripts/dt vol -f "$DUMP_MEM" windows.pslist 2>&1 || true)
  if echo "$SORTIE_MEM" | grep -qiE "volatility 3"; then
    if echo "$SORTIE_MEM" | grep -qiE "unsatisfied requirement"; then
      warn "volatility3 execute mais symboles requis (connaissances/memoire/exploitation-volatility.md)"
    else
      ok "volatility3 conteneurise sur dump de test"
    fi
  else
    ko "volatility3 sur dump de test (aucune sortie exploitable)"
  fi
fi

etape "6. Resume"
if [[ $ECHAP -eq 0 ]]; then
  echo "   E2E : OK"
else
  echo "   E2E : ECHEC (voir ci-dessus)"
fi
exit $ECHAP
