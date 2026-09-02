#!/usr/bin/env bash
# create_case.sh - scaffold d'un dossier d'affaire dans cases/
# Usage : ./create_case.sh [--id CASE-2026-0042] "Nom de l'affaire"
set -euo pipefail

KIT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CASES_DIR="$KIT_DIR/cases"

ID=""
ARGS=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    --id)
      ID="${2:-}"
      shift 2
      ;;
    *)
      ARGS+=("$1")
      shift
      ;;
  esac
done

NOM="${ARGS[*]:-}"
if [[ -z "$NOM" ]]; then
  echo "Erreur : nom d'affaire requis." >&2
  echo "Usage : ./create_case.sh [--id CASE-2026-0042] \"Nom de l'affaire\"" >&2
  exit 2
fi

# Identifiant par defaut : CASE-YYYY-NNNN (proxime numero libre)
if [[ -z "$ID" ]]; then
  ANNEE="$(date +%Y)"
  N=1
  while [[ -e "$CASES_DIR/CASE-$ANNEE-$(printf '%04d' "$N")" ]]; do
    N=$((N+1))
  done
  ID="CASE-$ANNEE-$(printf '%04d' "$N")"
fi

CASE_DIR="$CASES_DIR/$ID"
if [[ -e "$CASE_DIR" ]]; then
  echo "Erreur : l'affaire $ID existe deja ($CASE_DIR)." >&2
  exit 1
fi

mkdir -p "$CASE_DIR"/{00_evidence/{originals,exports},01_work/tmp,02_analysis/{logs,ioc,report}}

cat > "$CASE_DIR/manifest.yaml" <<EOF
affaire:
  id: "$ID"
  nom: "$NOM"
  date_creation: "$(date +%F)"
  statut: ouverte
collections: []
EOF

cat > "$CASE_DIR/journal.md" <<EOF
# Journal - $ID

Affaire : $NOM
Ouverture : $(date '+%F %T')

---

## Phase 0 - Import

- $(date '+%F %T') -- Dossier d'affaire cree par create_case.sh
EOF

echo "Affaire $ID creee : $CASE_DIR"
