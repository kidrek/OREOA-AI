#!/bin/sh
# Worker entrypoint placeholder: the RQ harness (queues fast/deep, per-step
# job_timeout, manifest/phase writes) is wired at work-order step 1.4.
set -eu
echo "oreoa worker harness: Redis/RQ wiring lands at work-order step 1.4" >&2
exec "$@"
