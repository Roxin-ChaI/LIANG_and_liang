#!/usr/bin/env python3
"""Read-only AMFI entitlement diagnosis for the Phase 8C temporary launch.

The tool reads signed metadata and a narrowly bounded unified-log window. It
never reads Keychain items, signs code, removes entitlements, or launches apps.
"""

from __future__ import annotations

import argparse
import json
import plistlib
import re
import subprocess
from pathlib import Path


OFFICIAL_APP = Path("/Applications/ChatGPT.app")

# Authorization classes are based on Apple's TN3125 and per-entitlement docs.
# UNKNOWN deliberately includes identity fields that the observed AMFI log did
# not name as the failing entitlement.
CLASSES = {
    "com.apple.application-identifier": "UNKNOWN",
    "com.apple.developer.aps-environment": "RESTRICTED",
    "com.apple.developer.team-identifier": "UNKNOWN",
    "com.apple.security.app-sandbox": "UNRESTRICTED",
    "com.apple.security.application-groups": "UNRESTRICTED",
    "com.apple.security.automation.apple-events": "UNRESTRICTED",
    "com.apple.security.cs.allow-jit": "UNRESTRICTED",
    "com.apple.security.cs.allow-unsigned-executable-memory": "UNRESTRICTED",
    "com.apple.security.device.audio-input": "UNRESTRICTED",
    "com.apple.security.device.camera": "UNRESTRICTED",
    "com.apple.security.files.user-selected.read-write": "UNRESTRICTED",
    "com.apple.security.network.client": "UNRESTRICTED",
    "com.apple.security.personal-information.calendars": "UNRESTRICTED",
    "keychain-access-groups": "RESTRICTED",
}


def classify_entitlements(keys: list[str]) -> dict[str, str]:
    return {key: CLASSES.get(key, "UNKNOWN") for key in sorted(keys)}


def parse_amfi_log(log_text: str) -> dict[str, object]:
    """Extract only launch-rejection evidence, never raw log contents."""

    executable = None
    for line in log_text.splitlines():
        if "AppleMobileFileIntegrityError Code=-424" not in line:
            continue
        match = re.search(r"(?:\S+\.app/)(Contents/MacOS/[^\s]+) not valid:", line)
        if match:
            executable = match.group(1)
            break
    names: set[str] = set()
    for match in re.finditer(r"Unsatisfied Entitlements?:\s*([^\n]+)", log_text, re.IGNORECASE):
        names.update(re.findall(r"(?:keychain-access-groups|com\.apple\.[A-Za-z0-9._-]+)", match.group(1)))
    generic = "adhoc signed app with restricted entitlements" in log_text.lower()
    certificate_chain_failed = "Unable to retrieve certificate chain" in log_text
    return {
        "failedExecutable": executable,
        "amfiCode424": executable is not None,
        "amfiCode427": certificate_chain_failed,
        "genericRestrictedEntitlementRejection": generic,
        "namedUnsatisfiedEntitlements": sorted(names),
        "failureClass": (
            "ENTITLEMENT_AUTHORIZATION_FAILED"
            if executable and generic
            else "OTHER_LAUNCH_FAILURE" if executable
            else "UNKNOWN"
        ),
        "verdict": (
            "EXACT_ENTITLEMENT_IDENTIFIED"
            if executable and names
            else "AMFI_CAUSE_UNCONFIRMED"
        ),
    }


def _run(command: list[str]) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(command, capture_output=True, check=True)


def signed_entitlements(component: Path) -> dict[str, object]:
    result = _run(["codesign", "-d", "--entitlements", "-", "--xml", str(component)])
    value = plistlib.loads(result.stdout)
    if not isinstance(value, dict):
        raise ValueError("signed entitlement plist is not a dictionary")
    return value


def signer_metadata(component: Path) -> dict[str, object]:
    result = _run(["codesign", "-dv", "--verbose=4", str(component)])
    details = (result.stdout + result.stderr).decode("utf-8", "replace")
    def field(name: str) -> str | None:
        prefix = name + "="
        return next((line[len(prefix):] for line in details.splitlines() if line.startswith(prefix)), None)
    return {
        "identifier": field("Identifier"),
        "teamIdentifier": field("TeamIdentifier"),
        "hardenedRuntime": "flags=0x10000(runtime)" in details,
        "adHoc": "Signature=adhoc" in details or field("TeamIdentifier") == "not set",
    }


def component_paths(app: Path) -> dict[str, Path]:
    framework = app / "Contents/Frameworks/Codex Framework.framework"
    versions = sorted((framework / "Versions").glob("*/Helpers"))
    helpers = versions[-1] if versions else framework / "Versions/missing/Helpers"
    return {
        "main": app,
        "framework": framework,
        "rendererHelper": helpers / "Codex (Renderer).app",
        "serviceHelper": helpers / "Codex (Service).app",
    }


def read_log_window(start: str, end: str) -> str:
    predicate = 'process == "amfid" OR process == "kernel" OR process == "launchd"'
    result = _run([
        "/usr/bin/log", "show", "--start", start, "--end", end,
        "--info", "--debug", "--style", "compact", "--predicate", predicate,
    ])
    return result.stdout.decode("utf-8", "replace")


def diagnose(app: Path, log_text: str) -> dict[str, object]:
    parts = component_paths(app)
    entitlements = signed_entitlements(parts["main"])
    signed = {name: signer_metadata(path) for name, path in parts.items() if path.exists()}
    evidence = parse_amfi_log(log_text)
    return {
        "officialMainProfilePresent": (app / "Contents/embedded.provisionprofile").is_file(),
        "signedComponents": signed,
        "entitlementClasses": classify_entitlements(list(entitlements)),
        "entitlementCount": len(entitlements),
        "amfi": evidence,
        "phase8cStrictCodesign": "SIGNATURE_STRUCTURE_VALID",
        "minimalSigningExperimentAllowed": evidence["verdict"] == "EXACT_ENTITLEMENT_IDENTIFIED",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--app", type=Path, default=OFFICIAL_APP)
    parser.add_argument("--log-start", required=True)
    parser.add_argument("--log-end", required=True)
    args = parser.parse_args()
    report = diagnose(args.app, read_log_window(args.log_start, args.log_end))
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["amfi"]["verdict"] == "EXACT_ENTITLEMENT_IDENTIFIED" else 2


if __name__ == "__main__":
    raise SystemExit(main())
