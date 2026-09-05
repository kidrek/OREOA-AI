"""T5: fetcher smoke (profile symbol-fetch) - real image, real Redis ACL.

Run by `make test-infra` (host with Docker). Starts the redis service, then
executes inside the fetcher image:

- refusals BEFORE any network call: fetch_symbol without analyst
  confirmation, with a malformed GUID, with an unknown pdb_name, on the
  wrong queue (T5 11 - docker_build_spec 9.11);
- one valid fetch_symbol run with the download/conversion stubbed at the
  function boundary: validates the write path (ISF layout
  windows/<pdb_name>/<GUID>-<age>.json + provenance file) in the mounted
  symbols directory, and the RQ cycle (enqueue / burst worker / result)
  on the `fetch` queue under the rq ACL.

No external network is used: the stub never reaches the proxy.
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
CASE_ID = "smoke-fetch-1"
GUID = "A2C42DD660EC415CBE9D79C2559C015C1"

SCRIPT = r'''
import json
import os
import shutil
from pathlib import Path

from oreoa import fetcher, worker

conn = worker.redis_connection()
assert conn.ping(), "redis ping failed (ACL rq)"

symbols = Path(os.environ["OREOA_SYMBOLS_DIR"])
symbols.mkdir(parents=True, exist_ok=True)

from rq import Queue, Worker
from rq.job import Job

queue = Queue("fetch", connection=conn)

def envelope(pdb="ntkrnlmp.pdb", guid="@@GUID@@", confirmed=True):
    return {"job_type": "fetch_symbol", "queue": "fetch", "case_id": "@@CASE_ID@@",
            "payload": {"pdb_name": pdb, "guid": guid, "confirmed_by_analyst": confirmed}}

# refusals before any network call - the jobs fail with the validation reason
refusals = {
    "unconfirmed": envelope(confirmed=False),
    "malformed-guid": envelope(guid="ZZZZ"),
    "unknown-pdb": envelope(pdb="explorer.pdb"),
    "wrong-queue": {**envelope(), "queue": "fast"},
}
for label, env in refusals.items():
    job = queue.enqueue("oreoa.fetcher.run_fetch_symbol", env, job_timeout=60)
    Worker([queue], connection=conn, name="smoke-burst-refusal").work(burst=True)
    job = Job.fetch(job.id, connection=conn)
    if job.get_status() != "failed":
        raise SystemExit(f"SMOKE FAIL: {label} accepted")
    text = str(getattr(job.latest_result(), "exc_string", "") or "")
    if "confirmed_by_analyst" not in text and label == "unconfirmed":
        raise SystemExit(f"SMOKE FAIL: {label} wrong reason: {text[:200]}")

# valid job, download/conversion stubbed at the function boundary
isf_body = {"metadata": {"windows": {"pdb": {"GUID": "@@GUID32@@", "age": 1}}}, "user_symbols": {}}

def fake_download(url, destination):
    assert url.startswith("https://msdl.microsoft.com/download/symbols/ntkrnlmp.pdb/"), url
    destination.write_bytes(b"stub-pdb")

def fake_convert(pdb_path, isf_path):
    isf_path.write_text(json.dumps(isf_body), encoding="utf-8")

fetcher.download_pdb = fake_download
fetcher.convert_to_isf = fake_convert

job = queue.enqueue("oreoa.fetcher.run_fetch_symbol", envelope(), job_timeout=60)
Worker([queue], connection=conn, name="smoke-burst-valid").work(burst=True)
job = Job.fetch(job.id, connection=conn)
if job.get_status() != "finished":
    raise SystemExit(f"SMOKE FAIL: valid job {job.get_status()}: {getattr(job.latest_result(), 'exc_string', '')}")
result = job.return_value()
isf = Path(result["isf_path"])
if not isf.is_file() or not isf.parent.name == "ntkrnlmp.pdb" or isf.parent.parent.name != "windows":
    raise SystemExit(f"SMOKE FAIL: ISF layout {isf}")
prov = json.loads(Path(result["provenance"]).read_text())
for key in ("source_url", "sha256_isf", "sha256_pdb", "job_id", "confirmed_by", "fetched_at"):
    if key not in prov:
        raise SystemExit(f"SMOKE FAIL: provenance missing {key}")

shutil.rmtree(symbols / "windows")  # contents only: the mount point stays
print("SMOKE OK")
'''.replace("@@GUID32@@", GUID[:32]).replace("@@GUID@@", GUID).replace("@@CASE_ID@@", CASE_ID)


@pytest.fixture(scope="module")
def redis_up():
    if not image_exists("oreoa/fetcher:dev"):
        pytest.skip("image oreoa/fetcher:dev not built - run make build")
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


def test_fetcher_cycle_and_refusals(redis_up):
    run = subprocess.run(
        compose_cmd(["symbol-fetch"])
        + ["run", "--rm", "--no-deps", "--entrypoint", "python", "fetcher", "-c", SCRIPT],
        capture_output=True, text=True, timeout=180, cwd=REPO,
    )
    assert "SMOKE OK" in run.stdout, f"stdout={run.stdout}\nstderr={run.stderr}"


def test_fetcher_compose_wiring():
    """The fetcher service talks to Redis through the rq ACL user and has no
    other egress than the proxy-fetch allow-list (docker_build_spec 3.6)."""
    from helpers import compose_config

    config = compose_config(["symbol-fetch"])["services"]["fetcher"]
    env = config["environment"]
    assert env["REDIS_HOST"] == "redis"
    assert env["HTTPS_PROXY"] == "http://proxy-fetch:8888"
    secrets = {s["source"] for s in (config.get("secrets") or [])}
    assert "redis_password" in secrets
    networks = config["networks"]
    assert "internal" in networks and "external" not in networks
    assert "fetcher" in " ".join(config["command"])
    volumes = " ".join(str(v) for v in config["volumes"])
    assert "volatility_symbols" in volumes
