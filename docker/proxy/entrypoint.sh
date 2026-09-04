#!/bin/sh
# Allow-list forward proxy entrypoint (docker_build_spec.md 3.7).
# Renders the allow.list from LLM_ENDPOINTS (space-separated host:port),
# then runs tinyproxy in the foreground with default-deny filtering.
set -eu

ALLOW=/tmp/allow.list
: > "$ALLOW"
for ep in ${LLM_ENDPOINTS:-}; do
    printf '%s\n' "$ep" >> "$ALLOW"
done

sed -e "s|@ALLOW_LIST@|${ALLOW}|g" /etc/tinyproxy/tinyproxy.conf.template > /tmp/tinyproxy.conf

exec tinyproxy -d -c /tmp/tinyproxy.conf
