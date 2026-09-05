#!/bin/sh
# Agent entrypoint (docker_build_spec.md 3.2): regenerate runtime config from
# the mounted agents/ and commands/ (editing a role prompt needs no rebuild),
# check the case directory exists, then exec the runtime TUI.
set -eu

# OpenCode global config from the canonical sources (ro mounts).
mkdir -p "${HOME}/.config/opencode"
oreoa runtime-config render \
    --out "${HOME}/.config/opencode" \
    --runtimes opencode --layout global >/dev/null 2>&1 || true

# Claude Code project config lives in the current case directory.
if [ -n "${OREOA_CASE_ID:-}" ]; then
    if [ ! -d "/cases/${OREOA_CASE_ID}" ]; then
        echo "case not found: /cases/${OREOA_CASE_ID}" >&2
        exit 1
    fi
    oreoa runtime-config render --out "/cases/${OREOA_CASE_ID}" \
        --runtimes claude --layout project >/dev/null 2>&1 || true

fi

exec "$@"
