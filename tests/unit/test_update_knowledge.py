"""T1: update-knowledge script (pins, snapshot, clamav one-shot, flags)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "src"))

import update_knowledge as uk  # noqa: E402


def test_load_pins_parses_versions_env():
    pins = uk.load_pins()
    assert pins.get("DFIQ_COMMIT")  # full sha
    assert pins.get("ATTACK_VERSION", "").startswith("v")
    assert pins.get("CLAMAV_IMAGE", "").startswith("clamav/clamav:")
    # empty pins are kept (flags like --full-symbols refuse them explicitly)
    assert "VOL_SYMBOLS_WINDOWS_SHA256" in pins


def test_attack_file_url_versioned_file():
    url, filename = uk.attack_file_url("v19.2")
    assert url.endswith("/v19.2/enterprise-attack/enterprise-attack-19.2.json")
    assert "raw.githubusercontent.com" in url
    assert filename == "enterprise-attack-19.2.json"


def test_source_table_matches_pins():
    pins = uk.load_pins()
    for source in uk.SOURCES:
        assert source.pin_var in pins, f"{source.name}: {source.pin_var} absent de versions.env"


def test_detect_licence(tmp_path: Path):
    (tmp_path / "LICENSE").write_text("GNU GENERAL PUBLIC LICENSE Version 3", encoding="utf-8")
    assert "GPL" in uk.detect_licence(tmp_path)
    (tmp_path / "LICENSE").write_text("Apache License Version 2.0", encoding="utf-8")
    assert "Apache" in uk.detect_licence(tmp_path)
    empty = tmp_path / "none"
    empty.mkdir()
    assert uk.detect_licence(empty) == "unknown"


def _fake_git(monkeypatch: pytest.MonkeyPatch, calls: list):
    def fake_run_git(args, cwd=None):
        calls.append(args)
        if args[:2] == ["rev-parse", "HEAD"]:
            return subprocess.CompletedProcess(args, 0, "old" + "0" * 37, "")
        if args[:1] == ["clone"]:
            target = Path(args[-1])
            target.mkdir(parents=True)
            (target / "LICENSE").write_text("MIT License", encoding="utf-8")
        if args[:2] == ["rev-parse", "FETCH_HEAD"]:
            return subprocess.CompletedProcess(args, 0, "f" * 40, "")
        return subprocess.CompletedProcess(args, 0, "", "")

    monkeypatch.setattr(uk, "run_git", fake_run_git)


def test_fetch_git_source_clone_and_cache(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    calls = []
    _fake_git(monkeypatch, calls)
    source = uk.Source("acme", "https://example.com/acme", "ACME_COMMIT", "*")
    dest = tmp_path / "acme"

    resolved, licence, fetched = uk.fetch_git_source(source, "a" * 40, dest, False)
    assert resolved == "f" * 40 and fetched is True and "MIT" in licence

    # second run at the pinned commit: cached, no clone
    (dest / ".git").mkdir()
    import subprocess as sp

    def cached_head(args, cwd=None):
        if args[:2] == ["rev-parse", "HEAD"]:
            return sp.CompletedProcess(args, 0, "a" * 40, "")
        return sp.CompletedProcess(args, 0, "", "")

    monkeypatch.setattr(uk, "run_git", cached_head)
    resolved, licence, fetched = uk.fetch_git_source(source, "a" * 40, dest, False)
    assert fetched is False and resolved == "a" * 40


def test_refresh_clamav_requires_docker(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    monkeypatch.setattr(uk, "UPSTREAM", tmp_path / "upstream")
    monkeypatch.setattr(uk.shutil, "which", lambda name: None)
    status = uk.refresh_clamav({"CLAMAV_IMAGE": "clamav/clamav:1.5.4-debian13-slim"}, {})
    assert status["status"] == "error" and "docker" in status["message"]


def test_refresh_clamav_one_shot_container(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    db_dir = tmp_path / "upstream" / "clamav_db"
    db_dir.mkdir(parents=True)
    (db_dir / "daily.cvd").write_text("ClamAV-VDB:test:1:2:3", encoding="utf-8")
    monkeypatch.setattr(uk, "UPSTREAM", tmp_path / "upstream")

    captured = {}

    def fake_run(cmd, **kwargs):
        captured["cmd"] = cmd
        captured["db_dir"] = Path(str(cmd[cmd.index("-v") + 1]).split(":")[0])
        return subprocess.CompletedProcess(cmd, 0, "", "")

    monkeypatch.setattr(uk.subprocess, "run", fake_run)
    monkeypatch.setattr(uk.shutil, "which", lambda name: "/usr/bin/docker")
    status = uk.refresh_clamav({"CLAMAV_IMAGE": "clamav/clamav:1.5.4-debian13-slim"}, {})
    assert status["status"] == "ok"
    assert status["databases"] == ["daily.cvd"]
    assert captured["cmd"][0].endswith("docker")
    assert "--entrypoint" in captured["cmd"] and "freshclam" in captured["cmd"]
    assert captured["db_dir"] == db_dir.resolve()


def test_refresh_clamav_failure_is_non_blocking(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    monkeypatch.setattr(uk, "UPSTREAM", tmp_path / "upstream")

    def fake_run(cmd, **kwargs):
        return subprocess.CompletedProcess(cmd, 1, "", "Can't reach database server")

    monkeypatch.setattr(uk.subprocess, "run", fake_run)
    monkeypatch.setattr(uk.shutil, "which", lambda name: "/usr/bin/docker")
    status = uk.refresh_clamav({"CLAMAV_IMAGE": "clamav/clamav:1.5.4-debian13-slim"}, {})
    assert status["status"] == "error" and "freshclam failed" in status["message"]


def test_full_symbols_requires_pinned_sha256(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(uk, "UPSTREAM", tmp_path)
    with pytest.raises(RuntimeError, match="VOL_SYMBOLS_WINDOWS_SHA256"):
        uk.fetch_full_symbols({})


def test_symbol_linux_prints_guidance(capsys):
    entry = uk.fetch_single_symbol({}, "linux", "ignored")
    assert entry["status"] == "guidance_printed"
    out = capsys.readouterr().out
    assert "dwarf2json" in out


def test_symbol_windows_requires_pdbconv(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """pdbconv absent on the host -> clear error, nothing written."""
    import requests

    monkeypatch.setattr(uk, "SYMBOLS_CUSTOM", tmp_path / "symbols")

    class FakeResponse:
        status_code = 200

        def iter_content(self, **kwargs):
            yield b"fake-pdb"

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    monkeypatch.setattr(requests, "get", lambda url, stream=True, timeout=None: FakeResponse())
    monkeypatch.setattr(
        uk.subprocess,
        "run",
        lambda *a, **kw: subprocess.CompletedProcess(a[0], 1, "", "no module"),
    )
    with pytest.raises(SystemExit, match="pdbconv"):
        uk.fetch_single_symbol({}, "windows", "ntkrnlmp.pdb/" + "A" * 32 + "1")
    assert not (tmp_path / "symbols").exists() or not list((tmp_path / "symbols").rglob("*.json"))


def test_snapshot_round_trip(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(uk, "SNAPSHOT_PATH", tmp_path / "snapshot.json")
    uk.write_snapshot({"version": 1, "sources": [{"name": "dfiq"}]})
    data = json.loads((tmp_path / "snapshot.json").read_text(encoding="utf-8"))
    assert data["sources"][0]["name"] == "dfiq"


def test_main_refuses_nsrl(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """--nsrl is refused until the NIST subset is pinned (nothing fetched)."""
    monkeypatch.setattr(uk, "UPSTREAM", tmp_path / "upstream")
    monkeypatch.setattr(uk, "SNAPSHOT_PATH", tmp_path / "snapshot.json")
    monkeypatch.setattr(uk, "refresh_clamav", lambda pins, summary: {"status": "skipped", "message": "test"})
    monkeypatch.setattr(
        uk,
        "fetch_git_source",
        lambda source, pin, dest, force: (pin, source.licence, True),
    )
    monkeypatch.setattr(
        uk,
        "fetch_file_source",
        lambda source, pin, dest, force: (pin, source.licence, True),
    )
    rc = uk.main(["--nsrl", "--no-clamav"])
    assert rc == 1
    snapshot = json.loads((tmp_path / "snapshot.json").read_text(encoding="utf-8"))
    assert any("NSRL" in e or "nsrl" in e for e in snapshot["errors"])
    assert len(snapshot["sources"]) == len(uk.SOURCES)
