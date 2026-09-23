from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from tools.verify_official_codex_cache import verify_cache


def fixture(tmp_path: Path) -> tuple[Path, Path, Path]:
    cache = tmp_path / "cache"
    cache.mkdir()
    dmg = cache / "ChatGPT-10789.dmg"
    dmg.write_bytes(b"official test fixture")
    baseline = tmp_path / "baseline.json"
    baseline.write_text(json.dumps({
        "classification": "TRUSTED_BASELINE", "version": "test", "build": "10789",
        "source": {"kind": "official-openai-dmg", "hdiutilVerify": "PASS",
                   "cachedFileName": dmg.name, "dmgSizeBytes": dmg.stat().st_size,
                   "dmgSha256": hashlib.sha256(dmg.read_bytes()).hexdigest()},
    }))
    return baseline, cache, dmg


def test_exact_cached_bytes_are_reused(tmp_path: Path) -> None:
    baseline, cache, _dmg = fixture(tmp_path)
    assert verify_cache(baseline, cache)["status"] == "TRUSTED_CACHE_MATCH"


def test_missing_and_changed_cache_are_rejected(tmp_path: Path) -> None:
    baseline, cache, dmg = fixture(tmp_path)
    dmg.unlink()
    assert verify_cache(baseline, cache)["status"] == "CACHE_MISSING"
    dmg.write_bytes(b"wrong size")
    assert verify_cache(baseline, cache)["status"] == "CACHE_SIZE_MISMATCH"
    dmg.write_bytes(b"X" * len(b"official test fixture"))
    assert verify_cache(baseline, cache)["status"] == "CACHE_HASH_MISMATCH"


def test_unsafe_source_claims_are_rejected(tmp_path: Path) -> None:
    baseline, cache, _dmg = fixture(tmp_path)
    value = json.loads(baseline.read_text())
    value["source"]["cachedFileName"] = "../escape.dmg"
    baseline.write_text(json.dumps(value))
    with pytest.raises(ValueError, match="unsafe"):
        verify_cache(baseline, cache)
    value["source"]["cachedFileName"] = "ChatGPT-10789.dmg"
    value["source"]["hdiutilVerify"] = "UNKNOWN"
    baseline.write_text(json.dumps(value))
    with pytest.raises(ValueError, match="verified"):
        verify_cache(baseline, cache)
