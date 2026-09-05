"""T5: detection engines in worker-fast + clamd sidecar (S2.0).

Run by `make test-infra` (host with Docker, after `make build`):

- the pinned engines answer with the versions.env versions: hayabusa banner
  (no --version flag upstream), chainsaw --version, zircolite --version (the
  zircolite run also exercises its full import chain against the pinned
  dependencies);
- engines are root-owned, executable, and not writable by the worker uid;
- the clamav service is wired per docker_build_spec 3.3: internal network
  only, signature db mounted read-only from knowledge/upstream/clamav_db,
  custom config mounted read-only, hardened anchor (user 10001, read_only);
- live smoke (skipped without a local clamav db snapshot): clamd answers a
  PING and reports its version through the pyclamd client.
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from helpers import (  # noqa: E402
    ROOT,
    compose_cmd,
    compose_config,
    image_exists,
    load_versions_env,
    run_in_service,
)

VERSIONS = load_versions_env()
ENGINE_CHECK = r"""
set -eu
hayabusa 2>&1 | grep -q "v${HAYABUSA_VERSION}"
chainsaw --version | grep -q "${CHAINSAW_VERSION}"
zircolite -v 2>&1 | grep -q "${ZIRCOLITE_VERSION}"
for f in /oreoa/hayabusa/hayabusa /oreoa/chainsaw/chainsaw; do
    [ "$(stat -c %U "$f")" = "root" ]
    [ "$(stat -c %U /oreoa/zircolite/zircolite.py)" = "root" ]
    if [ -w "$f" ]; then echo "FAIL: $f writable by worker uid"; exit 1; fi
done
echo ENGINES OK
"""


@pytest.fixture(scope="module")
def worker_fast_image():
    if not image_exists("oreoa/worker-fast:dev"):
        pytest.skip("image oreoa/worker-fast:dev not built - run make build")


def _run_in_worker_fast(script: str, timeout: int = 180) -> subprocess.CompletedProcess:
    """compose run worker-fast with the pinned versions injected as -e flags
    (compose does not forward the host env into the container)."""
    import os

    env = os.environ.copy()
    env.update(VERSIONS)
    cmd = compose_cmd() + ["run", "--rm", "--no-deps", "--entrypoint", "/bin/sh"]
    for key in ("HAYABUSA_VERSION", "CHAINSAW_VERSION", "ZIRCOLITE_VERSION"):
        cmd += ["-e", f"{key}={VERSIONS[key]}"]
    cmd += ["worker-fast", "-c", script]
    return subprocess.run(cmd, capture_output=True, text=True, env=env, cwd=ROOT, timeout=timeout)


def test_engines_versions_and_layout(worker_fast_image):
    run = _run_in_worker_fast(ENGINE_CHECK)
    assert "ENGINES OK" in run.stdout, f"stdout={run.stdout}\nstderr={run.stderr}"


def test_clamav_service_wiring():
    config = compose_config()["services"]
    assert "clamav" in config, "clamd sidecar service missing"
    clamav = config["clamav"]
    assert clamav["image"] == VERSIONS["CLAMAV_IMAGE"]
    assert set(clamav["networks"]) == {"internal"}
    assert clamav.get("read_only") is True
    mounts = {(str(v["source"]), v["target"]) for v in clamav["volumes"]}
    assert any(src.endswith("clamav_db") and tgt == "/var/lib/clamav" for src, tgt in mounts), mounts
    assert any(src.endswith("oreoa-clamd.conf") and tgt == "/etc/clamav/oreoa-clamd.conf" for src, tgt in mounts), mounts
    assert clamav["user"].startswith("10001:")
    entry = " ".join(clamav["entrypoint"])
    assert "clamd" in entry, "clamd must run directly (no freshclam in the service)"
    assert "--foreground" in " ".join(clamav["command"]), "clamd must not daemonize (PID 1)"


@pytest.fixture(scope="module")
def clamav_up():
    db = ROOT / "knowledge" / "upstream" / "clamav_db" / "daily.cvd"
    if not db.is_file():
        pytest.skip("clamav db snapshot missing - run make update-knowledge")
    env = os.environ.copy()
    env.update(load_versions_env())
    up = subprocess.run(
        compose_cmd() + ["up", "-d", "--wait", "clamav"],
        capture_output=True, text=True, env=env, cwd=ROOT, timeout=300,
    )
    assert up.returncode == 0, f"clamav up failed: {up.stderr}"
    yield
    subprocess.run(
        compose_cmd() + ["rm", "-sf", "clamav"],
        capture_output=True, text=True, env=env, cwd=ROOT,
    )


CLAMD_PING = r"""
python - <<'PY'
import time

import pyclamd

cd = pyclamd.ClamdNetworkSocket(host="clamav", port=3310)
for _ in range(40):
    try:
        if cd.ping():
            break
    except Exception:
        pass
    time.sleep(3)
else:
    raise SystemExit("SMOKE FAIL: clamd unreachable on clamav:3310")
version = cd.version()
assert version, "SMOKE FAIL: empty clamd version"
print("SMOKE OK", version)
PY
"""


def test_clamd_live_ping(clamav_up, worker_fast_image):
    run = run_in_service("worker-fast", CLAMD_PING, timeout=300)
    assert "SMOKE OK" in run.stdout, f"stdout={run.stdout}\nstderr={run.stderr}"
