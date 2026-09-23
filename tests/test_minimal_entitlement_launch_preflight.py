"""End-to-end fail-closed gate before any temporary signing experiment."""

from __future__ import annotations

import hashlib
import json
import os
import plistlib
import struct
import subprocess
import sys
from pathlib import Path


TOOL = Path(__file__).resolve().parents[1] / "tools/derive_test_entitlements.py"


def test_newer_app_cannot_enter_minimal_signing_workflow(tmp_path: Path) -> None:
    source = tmp_path / "ChatGPT.app"
    resources = source / "Contents/Resources"
    executable_dir = source / "Contents/MacOS"
    resources.mkdir(parents=True)
    executable_dir.mkdir()
    encoded = b'{"files":{}}'
    aligned = (4 + len(encoded) + 1 + 3) & ~3
    archive = (
        struct.pack("<II", 4, 4 + aligned)
        + struct.pack("<II", aligned, len(encoded))
        + encoded + b"\0" + b"\0" * (aligned - 4 - len(encoded) - 1)
        + b"fixture"
    )
    (resources / "app.asar").write_bytes(archive)
    (executable_dir / "ChatGPT").write_bytes(b"fixture executable")
    with (source / "Contents/Info.plist").open("wb") as handle:
        plistlib.dump({
            "CFBundleShortVersionString": "26.924.0",
            "CFBundleVersion": "10789",
            "CFBundleIdentifier": "com.openai.codex",
            "CFBundleExecutable": "ChatGPT",
            "ElectronAsarIntegrity": {"Resources/app.asar": {
                "algorithm": "SHA256", "hash": hashlib.sha256(encoded).hexdigest()
            }},
        }, handle)
    baseline = tmp_path / "trusted-baseline.json"
    baseline.write_text(json.dumps({
        "classification": "TRUSTED_BASELINE",
        "version": "26.915.31945",
        "build": "9922",
        "appAsar": {"sha256": "frozen-9922-archive"},
        "executable": {"sha256": "frozen-9922-executable"},
    }))
    before = {path.relative_to(tmp_path).as_posix(): path.read_bytes()
              for path in tmp_path.rglob("*") if path.is_file()}
    # A missing PATH proves the mismatched-source CLI never even attempts
    # codesign/spctl, let alone patching, signing or launching an App.
    result = subprocess.run(
        [sys.executable, str(TOOL), "--app", str(source), "--baseline", str(baseline)],
        cwd=tmp_path, env={**os.environ, "PATH": "/nonexistent"},
        capture_output=True, text=True, check=False,
    )
    after = {path.relative_to(tmp_path).as_posix(): path.read_bytes()
             for path in tmp_path.rglob("*") if path.is_file()}
    assert result.returncode == 2
    assert json.loads(result.stdout) == {
        "components": [], "sourceBuild": "10789", "status": "BLOCKED_SOURCE_UNSUPPORTED_BUILD"
    }
    assert before == after
