#!/usr/bin/env bash
# install.sh - sante et provisioning du kit OREOA-AI
# Alternative manuelle au parcours agent (l'agent provisionne seul via doctor.py).
# Usage : ./install.sh check | test | fix
set -euo pipefail

KIT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DOCTOR="$KIT_DIR/scripts/doctor.py"

case "${1:-check}" in
  check) exec python3 "$DOCTOR" check ;;
  test)  exec python3 "$DOCTOR" test ;;
  fix)   exec python3 "$DOCTOR" fix ;;
  *)
    echo "Usage : ./install.sh check|test|fix" >&2
    exit 2
    ;;
esac
