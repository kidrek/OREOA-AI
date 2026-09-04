"""T5 item 5: every service runs as uid 10001 (id -u != 0 everywhere).

Runtime test - requires built images (make build first). Skips with a clear
message when an image is absent so that `make test-infra` stays usable on a
fresh checkout without images.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from helpers import compose_config, compose_services, image_exists, run_in_service  # noqa: E402

SERVICES = [
    "agent",
    "proxy",
    "redis",
    "worker-fast",
    "worker-deep",
    "mcp-evidence",
    "mcp-knowledge",
    "mcp-case",
    "mcp-jobs",
]


def _image_of(service: str) -> str | None:
    svcs = compose_services(compose_config())
    return svcs[service].get("image")


@pytest.mark.parametrize("service", SERVICES)
def test_service_runs_as_uid_10001(service):
    image = _image_of(service)
    assert image, f"{service}: no image in compose"
    if not image_exists(image):
        pytest.skip(f"image {image} not built - run make build")
    out = run_in_service(service, "id -u")
    assert out.returncode == 0, f"{service}: {out.stderr}"
    assert out.stdout.strip() == "10001", f"{service}: uid is {out.stdout.strip()!r}, expected 10001"
