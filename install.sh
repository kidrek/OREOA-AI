#!/usr/bin/env bash
# install.sh - bootstrap du kit DFIR Agent Kit
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
