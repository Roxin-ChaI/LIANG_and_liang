#!/usr/bin/env python3
"""Read-only Build 9922 isolation audit; never opens Keychain or launches App."""

from __future__ import annotations

import argparse
import json
import plistlib
import struct
import subprocess
from pathlib import Path

if __package__:
    from .isolated_runtime_test import DEFAULT_BASELINE, REAL_APP, fingerprint
else:
    from isolated_runtime_test import DEFAULT_BASELINE, REAL_APP, fingerprint

BOOTSTRAP = ".vite/build/bootstrap-DF0QwAxC.js"
MAIN = ".vite/build/main-DUHZj4_w.js"
PRELOAD = ".vite/build/preload.js"
ANCHORS = {
    "user_data": "o.app.setPath(`userData`,pk(",
    "lock": "if(bj&&!o.app.requestSingleInstanceLock())",
    "override": "CODEX_ELECTRON_USER_DATA_PATH",
    "second_instance": "o.app.on(`second-instance`",
}


def packed_asar_file(archive: Path, relative: str) -> bytes:
    """Read one packed entry without unpacking or writing proprietary JS."""
    with archive.open("rb") as handle:
        prefix = handle.read(8)
        if len(prefix) != 8:
            raise ValueError("truncated ASAR")
        pickle_size, header_size = struct.unpack("<II", prefix)
        if pickle_size != 4 or not 12 <= header_size <= 64 * 1024 * 1024:
            raise ValueError("invalid ASAR header")
        header = handle.read(header_size)
        if len(header) != header_size:
            raise ValueError("truncated ASAR header")
        payload_size, json_size = struct.unpack("<II", header[:8])
        if payload_size != header_size - 4 or json_size > header_size - 8:
            raise ValueError("invalid ASAR header payload")
        tree = json.loads(header[8 : 8 + json_size])["files"]
        for segment in relative.split("/"):
            entry = tree[segment]
            tree = entry.get("files", {})
        if entry.get("unpacked") or "link" in entry:
            raise ValueError("entry is not packed")
        handle.seek(8 + header_size + int(entry["offset"]))
        result = handle.read(int(entry["size"]))
        if len(result) != int(entry["size"]):
            raise ValueError("truncated entry")
        return result


def analyze_bootstrap(source: str) -> dict[str, object]:
    offsets = {name: source.find(anchor) for name, anchor in ANCHORS.items()}
    ordered = all(offset >= 0 for offset in offsets.values()) and offsets["user_data"] < offsets["lock"]
    explicit_override = "hasExplicitUserDataPath:!!process.env.CODEX_ELECTRON_USER_DATA_PATH?.trim()" in source
    return {
        "status": "CONFIRMED" if ordered and explicit_override else "NOT_PROVEN",
        "anchorsPresent": {key: offset >= 0 for key, offset in offsets.items()},
        "userDataBeforeLock": ordered,
        "explicitOverrideControlsLockBranch": explicit_override,
        "lockScopedAwayFromProduction": "NOT_PROVEN",
    }


def classify_entitlements(values: dict[str, object], team_identifier: str | None) -> dict[str, object]:
    groups = values.get("keychain-access-groups", [])
    production_groups = isinstance(groups, list) and any(
        isinstance(group, str) and group.startswith("2DC432GLL2.") for group in groups
    )
    return {
        "keyCount": len(values),
        "teamIdentifier": team_identifier,
        "productionKeychainGroupsDeclared": production_groups,
        "effectiveKeychainAccessAfterAdHocSigning": "NOT_PROVEN",
        "sameAppleTeamAfterAdHocSigning": False,
    }


def run_capture(command: list[str]) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(command, capture_output=True, check=False)


def inspect(app: Path = REAL_APP, baseline: Path = DEFAULT_BASELINE) -> dict[str, object]:
    expected = json.loads(baseline.read_text())
    observed = fingerprint(app)
    if observed.build != "9922" or observed.app_asar_sha256 != expected["appAsar"]["sha256"]:
        raise ValueError("not the trusted Build 9922 source")
    archive = app / "Contents/Resources/app.asar"
    bootstrap = packed_asar_file(archive, BOOTSTRAP).decode("utf-8", "replace")
    main = packed_asar_file(archive, MAIN).decode("utf-8", "replace")
    preload = packed_asar_file(archive, PRELOAD).decode("utf-8", "replace")
    detail = run_capture(["codesign", "-dv", "--verbose=4", str(app)])
    detail_text = (detail.stdout + detail.stderr).decode("utf-8", "replace")
    team = next((line.partition("=")[2] for line in detail_text.splitlines() if line.startswith("TeamIdentifier=")), None)
    entitlement_result = run_capture(["codesign", "-d", "--entitlements", "-", "--xml", str(app)])
    if detail.returncode or entitlement_result.returncode:
        raise ValueError("signature metadata unavailable; use verified trust context")
    entitlements = plistlib.loads(entitlement_result.stdout)
    helper_root = app / "Contents/Frameworks/Codex Framework.framework/Helpers"
    helpers = sorted(path.name for path in helper_root.glob("Codex*.app") if path.is_dir())
    native_root = app / "Contents/Resources/native"
    native_modules = sorted(path.name for path in native_root.glob("*.node"))
    credential_terms = ("keychain", "safeStorage", "keytar")
    return {
        "build": observed.build,
        "asarSha256": observed.app_asar_sha256,
        "bundleId": observed.bundle_identifier,
        "singleInstance": analyze_bootstrap(bootstrap),
        "processLayout": {
            "status": "CONFIRMED",
            "mainChunk": MAIN,
            "preloadChunk": PRELOAD,
            "helperApps": helpers,
            "mainHasBrowserWindow": "BrowserWindow" in main,
            "preloadHasContextBridge": "contextBridge" in preload,
            "helperArgumentPropagation": "NOT_PROVEN",
        },
        "credentialPaths": {
            "status": "NOT_PROVEN",
            "keywordCountsInInspectedChunks": {
                term: sum(chunk.lower().count(term.lower()) for chunk in (bootstrap, main, preload))
                for term in credential_terms
            },
            "nativeModuleNames": native_modules,
            "nativeAndOSKeychainCallsFullyExcluded": False,
        },
        "signature": classify_entitlements(entitlements, team),
        "independentGuiLoginSession": "NOT_PROVEN",
        "realAppLaunchSafe": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--app", type=Path, default=REAL_APP)
    parser.add_argument("--baseline", type=Path, default=DEFAULT_BASELINE)
    args = parser.parse_args()
    try:
        result = inspect(args.app, args.baseline)
    except (OSError, ValueError, KeyError, plistlib.InvalidFileException) as error:
        print(json.dumps({"status": "UNSAFE", "reason": type(error).__name__}))
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
