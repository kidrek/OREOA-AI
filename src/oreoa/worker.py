"""RQ worker harness (SPEC "Pipeline (jobs, not agents)"; docker_build_spec 5b).

One job per pipeline step, executed by RQ workers on queues ``fast`` and
``deep`` (queue ``fetch`` belongs to the fetcher service, profile
symbol-fetch, work-order step 1.5). Every step:

- revalidates its :class:`~oreoa.jobs_model.JobEnvelope` at execution time
  (the payload was validated in mcp-jobs before enqueue, defence in depth);
- rewrites ``derived/manifest.json`` (step status, A1: workers are the only
  writers) and derives ``state/phase.json`` from it (one write per step);
- refuses to run when ``evidence/`` is writable (compose-override defence,
  docker_build_spec 4 / T5 6).

Fast-lane completion notification (SPEC 104): when every fast step
registered for all evidences of a host is ``ok``, the host phase becomes
``fast_done`` and a single ``[pipeline]`` line is appended to ``journal.md``
(state-based notification - the analyst/roles read state through MCP; no
pub/sub). The ``triage`` role is then triggered by the analyst / ingest role
seeing the phase. Step implementations are work-order step 2+: this harness
ships the plumbing with explicit placeholder handlers.

Concurrency: replicas are set at launch time (``make up`` passes
``--scale worker-fast=$WORKER_FAST_REPLICAS``). Shared writes
(manifest/phase/journal) are serialized per case by an advisory ``flock`` on
``state/.locks/case.lock``.
"""

from __future__ import annotations

import contextlib
import fcntl
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from oreoa.jobs_model import FAST_STEPS, JobEnvelope
from oreoa.vocab import CASE_ID_PATTERN

LANES = ("fast", "deep", "fetch")
PHASES = ("dropped", "inventoried", "fast_done", "triaged", "deep_done", "reviewed")

MANIFEST_PATH = Path("derived/manifest.json")
PHASE_PATH = Path("state/phase.json")
LOCK_PATH = Path("state/.locks/case.lock")

DEFAULT_STEP_TIMEOUTS: dict[str, int] = {
    # seconds - SPEC examples (docker_build_spec 5b): hash 10m, extract 60m,
    # plaso 6h, volatility 2h; others are skeleton defaults, overridden by
    # packs/<os>/pipeline.yaml when packs land (work-order step 2).
    "hash": 600,
    "detect": 900,
    "inventory": 900,
    "extract": 3600,
    "extract_unitary": 3600,
    "parse": 1800,
    "sigma": 1800,
    "yara": 1800,
    "clamav": 1800,
    "events": 900,
    "hunts": 900,
    "rank_signals": 600,
    "dissect": 21600,
    "plaso": 21600,
    "volatility": 7200,
    "binary_triage": 7200,
    "vss": 3600,
    "unlock": 1800,
    "fetch_symbol": 1800,
}

RESULT_TTL = 600
FAILURE_TTL = 86400


def step_timeout(job_type: str, packs_dir: Path | None = None) -> int:
    """Timeout for a step: override file, else default.

    ``packs_dir`` holds ``pipeline.yaml`` (``packs/<os>/`` once the OS is
    detected at step 2; a global override until then).
    """
    if packs_dir is not None:
        pipeline = Path(packs_dir) / "pipeline.yaml"
        if pipeline.is_file():
            import yaml

            overrides = yaml.safe_load(pipeline.read_text(encoding="utf-8")) or {}
            timeouts = overrides.get("timeouts") or {}
            if job_type in timeouts:
                return int(timeouts[job_type])
    return DEFAULT_STEP_TIMEOUTS[job_type]


def cases_root() -> Path:
    return Path(os.environ.get("OREOA_CASES", "cases")).resolve()


def case_dir(case_id: str) -> Path:
    """Resolve a case directory strictly under the cases root (T5 9)."""
    if not re.fullmatch(CASE_ID_PATTERN, case_id):
        raise ValueError(f"invalid case id {case_id!r}")
    root = cases_root()
    resolved = (root / case_id).resolve()
    if resolved.parent != root:
        raise ValueError(f"case id {case_id!r} escapes the cases root")
    if not resolved.is_dir():
        raise FileNotFoundError(f"unknown case {case_id!r}")
    return resolved


@contextlib.contextmanager
def case_lock(cdir: Path):
    """Advisory per-case lock serializing manifest/phase/journal writes."""
    lock_file = cdir / LOCK_PATH
    lock_file.parent.mkdir(parents=True, exist_ok=True)
    with open(lock_file, "a+") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def assert_evidence_readonly(cdir: Path) -> None:
    """Refuse to run if evidence/ is writable (docker_build_spec 4, T5 6)."""
    evidence = cdir / "evidence"
    if not evidence.is_dir():
        return
    probe = evidence / ".oreoa_ro_probe"
    try:
        probe.write_text("probe")
    except OSError:
        return
    probe.unlink(missing_ok=True)
    raise PermissionError(
        f"{evidence} is writable; refusing to run (compose override defect, "
        "evidence must be read-only)"
    )


def utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _manifest_path(cdir: Path) -> Path:
    return cdir / MANIFEST_PATH


def _load_manifest(cdir: Path):
    from oreoa.manifest_model import load_manifest

    path = _manifest_path(cdir)
    if not path.is_file():
        raise FileNotFoundError(
            f"no manifest at {path} (evidence is registered by /ingest, step 2)"
        )
    return load_manifest(path)


def _save_manifest(cdir: Path, manifest) -> None:
    from oreoa.manifest_model import save_manifest

    manifest.updated_at = utc_now()
    save_manifest(_manifest_path(cdir), manifest)


def journal_append(cdir: Path, line: str) -> None:
    """Append-only journal line (UTC, role tag). Workers own [pipeline]."""
    stamp = utc_now().strftime("%H:%M:%SZ")
    with open(cdir / "journal.md", "a", encoding="utf-8") as handle:
        handle.write(f"- {stamp} [pipeline] {line}\n")


def _fast_complete(steps: dict) -> bool:
    """Fast lane done for an evidence: every registered fast step is ok."""
    registered = [name for name in steps if name in FAST_STEPS]
    return bool(registered) and all(steps[name].status == "ok" for name in registered)


def sync_phase(cdir: Path, manifest) -> list[str]:
    """Derive ``state/phase.json`` from the manifest (one write per step).

    Returns the notification lines to journal. Host mapping comes from
    ``case.yaml`` (machines[].evidence_ids); evidences not bound to a machine
    are grouped under their ``host`` field or ``_unbound``.
    """
    per_host: dict[str, list[str]] = {}
    for evidence in manifest.evidence:
        host = evidence.host or "_unbound"
        per_host.setdefault(host, []).append(evidence.ev_id)

    import yaml

    meta = yaml.safe_load((cdir / "case.yaml").read_text(encoding="utf-8")) or {}
    ev_host: dict[str, str] = {}
    for machine in meta.get("machines") or []:
        for ev_id in machine.get("evidence_ids") or []:
            ev_host[ev_id] = machine.get("hostname") or host_of(manifest, ev_id)

    phases: dict[str, dict] = {}
    notifications: list[str] = []
    previous = _load_phase(cdir)
    for host, ev_ids in per_host.items():
        host_name = next(
            (h for ev in ev_ids if (h := ev_host.get(ev))), host
        )
        missing: list[str] = []
        all_fast_done = True
        for ev_id in ev_ids:
            evidence = manifest.get_evidence(ev_id)
            for name in FAST_STEPS:
                step = evidence.steps.get(name)
                if step is not None and step.status != "ok":
                    missing.append(f"{ev_id}:{name}={step.status}")
            if not _fast_complete(evidence.steps):
                all_fast_done = False
        phase = "fast_done" if all_fast_done else "dropped"
        phases[host_name] = {"phase": phase, "missing": missing}
        previous_phase = (previous.get("hosts") or {}).get(host_name, {}).get("phase")
        if phase == "fast_done" and previous_phase != "fast_done":
            notifications.append(
                f"fast lane complete for {host_name} ({', '.join(sorted(ev_ids))}); "
                "triage may run (/triage)"
            )

    payload = {"hosts": phases, "updated_at": utc_now().isoformat(timespec="seconds") + "Z"}
    path = cdir / PHASE_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    os.replace(tmp, path)
    return notifications


def host_of(manifest, ev_id: str) -> str:
    try:
        return manifest.get_evidence(ev_id).host or "_unbound"
    except KeyError:
        return "_unbound"


def _load_phase(cdir: Path) -> dict:
    path = cdir / PHASE_PATH
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def run_step(envelope: dict) -> dict:
    """RQ job entrypoint: execute one pipeline step for one evidence.

    Registered as the callable for every enqueue; validates the envelope
    again at execution. Returns a JSON-serializable summary (RQ result,
    visible through mcp-jobs status/wait).
    """
    env = JobEnvelope.model_validate(envelope)
    cdir = case_dir(env.case_id)
    assert_evidence_readonly(cdir)
    if env.ev_id is None:
        raise ValueError(f"job_type {env.job_type!r} requires ev_id")

    with case_lock(cdir):
        manifest = _load_manifest(cdir)
        evidence = manifest.get_evidence(env.ev_id)
        step = evidence.steps.get(env.job_type)
        from oreoa.manifest_model import StepResult

        if step is None:
            step = StepResult(status="running")
            evidence.steps[env.job_type] = step
        step.status = "running"
        step.started_at = utc_now()
        step.finished_at = None
        step.error = ""
        _save_manifest(cdir, manifest)

    details: dict = {}
    try:
        handler = HANDLERS.get(env.job_type)
        if handler is not None:
            details = handler(cdir, env) or {}
        else:
            details = {
                "note": f"step {env.job_type!r} lands at work-order step 2+ "
                "(skeleton harness only)"
            }
        status, error = "ok", ""
    except Exception as exc:  # noqa: BLE001 - failure is a manifest status
        status, error, details = "failed", f"{type(exc).__name__}: {exc}", {}

    with case_lock(cdir):
        manifest = _load_manifest(cdir)
        step = manifest.get_evidence(env.ev_id).steps[env.job_type]
        step.status = status
        step.error = error
        step.details = details
        step.finished_at = utc_now()
        _save_manifest(cdir, manifest)
        notifications = sync_phase(cdir, manifest)
        for note in notifications:
            journal_append(cdir, note)

    return {
        "case_id": env.case_id,
        "ev_id": env.ev_id,
        "job_type": env.job_type,
        "status": status,
        "error": error,
        "notifications": notifications,
    }


HANDLERS: dict[str, Callable] = {}
# Step implementations land at work-order step 2+ (fast lane parsers, deep
# lane tools, unlock); unlisted steps run the harness placeholder and report
# it in their manifest details.


def redis_connection():
    """Redis connection from REDIS_HOST/REDIS_PORT + docker secret file.

    ``decode_responses=False`` (redis-py default): RQ stores binary/compressed
    job payloads (HGETALL on a job key returns them); callers decode their own
    strings explicitly.
    """
    import redis

    password_file = os.environ.get("REDIS_PASSWORD_FILE", "")
    password = Path(password_file).read_text(encoding="utf-8").strip() if password_file else ""
    return redis.Redis(
        host=os.environ.get("REDIS_HOST", "redis"),
        port=int(os.environ.get("REDIS_PORT", "6379")),
        password=password,
        username="rq",
    )


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if len(argv) != 1 or argv[0] not in LANES:
        print(f"usage: python -m oreoa.worker {'|'.join(LANES)}", file=sys.stderr)
        return 2
    lane = argv[0]
    if lane == "fetch":
        print(
            "queue 'fetch' is served by the fetcher service (profile "
            "symbol-fetch, work-order step 1.5); fast/deep workers refuse it",
            file=sys.stderr,
        )
        return 1

    from redis import Redis
    from rq import Queue, Worker

    connection = redis_connection()
    worker = Worker(
        [Queue(lane, connection=connection)],
        connection=connection,
        name=f"oreoa-{lane}-{os.getpid()}",
    )
    print(f"oreoa worker {worker.name} listening on queue {lane!r}", flush=True)
    worker.work(burst=False)
    return 0


if __name__ == "__main__":
    sys.exit(main())
