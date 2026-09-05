#!/usr/bin/env bash
# Create a case skeleton on the host (docker_build_spec.md 8, case-new).
# Basic version (step 1.1): directories + template copy + permissions.
# The /case command (empty-skeleton derivation, incident/exercise prompt,
# answers.yaml, banner) is the CLI at step 1.2.
set -euo pipefail

ID=""
TYPE="incident"
while [ $# -gt 0 ]; do
    case "$1" in
        --type) TYPE="$2"; shift 2 ;;
        *) ID="$1"; shift ;;
    esac
done
[ -n "$ID" ] || { echo "usage: case_new.sh <case-id> [--type incident|exercice]" >&2; exit 2; }
case "$TYPE" in incident|exercice) ;; *) echo "invalid type: $TYPE" >&2; exit 2 ;; esac

D="cases/$ID"
[ -e "$D" ] && { echo "case already exists: $D" >&2; exit 1; }

mkdir -p "$D/evidence" "$D/derived" "$D/reports" "$D/state/keys"
cp templates/case/case.yaml "$D/case.yaml"
cp templates/case/journal.md "$D/journal.md"
if [ "$TYPE" = "exercice" ]; then
    touch "$D/answers.yaml"   # score-layer only (amendment A2)
fi
chmod -R 750 "$D"
echo "case created: $D ($TYPE) - template copy, personalize case.yaml before use"
