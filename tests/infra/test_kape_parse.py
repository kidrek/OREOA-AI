"""T5: KAPE quick parsers in the real worker-fast image (S2.1).

Run by `make test-infra` (host with Docker, after `make build`):

- ``mappings/kape/`` is baked into the image (read-only, S1.6 contract) and
  carries the three lossless mappings;
- ``oreoa.parse_kape`` imports in the pinned image;
- one real ``worker.run_step`` parse of a T0 KAPE archive inside the
  container writes Parquet + DuckDB and the manifest step is ``ok`` with the
  kape parser summary (S2.1 dispatch by evidence kind).

The in-container script prints SMOKE OK / SMOKE FAIL: assertions run where
the data lives (uid 10001 files are not host-readable, umask 027).
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
CASE_ID = "smoke-kape-1"

MAPPINGS_CHECK = r"""
set -eu
test -f /oreoa/mappings/kape/kape.MFT.yaml
test -f /oreoa/mappings/kape/kape.USN.yaml
test -f /oreoa/mappings/kape/kape.Amcache.yaml
python - <<'PY'
from oreoa import parse_kape

assert parse_kape.PARSER_VERSION == "1.0.0"
assert set(parse_kape.CSV_ARTIFACTS.values()) == {"kape.MFT", "kape.USN", "kape.Amcache"}
print("SMOKE OK")
PY
"""

PARSE_CHECK = r"""
import hashlib
import os
import shutil
from pathlib import Path

from oreoa import worker
from oreoa.manifest_model import Evidence, EvidenceFile, Manifest, load_manifest

root = Path(os.environ.get("OREOA_CASES", "/cases"))
CASE = "@@CASE_ID@@"
cdir = root / CASE
if not (cdir / "case.yaml").is_file():
    raise SystemExit("SMOKE FAIL: smoke case missing (created on the host)")

archive = cdir / "evidence" / "win-workstation-01.kape.zip"
sha = hashlib.sha256(archive.read_bytes()).hexdigest()
manifest = Manifest(
    case_id=CASE,
    evidence=[Evidence(ev_id="EV-901", kind="archive_kape", host="WKS-042",
                       files=[EvidenceFile(path="evidence/win-workstation-01.kape.zip", sha256=sha)])],
)
(cdir / "derived").mkdir(exist_ok=True)
(cdir / "derived" / "manifest.json").write_text(manifest.model_dump_json(indent=2))

result = worker.run_step({
    "job_type": "parse", "queue": "fast", "case_id": CASE, "ev_id": "EV-901",
    "payload": {"case_id": CASE, "ev_id": "EV-901"},
})
if result["status"] != "ok":
    raise SystemExit(f"SMOKE FAIL: parse step {result['status']}: {result['error']}")

step = load_manifest(cdir / "derived" / "manifest.json").get_evidence("EV-901").steps["parse"]
details = step.details
if details.get("parser") != "kape/1.0.0" or not details.get("rows"):
    raise SystemExit(f"SMOKE FAIL: parse details {details}")

from oreoa import db

con = db.connect(cdir)
families = {
    "fs_entries": "select count(*) from fs_entries where source_tool = 'kape' and name = 'upd.exe'",
    "fs_journal": "select count(*) from fs_journal where source_tool = 'kape' and name = 'docs.7z'",
    "executions": "select count(*) from executions where evidence_type = 'amcache'",
}
for family, sql in families.items():
    count = con.execute(sql).fetchone()[0]
    if count < 1:
        raise SystemExit(f"SMOKE FAIL: {family} planted rows missing ({count})")
con.close()
# evidence/ is read-only for the worker (T5 6): the container removes only
# what it created; the host fixture teardown owns evidence/ and cdir.
import shutil

for child in sorted(cdir.iterdir()):
    if child.name == "evidence":
        continue
    if child.is_dir():
        shutil.rmtree(child)
    else:
        child.unlink()
print("SMOKE OK")
""".replace("@@CASE_ID@@", CASE_ID)


@pytest.fixture(scope="module")
def worker_fast_image():
    if not image_exists("oreoa/worker-fast:dev"):
        pytest.skip("image oreoa/worker-fast:dev not built - run make build")


@pytest.fixture()
def smoke_case():
    from oreoa.corpus_gen import kape
    from oreoa.corpus_gen.scenario import load_scenarios
    from oreoa.scaffold import scaffold_case

    cases_root = REPO / "cases"
    cases_root.mkdir(exist_ok=True)
    cdir = scaffold_case(cases_root, CASE_ID, "incident")
    scenario = next(s for s in load_scenarios(REPO / "corpus" / "scenarios") if s.name == "win-workstation-01")
    evidence_dir = cdir / "evidence"
    evidence_dir.chmod(0o755)
    kape.build_archive(scenario, evidence_dir / "win-workstation-01.kape.zip")
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


def test_kape_mappings_baked(worker_fast_image):
    run = subprocess.run(
        compose_cmd()
        + ["run", "--rm", "--no-deps", "--entrypoint", "/bin/sh", "worker-fast", "-c", MAPPINGS_CHECK],
        capture_output=True, text=True, timeout=120, cwd=REPO,
    )
    assert "SMOKE OK" in run.stdout, f"stdout={run.stdout}\nstderr={run.stderr}"


def test_kape_parse_in_container(worker_fast_image, smoke_case):
    run = subprocess.run(
        compose_cmd()
        + ["run", "--rm", "--no-deps", "--entrypoint", "python", "worker-fast", "-c", PARSE_CHECK],
        capture_output=True, text=True, timeout=300, cwd=REPO,
    )
    assert "SMOKE OK" in run.stdout, f"stdout={run.stdout}\nstderr={run.stderr}"
