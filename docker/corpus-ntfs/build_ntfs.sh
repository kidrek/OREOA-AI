#!/bin/sh
# OREOA-AI corpus-ntfs one-shot entrypoint (S1.6, pattern ClamAV S1.5).
# Runs as the host user (--user): mkntfs + ntfscp on regular files, no mount,
# no privileged container. Reads /work/plan.txt (lines: name<TAB>srcfile,
# staged by the host) and writes /work/<out> (sparse NTFS, <size_mb> MB).
set -eu

SIZE_MB="${1:-64}"
OUT="${2:-disk.img}"
PLAN=/work/plan.txt
IMG="/work/$OUT"

[ -f "$PLAN" ] || { echo "missing $PLAN" >&2; exit 2; }
cd /work
rm -f "$OUT"

SECTORS=$((SIZE_MB * 2048))
truncate -s "${SIZE_MB}M" "$OUT"
mkntfs --force --quick --label OREOA "$OUT" "$SECTORS" >/dev/null

COUNT=0
while IFS="$(printf '\t')" read -r NAME SRC; do
    [ -n "$NAME" ] || continue
    ntfscp -f "$OUT" "$SRC" "$NAME" >/dev/null
    COUNT=$((COUNT + 1))
done < "$PLAN"

echo "ntfs image ready: $OUT ($SIZE_MB MB, $COUNT files)"
