"""T5 item 1 (static): resolved compose config contains no privileged service,
no added capability, no device mapping, no docker socket, no host networking.
Also asserts the hardening anchor posture and the network model.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from helpers import compose_config, compose_services  # noqa: E402

FORBIDDEN_MOUNT_TARGETS = ("/var/run/docker.sock", "/var/run/docker")


@pytest.fixture(scope="module")
def config() -> dict:
    return compose_config()


@pytest.fixture(scope="module")
def config_symbol_fetch() -> dict:
    return compose_config(profiles=["symbol-fetch"])


def test_no_privileged(config, config_symbol_fetch):
    for cfg in (config, config_symbol_fetch):
        for name, svc in compose_services(cfg).items():
            assert svc.get("privileged") is not True, f"{name}: privileged"


def test_no_cap_add(config, config_symbol_fetch):
    for cfg in (config, config_symbol_fetch):
        for name, svc in compose_services(cfg).items():
            assert not svc.get("cap_add"), f"{name}: cap_add present"


def test_no_devices(config, config_symbol_fetch):
    for cfg in (config, config_symbol_fetch):
        for name, svc in compose_services(cfg).items():
            assert not svc.get("devices"), f"{name}: devices present"


def test_no_docker_socket_mount(config, config_symbol_fetch):
    for cfg in (config, config_symbol_fetch):
        for name, svc in compose_services(cfg).items():
            for vol in svc.get("volumes", []) or []:
                target = vol.get("target", "") if isinstance(vol, dict) else str(vol)
                source = vol.get("source", "") if isinstance(vol, dict) else ""
                assert target not in FORBIDDEN_MOUNT_TARGETS, f"{name}: docker socket mount"
                assert "docker.sock" not in str(source), f"{name}: docker.sock source"


def test_no_host_network_mode(config, config_symbol_fetch):
    for cfg in (config, config_symbol_fetch):
        for name, svc in compose_services(cfg).items():
            assert svc.get("network_mode") != "host", f"{name}: host networking"


def test_hardening_anchor_applied(config):
    for name, svc in compose_services(config).items():
        user = svc.get("user", "")
        assert user.startswith("10001:"), f"{name}: user must start with uid 10001 (got {user!r})"
        assert svc.get("read_only") is True, f"{name}: rootfs must be read-only"
        assert "ALL" in (svc.get("cap_drop") or []), f"{name}: cap_drop ALL missing"
        assert "no-new-privileges:true" in (svc.get("security_opt") or []), f"{name}: no-new-privileges missing"
        assert any(str(o).startswith("seccomp:") for o in (svc.get("security_opt") or [])), f"{name}: seccomp profile missing"
        assert svc.get("pids_limit") == 512, f"{name}: pids_limit"
        assert svc.get("init") is True, f"{name}: init missing"


def test_case_services_get_host_group(config):
    # Case dirs are 770 host-owned; services touching /cases run with the
    # host analyst group (OREOA_HOST_GID) via user gid + group_add.
    for name in ("agent", "worker-fast", "worker-deep", "mcp-evidence", "mcp-case"):
        svc = compose_services(config)[name]
        uid, _, gid = svc["user"].partition(":")
        assert uid == "10001", f"{name}: uid must be 10001"
        assert gid == "1001", f"{name}: gid must be the host analyst group (got {gid!r})"
        assert svc.get("group_add"), f"{name}: group_add missing"


def test_internal_network_has_no_route(config):
    networks = config.get("networks", {})
    assert networks.get("internal", {}).get("internal") is True


def test_workers_and_mcp_only_on_internal(config):
    for name in ("redis", "worker-fast", "worker-deep",
                 "mcp-evidence", "mcp-knowledge", "mcp-case", "mcp-jobs"):
        assert set(compose_services(config)[name]["networks"]) == {"internal"}, name


def test_agent_on_egress_and_internal(config):
    assert set(compose_services(config)["agent"]["networks"]) == {"egress", "internal"}


def test_proxy_is_the_only_egress_service(config):
    assert set(compose_services(config)["proxy"]["networks"]) == {"egress", "external"}


def test_fetcher_profile_networks(config_symbol_fetch):
    # Amendment of the spec table by 3.6: the fetcher egresses only through
    # proxy-fetch (internal + external), the fetcher itself stays on internal.
    svcs = compose_services(config_symbol_fetch)
    assert set(svcs["fetcher"]["networks"]) == {"internal"}
    assert set(svcs["proxy-fetch"]["networks"]) == {"internal", "external"}
