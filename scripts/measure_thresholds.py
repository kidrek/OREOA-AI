"""A3 measurement spike (work-order step 1.7, SPEC amendment A3).

Measures the current fast lane against the T0 Windows corpus, inside the
real ``worker-fast`` container (production posture: compose run, Redis ACL,
RQ burst drain) and writes a JSON report to ``evaluation/local/``.

Perimeter at S1.7 (honest measurement, not a projection):

- ``hash`` / ``detect`` / ``inventory`` are skeleton steps (no handler yet -
  run through the full RQ round trip and return ``ok`` with a note);
- ``parse`` is the only implemented handler: real work for
  ``archive_velociraptor``, explicit ``SkipStep`` for other kinds;
- ``sigma`` / ``yara`` / ``clamav`` / ``events`` / ``hunts`` /
  ``rank_signals`` land at work-order step 2 - the lane is re-measured there
  and thresholds recalibrated by PR (A3).

Threshold recalibration is never done by this script: it only produces the
raw report; a re-baseline PR copies the accepted numbers into the
``measured`` block of ``evaluation/thresholds.yaml``.

Usage: python3 scripts/measure_thresholds.py [--keep-case] [--report PATH]
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

CASE_ID = "measure-thresholds-1"
STEP_TODAY = ("hash", "detect", "inventory", "parse")

# {ev_id: (scenario, file, kind, host)} - order matters only for readability.
EV_MAP = {
    "EV-901": ("win-workstation-01", "win-workstation-01.velociraptor.zip", "archive_velociraptor"),
    "EV-902": ("win-workstation-01", "win-workstation-01.kape.zip", "archive_kape"),
    "EV-903": ("win-workstation-01", "win-workstation-01.disk.img", "disk_image"),
    "EV-904": ("clean-host-01", "clean-host-01.velociraptor.zip", "archive_velociraptor"),
    "EV-905": ("clean-host-01", "clean-host-01.kape.zip", "archive_kape"),
}

IN_CONTAINER = r'''
import json, time
from pathlib import Path

from oreoa import worker

conn = worker.redis_connection()
assert conn.ping(), "redis ping failed (ACL rq)"

CASE = "@@CASE_ID@@"
cdir = worker.case_dir(CASE)
manifest = worker._load_manifest(cdir)

from rq import Queue, Worker

queue = Queue("fast", connection=conn)
steps = ("hash", "detect", "inventory", "parse")
envelopes = [
    {"job_type": s, "queue": "fast", "case_id": CASE, "ev_id": ev.ev_id, "payload": {}}
    for ev in sorted(manifest.evidence, key=lambda e: e.ev_id)
    for s in steps
]
t_enqueue0 = time.perf_counter()
jobs = [queue.enqueue("oreoa.worker.run_step", e, job_timeout=600,
                      result_ttl=600, failure_ttl=86400) for e in envelopes]
t_enqueue_s = time.perf_counter() - t_enqueue0
print(f"DIAG enqueued {len(jobs)} jobs, queue count {queue.count}")

w = Worker([queue], connection=conn, name="measure-burst")
t_lane0 = time.perf_counter()
w.work(burst=True)
t_lane_s = time.perf_counter() - t_lane0
print(f"DIAG burst done, queue count {queue.count}, "
      f"failed {queue.failed_job_registry.count}")

manifest = worker._load_manifest(cdir)
rows, failures = [], []
for evidence in sorted(manifest.evidence, key=lambda e: e.ev_id):
    for name in steps:
        step = evidence.steps.get(name)
        if step is None:
            failures.append(f"{evidence.ev_id}:{name}=missing")
            continue
        if step.status not in ("ok", "skipped"):
            failures.append(f"{evidence.ev_id}:{name}={step.status} {step.error[:120]}")
        handler_s = 0.0
        if step.started_at and step.finished_at:
            handler_s = (step.finished_at - step.started_at).total_seconds()
        rows.append({
            "ev_id": evidence.ev_id,
            "kind": evidence.kind,
            "host": evidence.host,
            "job_type": name,
            "status": step.status,
            "handler_s": round(handler_s, 4),
            "note": (step.details or {}).get("note", "")[:200],
        })

duckdb = cdir / "derived" / "case.duckdb"
parquet = sorted((cdir / "derived").glob("*/parquet/*.parquet"))
payload = {
    "enqueue_s": round(t_enqueue_s, 4),
    "lane_wall_s": round(t_lane_s, 4),
    "duckdb_bytes": duckdb.stat().st_size if duckdb.is_file() else 0,
    "parquet_bytes": sum(p.stat().st_size for p in parquet),
    "parquet_files": len(parquet),
    "steps": rows,
    "failures": failures,
}
print("MEASURE " + json.dumps(payload))
'''.replace("@@CASE_ID@@", CASE_ID)


def compose_cmd() -> list[str]:
    return [
        "docker", "compose", "--env-file", str(ROOT / ".env.example"),
        "-f", str(ROOT / "compose.yaml"),
    ]


def compose_env() -> dict[str, str]:
    env = os.environ.copy()
    for line in (ROOT / "versions.env").read_text().splitlines():
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            env.setdefault(k, v)
    return env


def git_sha() -> str:
    return subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT,
                          capture_output=True, text=True).stdout.strip()


def build_case() -> Path:
    """Scaffold the measurement case and register the corpus artifacts."""
    corpus_manifest = json.loads((ROOT / "corpus" / "corpus_manifest.json").read_text())
    artifacts = {Path(a["file"]).name: a for a in corpus_manifest["artifacts"]}

    from oreoa.manifest_model import Evidence, EvidenceFile, Manifest, save_manifest
    from oreoa.scaffold import scaffold_case

    cases_root = ROOT / "cases"
    cases_root.mkdir(exist_ok=True)
    cdir = scaffold_case(cases_root, CASE_ID, "incident")

    evidence = []
    for ev_id, (scenario, file_name, kind) in sorted(EV_MAP.items()):
        artifact = artifacts[file_name]
        src = ROOT / "corpus" / artifact["file"]
        if not src.is_file():
            shutil.rmtree(cdir, ignore_errors=True)
            raise SystemExit(
                f"missing corpus artifact {src} - run `make corpus` first"
            )
        dst = cdir / "evidence" / file_name
        shutil.copy2(src, dst)
        evidence.append(Evidence(
            ev_id=ev_id, kind=kind, host=scenario,
            container_format="raw" if kind == "disk_image" else None,
            files=[EvidenceFile(path=f"evidence/{file_name}",
                                sha256=artifact["sha256"],
                                size_bytes=artifact["size_bytes"])],
        ))

    # container (uid 10001) must read evidence and write the rest of the tree
    for path in sorted(cdir.rglob("*")):
        if path.is_file():
            os.chmod(path, 0o444 if path.parent.name == "evidence" else 0o666)
        else:
            os.chmod(path, 0o555 if path.name == "evidence" else 0o777)
    os.chmod(cdir, 0o777)

    (cdir / "derived").mkdir(exist_ok=True)
    os.chmod(cdir / "derived", 0o777)
    manifest = Manifest(case_id=CASE_ID, evidence=evidence)
    save_manifest(cdir / "derived" / "manifest.json", manifest)
    return cdir


def teardown(cdir: Path) -> None:
    os.chmod(cdir / "evidence", 0o755)
    shutil.rmtree(cdir, ignore_errors=True)
    if cdir.exists():
        subprocess.run(
            compose_cmd() + ["run", "--rm", "--no-deps", "--entrypoint", "sh",
                             "worker-fast", "-c", f"rm -rf /cases/{CASE_ID}"],
            capture_output=True, cwd=ROOT, timeout=120, env=compose_env(),
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="A3 thresholds measurement spike")
    parser.add_argument("--keep-case", action="store_true", help="keep the scratch case")
    parser.add_argument("--report", default="", help="report path (default evaluation/local/)")
    args = parser.parse_args(argv)

    image = "oreoa/worker-fast:dev"
    if subprocess.run(["docker", "image", "inspect", image],
                      capture_output=True).returncode != 0:
        raise SystemExit(f"image {image} not built - run `make build` first")

    cdir = build_case()
    report: dict = {}
    try:
        up = subprocess.run(compose_cmd() + ["up", "-d", "redis"], cwd=ROOT,
                            capture_output=True, text=True, env=compose_env(),
                            timeout=120)
        if up.returncode != 0:
            raise SystemExit(f"redis up failed: {up.stderr}")

        run = subprocess.run(
            compose_cmd() + ["run", "--rm", "--no-deps", "--entrypoint", "python",
                             "worker-fast", "-c", IN_CONTAINER],
            capture_output=True, text=True, timeout=600, cwd=ROOT, env=compose_env(),
        )
        if run.returncode != 0:
            raise SystemExit(f"worker run failed:\n{run.stdout}\n{run.stderr}")
        line = next((l for l in run.stdout.splitlines() if l.startswith("MEASURE ")), None)
        if line is None:
            raise SystemExit(f"no MEASURE line in output:\n{run.stdout}\n{run.stderr}")
        report = json.loads(line.removeprefix("MEASURE "))
        if report["failures"]:
            raise SystemExit(
                f"step failures: {report['failures']}\n"
                f"container stdout tail:\n{run.stdout[-2000:]}\n"
                f"container stderr tail:\n{run.stderr[-2000:]}"
            )
    finally:
        subprocess.run(compose_cmd() + ["rm", "-sf", "redis"], cwd=ROOT,
                       capture_output=True, env=compose_env(), timeout=120)
        if not args.keep_case:
            teardown(cdir)

    totals: dict[str, float] = {}
    for row in report["steps"]:
        totals[row["job_type"]] = totals.get(row["job_type"], 0.0) + row["handler_s"]

    full = {
        "schema_version": 1,
        "measured_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "git_sha": git_sha(),
        "case_id": CASE_ID,
        "method": "compose run worker-fast (real Redis ACL + RQ burst drain, "
                  "concurrency 1) over the T0 corpus evidences",
        "perimeter": {
            "steps": list(STEP_TODAY),
            "notes": [
                "hash/detect/inventory are skeleton steps (no handler yet): "
                "measured wall includes the full RQ round trip, no tool work",
                "parse is real for archive_velociraptor, explicit SkipStep "
                "for archive_kape/disk_image",
                "sigma/yara/clamav/events/hunts/rank_signals land at step 2 - "
                "re-measure there before relying on these numbers",
            ],
        },
        **report,
        "totals_by_step_s": {k: round(v, 4) for k, v in sorted(totals.items())},
    }
    report_path = Path(args.report) if args.report else (
        ROOT / "evaluation" / "local"
        / f"thresholds_spike_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.json"
    )
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(full, indent=2) + "\n")

    print(f"report: {report_path}")
    print(f"lane wall: {full['lane_wall_s']}s (enqueue {full['enqueue_s']}s)")
    print(f"duckdb: {full['duckdb_bytes']} B | parquet: {full['parquet_bytes']} B "
          f"({full['parquet_files']} files)")
    print(f"{'ev':8} {'kind':22} {'step':10} {'status':8} {'handler_s':>10}  note")
    for row in report["steps"]:
        print(f"{row['ev_id']:8} {row['kind']:22} {row['job_type']:10} "
              f"{row['status']:8} {row['handler_s']:>10.4f}  {row['note'][:60]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
