#!/bin/sh
# Worker entrypoint: exec the RQ harness command (compose passes
# `python -m oredoa.worker fast|deep`). Kept as a hook for the deep lane's
# supervising needs at step 2; nothing else runs here (one process class per
# container, docker_build_spec 3.3/3.4).
set -eu
exec "$@"
