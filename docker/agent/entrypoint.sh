#!/bin/sh
# Agent entrypoint (docker_build_spec.md 3.2): regenerate runtime config from
# the mounted agents/ and commands/ (editing a role prompt needs no rebuild),
# check the case directory exists, then exec the runtime TUI.
set -eu

if command -v oredoa >/dev/null 2>&1; then
    oredoa runtime-config render >/dev/null 2>&1 || true
fi

if [ -n "${OREOA_CASE_ID:-}" ] && [ ! -d "/cases/${OREOA_CASE_ID}" ]; then
    echo "case not found: /cases/${OREOA_CASE_ID}" >&2
    exit 1
fi

exec "$@"
