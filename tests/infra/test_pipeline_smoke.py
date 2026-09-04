"""T5: pipeline smoke - the real RQ command set against the real Redis ACL.

Run by `make test-infra` (host with Docker). Starts the redis service, then
executes, inside the worker-fast image:

- the full enqueue / work / cancel cycle through the `rq` ACL user (S1.1
  left the command set provisional: this is the validation promised at 1.4);
- a negative ACL check (CONFIG refused);
- one real `oreoa.worker.run_step` execution writing manifest + phase.

The in-container script prints SMOKE OK / SMOKE FAIL: the host cannot read
files created by uid 10001 (umask 027), so assertions run where the data
lives.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from helpers import compose_cmd, image_exists, load_versions_env  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
CASE_ID = "smoke-pipeline-1"

SCRIPT = r'''
import json
import os
import shutil
from pathlib import Path

from oreoa import worker

conn = worker.redis_connection()
assert conn.ping(), "redis ping failed (ACL rq)"

root = Path(os.environ.get("OREOA_CASES", "/cases"))
CASE = "@@CASE_ID@@"
cdir = root / CASE
if not (cdir / "case.yaml").is_file():
    raise SystemExit("SMOKE FAIL: smoke case missing (created on the host)")

from oreoa.manifest_model import Evidence, EvidenceFile, Manifest, load_manifest

manifest = Manifest(
    case_id=CASE,
    evidence=[Evidence(ev_id="EV-901", kind="directory", host="SMOKE",
                       files=[EvidenceFile(path="evidence/x", sha256="a" * 64, size_bytes=1)])],
)
(cdir / "derived").mkdir(exist_ok=True)
(cdir / "derived" / "manifest.json").write_text(manifest.model_dump_json(indent=2))

from rq import Queue, Worker
from rq.job import Job

queue = Queue("fast", connection=conn)
envelope = {"job_type": "hash", "queue": "fast", "case_id": CASE,
            "ev_id": "EV-901", "payload": {}}
job = queue.enqueue("oreoa.worker.run_step", envelope, job_timeout=60,
                    result_ttl=600, failure_ttl=86400)
Worker([queue], connection=conn, name="smoke-burst").work(burst=True)
job.refresh()
result = job.return_value()
if not result or result.get("status") != "ok":
    raise SystemExit(f"SMOKE FAIL: job result {result}")

step = load_manifest(cdir / "derived" / "manifest.json").get_evidence("EV-901").steps["hash"]
if step.status != "ok":
    raise SystemExit(f"SMOKE FAIL: manifest step {step.status}")
phase = json.loads((cdir / "state" / "phase.json").read_text())
if phase["hosts"].get("SMOKE", {}).get("phase") != "fast_done":
    # skeleton rule: every registered fast step ok -> fast_done
    raise SystemExit(f"SMOKE FAIL: phase {phase}")

cancel_me = queue.enqueue("oreoa.worker.run_step",
                          {**envelope, "job_type": "parse"}, job_timeout=60)
cancel_me.cancel()
if Job.fetch(cancel_me.id, connection=conn).get_status() != "canceled":
    raise SystemExit("SMOKE FAIL: cancel")

import redis.exceptions
try:
    conn.config_get("maxmemory")
    raise SystemExit("SMOKE FAIL: CONFIG accepted by the rq ACL (must be denied)")
except redis.exceptions.ResponseError:
    pass

shutil.rmtree(cdir)
print("SMOKE OK")
'''.replace("@@CASE_ID@@", CASE_ID)


@pytest.fixture(scope="module")
def redis_up():
    if not image_exists("oreoa/worker-fast:dev"):
        pytest.skip("image oreoa/worker-fast:dev not built - run make build")
    env = os.environ.copy()
    env.update(load_versions_env())
    up = subprocess.run(
        compose_cmd() + ["up", "-d", "redis"],
        capture_output=True, text=True, env=env, cwd=REPO,
    )
    assert up.returncode == 0, f"redis up failed: {up.stderr}"
    yield
    subprocess.run(
        compose_cmd() + ["rm", "-sf", "redis"],
        capture_output=True, text=True, env=env, cwd=REPO,
    )


@pytest.fixture()
def smoke_case():
    from oreoa.scaffold import scaffold_case

    cases_root = REPO / "cases"
    cases_root.mkdir(exist_ok=True)
    cdir = scaffold_case(cases_root, CASE_ID, "incident")
    # the container (uid 10001, group OREOA_HOST_GID) must read and write the
    # case tree, except evidence/ which stays read-only (T5 6)
    for path in sorted(cdir.rglob("*")):
        if path.is_dir() and path.name == "evidence":
            os.chmod(path, 0o555)
        else:
            os.chmod(path, 0o777 if path.is_dir() else 0o666)
    os.chmod(cdir, 0o777)
    yield cdir
    if (cdir / "evidence").exists():
        os.chmod(cdir / "evidence", 0o755)
    shutil.rmtree(cdir, ignore_errors=True)
    if cdir.exists():
        # container-owned files (worker umask 027) - clean from inside
        subprocess.run(
            compose_cmd()
            + ["run", "--rm", "--no-deps", "--entrypoint", "sh", "worker-fast",
               "-c", f"rm -rf /cases/{CASE_ID}"],
            capture_output=True, cwd=REPO, timeout=120,
        )


def test_rq_cycle_under_acl(redis_up, smoke_case):
    run = subprocess.run(
        compose_cmd()
        + ["run", "--rm", "--no-deps", "--entrypoint", "python", "worker-fast", "-c", SCRIPT],
        capture_output=True, text=True, timeout=180, cwd=REPO,
    )
    assert "SMOKE OK" in run.stdout, f"stdout={run.stdout}\nstderr={run.stderr}"
