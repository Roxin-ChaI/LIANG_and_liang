#!/usr/bin/env python3
"""Read-only, per-component entitlement plan for a trusted Build 9922 App.

This tool does not copy, modify, sign, or launch an application. It refuses to
inspect a different build as though it were the frozen Build 9922 baseline.
"""

from __future__ import annotations

import argparse
import json
import os
import plistlib
import subprocess
import sys
from pathlib import Path
from typing import Callable

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.isolated_runtime_test import DEFAULT_BASELINE, IsolationError, fingerprint, verify_source


Run = Callable[[list[str]], subprocess.CompletedProcess[bytes]]

# These are Hardened Runtime exceptions used by Electron. They are retained
# only where the ORIGINAL signed component already requested them.
ELECTRON_RUNTIME_KEYS = frozenset({
    "com.apple.security.cs.allow-jit",
    "com.apple.security.cs.allow-unsigned-executable-memory",
    "com.apple.security.cs.disable-library-validation",
    "com.apple.security.cs.allow-dyld-environment-variables",
})

# These claims cannot be carried across from the OpenAI Developer ID identity
# to an ad-hoc local test signature. Never synthesize replacement values.
IDENTITY_BOUND_KEYS = frozenset({
    "com.apple.application-identifier",
    "com.apple.developer.team-identifier",
    "com.apple.developer.aps-environment",
    "com.apple.security.application-groups",
    "keychain-access-groups",
})

# All other *known* original claims are unnecessary for an offline Pet-only
# launch experiment, provided the original app is not sandboxed.
OFFLINE_OPTIONAL_KEYS = frozenset({
    "com.apple.security.app-sandbox",
    "com.apple.security.automation.apple-events",
    "com.apple.security.device.audio-input",
    "com.apple.security.device.camera",
    "com.apple.security.files.user-selected.read-write",
    "com.apple.security.network.client",
    "com.apple.security.personal-information.calendars",
})


def _run(command: list[str]) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(command, capture_output=True, check=False)


def discover_components(app: Path) -> list[Path]:
    """List signed code containers without following Framework symlinks."""
    components = [app]
    framework_root = app / "Contents/Frameworks"
    if not framework_root.is_dir():
        raise ValueError("Frameworks directory is missing")
    for root, directory_names, file_names in os.walk(framework_root, followlinks=False):
        parent = Path(root)
        directory_names[:] = [name for name in directory_names if not (parent / name).is_symlink()]
        for name in directory_names:
            path = parent / name
            if path.suffix in {".app", ".framework", ".xpc", ".appex"}:
                components.append(path)
        for name in file_names:
            path = parent / name
            if path.suffix in {".dylib", ".so"} and path.is_file() and not path.is_symlink():
                components.append(path)
    return sorted(set(components), key=lambda path: (len(path.parts), str(path)))


def inspect_component(app: Path, component: Path, run: Run = _run) -> dict[str, object]:
    relative = "." if component == app else component.relative_to(app).as_posix()
    details = run(["codesign", "-dv", "--verbose=4", str(component)])
    if details.returncode:
        raise ValueError(f"codesign display failed for {relative}")
    lines = (details.stdout + details.stderr).decode("utf-8", "replace").splitlines()
    fields = dict(line.split("=", 1) for line in lines if "=" in line)
    signed = run(["codesign", "-d", "--entitlements", "-", "--xml", str(component)])
    if signed.returncode:
        raise ValueError(f"entitlement extraction failed for {relative}")
    try:
        original = plistlib.loads(signed.stdout) if signed.stdout else {}
    except (ValueError, plistlib.InvalidFileException) as error:
        raise ValueError(f"invalid entitlement plist for {relative}") from error
    if not isinstance(original, dict):
        raise ValueError(f"entitlements are not a dictionary for {relative}")
    profile = component / "Contents/embedded.provisionprofile" if component.is_dir() else None
    return {
        "component": relative,
        "identifier": fields.get("Identifier"),
        "teamIdentifier": fields.get("TeamIdentifier"),
        "hardenedRuntime": any("runtime" in line and "flags=" in line for line in lines),
        "profilePresent": bool(profile and profile.is_file()),
        "originalEntitlements": original,
    }


def derive_component(record: dict[str, object]) -> dict[str, object]:
    original = record["originalEntitlements"]
    if not isinstance(original, dict):
        raise ValueError("original entitlements must be a dictionary")
    retained: dict[str, object] = {}
    removed: dict[str, str] = {}
    unknown: list[str] = []
    for key, value in sorted(original.items()):
        if key in ELECTRON_RUNTIME_KEYS:
            if value is True:
                retained[key] = value
            else:
                unknown.append(key)
        elif key in IDENTITY_BOUND_KEYS:
            removed[key] = "OpenAI identity/profile claim; never transferred to local test signer"
        elif key in OFFLINE_OPTIONAL_KEYS:
            removed[key] = "not required for offline Pet-only launch experiment"
            if key == "com.apple.security.app-sandbox" and value is True:
                unknown.append(key)
        else:
            unknown.append(key)
    return {
        **record,
        "testEntitlements": retained,
        "removed": removed,
        "unknownRisks": sorted(unknown),
        "planStatus": (
            "REVIEW_REQUIRED"
            if unknown or not record.get("hardenedRuntime")
            else "PROPOSED_NOT_LAUNCH_VALIDATED"
        ),
    }


def build_matrix(app: Path, baseline: Path = DEFAULT_BASELINE, run: Run = _run) -> dict[str, object]:
    # Crucial order: no component inventory or signing plan for unsupported
    # source bytes. The trusted preflight also checks identity and signature.
    observed = fingerprint(app)
    frozen = json.loads(baseline.read_text())
    if frozen.get("classification") != "TRUSTED_BASELINE":
        raise ValueError("baseline is not trusted")
    if (
        observed.version != frozen.get("version")
        or observed.build != frozen.get("build")
        or observed.app_asar_sha256 != frozen.get("appAsar", {}).get("sha256")
        or observed.executable_sha256 != frozen.get("executable", {}).get("sha256")
    ):
        return {
            "status": "BLOCKED_SOURCE_UNSUPPORTED_BUILD",
            "sourceBuild": observed.build,
            "components": [],
        }
    preflight = verify_source(app, baseline_path=baseline)
    if preflight.status != "PASS":
        return {
            "status": "BLOCKED_SOURCE_" + preflight.status,
            "sourceBuild": preflight.fingerprint.build,
            "components": [],
        }
    records = [derive_component(inspect_component(app, path, run)) for path in discover_components(app)]
    return {
        "status": (
            "PROPOSED_NOT_LAUNCH_VALIDATED"
            if records and all(row["planStatus"] == "PROPOSED_NOT_LAUNCH_VALIDATED" for row in records)
            else "BLOCKED_COMPONENT_REVIEW"
        ),
        "sourceBuild": preflight.fingerprint.build,
        "components": records,
        "warning": "A signature plan is not proof of AMFI launch authorization or credential isolation.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--app", type=Path, default=Path("/Applications/ChatGPT.app"))
    parser.add_argument("--baseline", type=Path, default=DEFAULT_BASELINE)
    args = parser.parse_args()
    try:
        report = build_matrix(args.app, args.baseline)
    except (IsolationError, OSError, ValueError) as error:
        report = {"status": "BLOCKED_SOURCE_INVALID", "reason": str(error), "components": []}
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["status"] == "PROPOSED_NOT_LAUNCH_VALIDATED" else 2


if __name__ == "__main__":
    raise SystemExit(main())
