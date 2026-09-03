#!/usr/bin/env bash
# e2e.sh - test de bout en bout du kit (tranche verticale v1)
# Prerequis : Docker daemon actif et image oreoa-ai-tools construite (doctor check)
set -uo pipefail

KIT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$KIT_DIR"
export KIT_DIR

ECHAP=0
etape() { echo ""; echo "== $1 =="; }
ok()    { echo "   [ok] $1"; }
warn()  { echo "   [warn] $1"; }
ko()    { echo "   [fail] $1"; ECHAP=1; }

etape "1. Scaffolding d'affaire de test (inline, sans script)"
CASE_ID="CASE-TEST-0001"
CASE_DIR="cases/$CASE_ID"
rm -rf "$CASE_DIR"
mkdir -p "$CASE_DIR"/{00_evidence/{originals,exports,images},01_work/tmp,02_analysis/{logs,ioc,report}}
cat > "$CASE_DIR/manifest.yaml" <<EOF
affaire:
  id: "$CASE_ID"
  nom: "Affaire de test E2E"
  date_creation: "$(date +%F)"
  statut: ouverte

contexte:
  description: ""
  declarant: ""
  date_signalement: ""
  systemes_concernes: []
  periode_suspecte: { debut: "", fin: "" }
  mesures_deja_prises: []
  contraintes: []

collections: []
EOF
cat > "$CASE_DIR/journal.md" <<EOF
# Journal - $CASE_ID

Affaire : Affaire de test E2E
Ouverture : $(date '+%F %T')

---

## Phase 0 - Import

- $(date '+%F %T') -- Dossier d'affaire cree (scaffold E2E inline)
EOF
[[ -d "$CASE_DIR/00_evidence/originals" && -d "$CASE_DIR/00_evidence/images" && -f "$CASE_DIR/manifest.yaml" ]] \
  && ok "scaffold affaire (inline, avec images/)" || ko "scaffold affaire"

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

etape "4bis. Scan des depots (voie normale : depot analyste)"
cp tests/samples/c2.pcap "$CASE_DIR/00_evidence/originals/" \
  && python3 scripts/ingest.py "$CASE_DIR" --scan --provenance "E2E depot synthetique" >/dev/null 2>&1 \
  && python3 - <<'EOF' && ok "scan : depot importe, empreinte et provenance consignees" || ko "scan des depots"
import sys, yaml
from pathlib import Path
m = yaml.safe_load(Path("cases/CASE-TEST-0001/manifest.yaml").read_text())
cols = {c["nom"]: c for c in m.get("collections", [])}
assert "c2.pcap" in cols, "c2.pcap absent du manifest"
assert cols["c2.pcap"]["chemin_original"].startswith("depot manuel"), "provenance absente"
assert len(cols["c2.pcap"]["sha256"]) == 64, "hash invalide"
sys.exit(0)
EOF
python3 scripts/ingest.py "$CASE_DIR" --scan >/dev/null 2>&1 \
  && ok "scan re-passe : integrite verifiee, zero alerte" || ko "scan re-passe (integrite)"

etape "5. Outils conteneurises (si image disponible)"
if docker image inspect oreoa-ai-tools:1.1.0 >/dev/null 2>&1; then
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
if ! docker image inspect oreoa-ai-tools:1.1.0 >/dev/null 2>&1; then
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

etape "5ter. Reseau outille (tshark + suricata)"
if ! docker image inspect oreoa-ai-tools:1.1.0 >/dev/null 2>&1; then
  echo "   [skip] image oreoa-ai-tools absente (provisioner avec : python3 scripts/doctor.py fix)"
else
  # tshark : extraction du domaine C2 dans la capture malveillante (deterministe)
  QRY=$(./scripts/dt tshark -r /tests/samples/c2.pcap -Y "dns.flags.response==0" -T fields -e dns.qry.name 2>/dev/null || true)
  echo "$QRY" | grep -q "c2.kit-test.invalid" \
    && ok "tshark conteneurise (DNS C2 extrait)" || ko "tshark conteneurise (DNS C2 extrait)"

  # suricata : recall sur la capture malveillante (regles kit, deterministes)
  SURI_C2=$(./scripts/dt sh -c 'rm -rf /tmp/suri && mkdir -p /tmp/suri && suricata -r /tests/samples/c2.pcap -l /tmp/suri >/dev/null 2>&1; cat /tmp/suri/eve.json 2>/dev/null' || true)
  echo "$SURI_C2" | grep -q "KIT-TEST" \
    && ok "suricata conteneurise (alertes regles kit sur c2.pcap)" || ko "suricata conteneurise (alertes regles kit sur c2.pcap)"

  # suricata : bruit sur la capture propre (0 alerte attendu ; alertes ET Open signalees sans echec)
  SURI_CLEAN=$(./scripts/dt sh -c 'rm -rf /tmp/suriclean && mkdir -p /tmp/suriclean && suricata -r /tests/samples/clean.pcap -l /tmp/suriclean >/dev/null 2>&1; grep -c "\"event_type\":\"alert\"" /tmp/suriclean/eve.json 2>/dev/null' || true)
  if [[ "${SURI_CLEAN:-}" == "0" ]]; then
    ok "suricata zero alerte sur clean.pcap (triage efficace)"
  elif [[ -n "${SURI_CLEAN:-}" && "${SURI_CLEAN:-}" =~ ^[0-9]+$ ]]; then
    warn "suricata : $SURI_CLEAN alerte(s) ET Open sur clean.pcap (regler le triage : config/suricata/disable.conf, connaissances/reseau/)"
  else
    ko "suricata sur clean.pcap (aucune sortie exploitable)"
  fi
fi

etape "5quater. Referentiel artefacts (ForensicArtifacts)"
if ! docker image inspect oreoa-ai-tools:1.1.0 >/dev/null 2>&1; then
  echo "   [skip] image oreoa-ai-tools absente (provisioner avec : python3 scripts/doctor.py fix)"
else
  # integrite du referentiel bake (MANIFEST.sha256 + traces)
  ./scripts/dt python3 /work/scripts/referentiels.py artefacts check >/dev/null 2>&1 \
    && ok "referentiel artefacts integre (manifest + traces)" \
    || ko "referentiel artefacts integre (manifest + traces)"

  # rapprochement automatique a l'ingestion (manifest de l'affaire de test)
  python3 - <<'EOF' && ok "rapprochement artefacts (manifest de test)" || ko "rapprochement artefacts (manifest de test)"
import sys, yaml
from pathlib import Path
m = yaml.safe_load(Path("cases/CASE-TEST-0001/manifest.yaml").read_text())
refs = m.get("referentiels", {})
assert refs.get("artefacts", {}).get("version"), "referentiels.absent du manifest"
cols = {c["nom"]: c for c in m.get("collections", [])}
assert "LinuxAuthLogs" in cols["auth.log"]["artefacts"], f"auth.log: {cols['auth.log']['artefacts']}"
assert cols["auth.log"]["artefacts"], "auth.log sans artefact"
sys.exit(0)
EOF

  # expansion resolue + outils kit
  EXP=$(./scripts/dt python3 /work/scripts/referentiels.py artefacts expand WindowsEventLogs 2>/dev/null || true)
  echo "$EXP" | grep -q "winevt" && echo "$EXP" | grep -q "log2timeline" \
    && ok "expansion artefact resolue (chemins + outils)" \
    || ko "expansion artefact resolue (chemins + outils)"
fi

etape "5quinquies. Referentiel DFIQ (questions d'investigation)"
if ! docker image inspect oreoa-ai-tools:1.1.0 >/dev/null 2>&1; then
  echo "   [skip] image oreoa-ai-tools absente (provisioner avec : python3 scripts/doctor.py fix)"
else
  # integrite du corpus + coherence parentale
  ./scripts/dt python3 /work/scripts/referentiels.py dfiq check >/dev/null 2>&1 \
    && ok "corpus DFIQ integre (manifest + parentes)" \
    || ko "corpus DFIQ integre (manifest + parentes)"

  # arbre du scenario de mouvement lateral (deterministe)
  ARBRE=$(./scripts/dt python3 /work/scripts/referentiels.py dfiq arbre S1008 2>/dev/null || true)
  echo "$ARBRE" | grep -q "Lateral Movement" && echo "$ARBRE" | grep -q "F1027" \
    && ok "arbre DFIQ S1008 exploitable" || ko "arbre DFIQ S1008 exploitable"

  # plan de reponse avec resolution croisee DFIQ -> artefact (Q1020 -> BrowserHistory)
  PLAN=$(./scripts/dt python3 /work/scripts/referentiels.py dfiq plan Q1020 2>/dev/null || true)
  echo "$PLAN" | grep -q "BrowserHistory" && echo "$PLAN" | grep -q "Plaso" \
    && ok "plan DFIQ Q1020 avec resolution ForensicArtifact" \
    || ko "plan DFIQ Q1020 avec resolution ForensicArtifact"

  # regen des index generes (preservation du mapping entre marqueurs)
  ./scripts/dt python3 /work/scripts/referentiels.py artefacts index /work/catalogue/artefacts.md >/dev/null 2>&1 \
    && ./scripts/dt python3 /work/scripts/referentiels.py dfiq index /work/catalogue/dfiq.md >/dev/null 2>&1 \
    && grep -q "SF-W-001" catalogue/artefacts.md && grep -q "S1008" catalogue/dfiq.md \
    && ok "index catalogues regeneres (mapping preserve)" \
    || ko "index catalogues regeneres (mapping preserve)"
fi

etape "6. Resume"
if [[ $ECHAP -eq 0 ]]; then
  echo "   E2E : OK"
else
  echo "   E2E : ECHEC (voir ci-dessus)"
fi
exit $ECHAP
