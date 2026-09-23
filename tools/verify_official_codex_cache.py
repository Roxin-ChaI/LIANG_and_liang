#!/usr/bin/env python3
"""Verify a cached official DMG against a frozen, previously trusted build.

This read-only check permits reuse without redownloading. It does not infer
trust from a file name or a mutable CDN URL and never mounts or installs an App.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BASELINE = ROOT / "runtime-patch/builds/10789/trusted-baseline.json"
DEFAULT_CACHE = ROOT / ".cache/official-codex"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def verify_cache(baseline_path: Path, cache_dir: Path) -> dict[str, object]:
    baseline = json.loads(baseline_path.read_text())
    if baseline.get("classification") != "TRUSTED_BASELINE":
        raise ValueError("baseline has not been trusted")
    source = baseline.get("source", {})
    if source.get("kind") != "official-openai-dmg" or source.get("hdiutilVerify") != "PASS":
        raise ValueError("baseline source is not a verified official DMG")
    name = source.get("cachedFileName")
    if not isinstance(name, str) or not name.endswith(".dmg") or Path(name).name != name:
        raise ValueError("unsafe cached DMG file name")
    candidate = cache_dir / name
    if candidate.is_symlink() or not candidate.is_file():
        return {"status": "CACHE_MISSING", "version": baseline.get("version"), "build": baseline.get("build")}
    size = candidate.stat().st_size
    if size != source.get("dmgSizeBytes"):
        return {"status": "CACHE_SIZE_MISMATCH", "version": baseline.get("version"), "build": baseline.get("build")}
    actual = sha256(candidate)
    return {
        "status": "TRUSTED_CACHE_MATCH" if actual == source.get("dmgSha256") else "CACHE_HASH_MISMATCH",
        "version": baseline.get("version"),
        "build": baseline.get("build"),
        "sha256": actual,
        "path": str(candidate),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, default=DEFAULT_BASELINE)
    parser.add_argument("--cache-dir", type=Path, default=DEFAULT_CACHE)
    args = parser.parse_args()
    report = verify_cache(args.baseline, args.cache_dir)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["status"] == "TRUSTED_CACHE_MATCH" else 2


if __name__ == "__main__":
    raise SystemExit(main())
