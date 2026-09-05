#!/bin/sh
# Zircolite launcher (S2.0): the pinned source tree lives at
# /oreoa/zircolite (OREOA_ZIRCOLITE_HOME); its Python deps are installed in
# the worker environment (requirements-worker-fast.lock).
# cwd decides where zircolite.log lands (config_loader.DEFAULT_LOG_FILE is
# relative to cwd); default to the writable tmpfs, override with
# ZIRCOLITE_WORKDIR per evidence in the sigma step (S2.2).
cd "${ZIRCOLITE_WORKDIR:-/tmp}" || exit 1
exec python /oreoa/zircolite/zircolite.py "$@"
