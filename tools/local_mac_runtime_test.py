#!/usr/bin/env python3
"""Opt-in, same-session Build 9922 runtime test preparation.

This is intentionally separate from the strict independent-account isolation
gate.  It cannot establish Keychain separation and never reads credentials.
"""

from __future__ import annotations

import argparse
import json
import os
import plistlib
import subprocess
import tempfile
from pathlib import Path

try:
    from tools.isolated_runtime_test import asar_raw_json_header_hash, sha256_file
except ModuleNotFoundError:
    from isolated_runtime_test import asar_raw_json_header_hash, sha256_file


ROOT = Path(__file__).resolve().parents[1]
BASELINE = ROOT / "runtime-patch/builds/9922/trusted-baseline.json"
OFFICIAL_APP = Path("/Applications/ChatGPT.app")


class LocalRuntimeError(RuntimeError):
    pass


def assert_temp_app(app: Path, phase_root: Path) -> None:
    resolved = app.resolve()
    base = phase_root.resolve()
    if resolved == OFFICIAL_APP.resolve() or base not in resolved.parents:
        raise LocalRuntimeError("App must be inside the Phase 8C temporary root")
    if app.is_symlink() or not app.is_dir() or app.name != "ChatGPT.app":
        raise LocalRuntimeError("App must be a real ChatGPT.app directory")


def update_integrity(app: Path, expected_asar_sha256: str) -> str:
    archive = app / "Contents/Resources/app.asar"
    if sha256_file(archive) != expected_asar_sha256:
        raise LocalRuntimeError("patched ASAR does not match the trusted recipe")
    plist = app / "Contents/Info.plist"
    original = plist.read_bytes()
    info = plistlib.loads(original)
    record = info.get("ElectronAsarIntegrity", {}).get("Resources/app.asar")
    if not isinstance(record, dict) or record.get("algorithm") != "SHA256":
        raise LocalRuntimeError("Electron integrity metadata is missing")
    header_hash = asar_raw_json_header_hash(archive)
    record["hash"] = header_hash
    encoded = plistlib.dumps(
        info, fmt=plistlib.FMT_BINARY if original.startswith(b"bplist") else plistlib.FMT_XML
    )
    with tempfile.NamedTemporaryFile(dir=plist.parent, prefix=".liang-info-", delete=False) as handle:
        staged = Path(handle.name)
        handle.write(encoded)
        handle.flush()
        os.fsync(handle.fileno())
    try:
        staged.chmod(plist.stat().st_mode)
        os.replace(staged, plist)
    finally:
        staged.unlink(missing_ok=True)
    return header_hash


def sign_temporary_app(app: Path, phase_root: Path) -> dict[str, object]:
    source = subprocess.run(
        ["codesign", "-d", "--entitlements", "-", "--xml", str(OFFICIAL_APP)],
        capture_output=True, check=True,
    )
    entitlements = plistlib.loads(source.stdout)
    if not isinstance(entitlements, dict) or len(entitlements) != 14:
        raise LocalRuntimeError("official entitlement key set is unexpected")
    with tempfile.NamedTemporaryFile(dir=phase_root, suffix=".plist", delete=False) as handle:
        entitlement_path = Path(handle.name)
        handle.write(plistlib.dumps(entitlements))
    try:
        signed = subprocess.run(
            ["codesign", "--force", "--deep", "--sign", "-", "--entitlements", str(entitlement_path), str(app)],
            capture_output=True,
        )
        if signed.returncode:
            raise LocalRuntimeError("ad-hoc signing failed")
        verify = subprocess.run(
            ["codesign", "--verify", "--deep", "--strict", "--verbose=2", str(app)],
            capture_output=True,
        )
        if verify.returncode:
            raise LocalRuntimeError("strict ad-hoc signature verification failed")
        observed = subprocess.run(
            ["codesign", "-d", "--entitlements", "-", "--xml", str(app)],
            capture_output=True, check=True,
        )
        actual = plistlib.loads(observed.stdout)
        if set(actual) != set(entitlements):
            raise LocalRuntimeError("entitlement keys changed during signing")
        return {
            "adHocSigning": "PASS",
            "strictCodesign": "PASS",
            "entitlementKeyCount": len(actual),
            "entitlementKeysPreserved": True,
            "keychainIsolationProven": False,
        }
    finally:
        entitlement_path.unlink(missing_ok=True)


def prepare(app: Path, phase_root: Path) -> dict[str, object]:
    assert_temp_app(app, phase_root)
    baseline = json.loads(BASELINE.read_text())
    recipe = baseline["recipeValidation"]
    if recipe["locatorCount"] != 12:
        raise LocalRuntimeError("trusted recipe locator count changed")
    expected = recipe["deterministicPatchedAsarSha256"]
    actual = sha256_file(app / "Contents/Resources/app.asar")
    if actual != expected:
        raise LocalRuntimeError("temporary App is not the trusted patched Build 9922")
    header = update_integrity(app, expected)
    signing = sign_temporary_app(app, phase_root)
    info = plistlib.loads((app / "Contents/Info.plist").read_bytes())
    if info["ElectronAsarIntegrity"]["Resources/app.asar"]["hash"] != header:
        raise LocalRuntimeError("Electron integrity metadata mismatch")
    return {
        "status": "TEMP_APP_SIGNED_LAUNCH_UNVERIFIED",
        "appAsarSha256": actual,
        "asarHeaderSha256": header,
        "locatorCount": recipe["locatorCount"],
        "launchabilityProven": False,
        "adHocRestrictedEntitlementRisk": (
            "Strict codesign verification does not prove that macOS AMFI will "
            "permit an ad-hoc signature with the preserved entitlement set."
        ),
        **signing,
    }


def verify_postflight(
    official_asar: Path, expected_sha256: str, temporary_roots: tuple[Path, ...]
) -> dict[str, object]:
    """Read-only recovery check; never inspects production credentials."""

    actual = sha256_file(official_asar)
    removed = all(not root.exists() for root in temporary_roots)
    return {
        "officialAppAsarUnchanged": actual == expected_sha256,
        "officialAppAsarSha256": actual,
        "temporaryRootsRemoved": removed,
        "status": "PASS" if actual == expected_sha256 and removed else "FAIL",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--app", type=Path, required=True)
    parser.add_argument("--phase-root", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = prepare(args.app, args.phase_root)
    except (LocalRuntimeError, OSError, subprocess.CalledProcessError) as error:
        print(json.dumps({"status": "BLOCKED", "reason": str(error)}))
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
