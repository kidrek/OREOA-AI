"""T1: fetcher service (profile symbol-fetch) - refusals before any network
call, URL construction, ISF + provenance write with stubbed download."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from oreoa import fetcher  # noqa: E402
from oreoa.jobs_model import FetchSymbolPayload, JobEnvelope  # noqa: E402

VALID_GUID = "A2C42DD660EC415CBE9D79C2559C015C1"
CASE_ID = "2026-09-INC-042"


def envelope(pdb: str = "ntkrnlmp.pdb", guid: str = VALID_GUID, confirmed: bool = True) -> dict:
    return {
        "job_type": "fetch_symbol",
        "queue": "fetch",
        "case_id": CASE_ID,
        "payload": {"pdb_name": pdb, "guid": guid, "confirmed_by_analyst": confirmed},
    }


def test_payload_requires_confirmation():
    with pytest.raises(ValueError, match="confirmed_by_analyst"):
        FetchSymbolPayload(pdb_name="ntkrnlmp.pdb", guid=VALID_GUID, confirmed_by_analyst=False)


def test_payload_rejects_unknown_pdb_and_malformed_guid():
    with pytest.raises(ValueError, match="outside known kernel PDBs"):
        FetchSymbolPayload(pdb_name="explorer.pdb", guid=VALID_GUID, confirmed_by_analyst=True)
    with pytest.raises(ValueError):
        FetchSymbolPayload(pdb_name="ntkrnlmp.pdb", guid="not-a-guid", confirmed_by_analyst=True)


def test_envelope_queue_coherence():
    with pytest.raises(ValueError, match="runs on queue"):
        JobEnvelope.model_validate({**envelope(), "queue": "fast"})


def test_build_pdb_url_construction():
    url = fetcher.build_pdb_url("ntkrnlmp.pdb", VALID_GUID)
    assert url == f"{fetcher.MSDL_BASE}/ntkrnlmp.pdb/{VALID_GUID}/ntkrnlmp.pdb"
    with pytest.raises(ValueError):
        fetcher.build_pdb_url("evil.pdb", VALID_GUID)
    with pytest.raises(ValueError):
        fetcher.build_pdb_url("ntkrnlmp.pdb", "../etc/passwd")


def test_split_identifier():
    pdb, guid, age = fetcher.split_identifier(f"ntkrnlmp.pdb/{VALID_GUID}")
    assert pdb == "ntkrnlmp.pdb"
    assert guid == VALID_GUID[:32]
    assert age == 1
    with pytest.raises(ValueError):
        fetcher.split_identifier("unknown.pdb/" + VALID_GUID)
    with pytest.raises(ValueError):
        fetcher.split_identifier("ntkrnlmp.pdb/short")


def test_refusal_before_network(monkeypatch: pytest.MonkeyPatch):
    """Unconfirmed or malformed payloads are refused before any download:
    the requests layer is never reached (it would raise if imported with a
    session stub - here the validation failure is the proof)."""
    called = {"download": False}

    def fail_download(url, destination):
        called["download"] = True
        raise AssertionError("download must not be reached")

    monkeypatch.setattr(fetcher, "download_pdb", fail_download)
    symbols = Path("/tmp/oreoa-test-symbols-refusal")
    monkeypatch.setenv("OREOA_SYMBOLS_DIR", str(symbols))
    with pytest.raises(ValueError):
        fetcher.run_fetch_symbol(envelope(confirmed=False))
    with pytest.raises(ValueError):
        fetcher.run_fetch_symbol(envelope(guid="ZZZZ"))
    assert called["download"] is False
    assert not symbols.exists()


def test_full_flow_writes_isf_and_provenance(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    symbols = tmp_path / "volatility_symbols"
    symbols.mkdir()
    monkeypatch.setenv("OREOA_SYMBOLS_DIR", str(symbols))
    isf_content = {
        "metadata": {"windows": {"pdb": {"GUID": VALID_GUID[:32], "age": 1}}},
        "user_symbols": {},
    }
    pdb_bytes = b"fake-pdb-stream"

    def fake_download(url, destination):
        assert url == f"{fetcher.MSDL_BASE}/ntkrnlmp.pdb/{VALID_GUID}/ntkrnlmp.pdb"
        destination.write_bytes(pdb_bytes)

    def fake_convert(pdb_path: Path, isf_path: Path):
        isf_path.write_text(json.dumps(isf_content), encoding="utf-8")

    monkeypatch.setattr(fetcher, "download_pdb", fake_download)
    monkeypatch.setattr(fetcher, "convert_to_isf", fake_convert)

    result = fetcher.run_fetch_symbol(envelope())
    assert result["status"] == "ok"
    isf = symbols / "windows" / "ntkrnlmp.pdb" / f"{VALID_GUID[:32]}-1.json"
    assert isf.is_file()
    assert result["sha256_isf"] == fetcher.sha256_of(isf)
    provenance = json.loads((Path(result["provenance"])).read_text(encoding="utf-8"))
    assert provenance["identifier"] == f"ntkrnlmp.pdb/{VALID_GUID}"
    assert provenance["source_url"].startswith(fetcher.MSDL_BASE)
    assert provenance["confirmed_by"] == "analyst"
    assert provenance["sha256_pdb"] == fetcher.sha256_of.__globals__["hashlib"].sha256(pdb_bytes).hexdigest()


def test_isf_metadata_mismatch_refused(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    symbols = tmp_path / "volatility_symbols"
    symbols.mkdir()
    monkeypatch.setenv("OREOA_SYMBOLS_DIR", str(symbols))
    bad_isf = {"metadata": {"windows": {"pdb": {"GUID": "B" * 32, "age": 9}}}}

    monkeypatch.setattr(fetcher, "download_pdb", lambda url, dest: dest.write_bytes(b"x"))
    monkeypatch.setattr(
        fetcher, "convert_to_isf", lambda pdb, isf: isf.write_text(json.dumps(bad_isf), encoding="utf-8")
    )
    with pytest.raises(RuntimeError, match="metadata mismatch"):
        fetcher.run_fetch_symbol(envelope())
    assert not list((symbols / "windows" / "ntkrnlmp.pdb").glob("*.json"))


def test_missing_symbols_dir_refused(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    monkeypatch.setenv("OREOA_SYMBOLS_DIR", str(tmp_path / "absent"))
    with pytest.raises(RuntimeError, match="not mounted"):
        fetcher.run_fetch_symbol(envelope())
