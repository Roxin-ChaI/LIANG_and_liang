#!/usr/bin/env python3
"""Ad-hoc sign only a fingerprint-gated temporary Codex App, inside-out.

The official source is read-only. No production Keychain item or original
provisioning profile is read, copied into a signing request, or reused.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import plistlib
import subprocess
import struct
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.derive_test_entitlements import build_matrix, discover_components, inspect_component
from tools.isolated_runtime_test import fingerprint


ROOT = Path(__file__).resolve().parents[1]
BASELINE = ROOT / "runtime-patch/builds/10789/trusted-baseline.json"
SOURCE_APP = ROOT / ".cache/official-codex/mount/ChatGPT.app"
TEMP_ROOT = ROOT / ".cache/phase8f-work"
TEMP_APP = TEMP_ROOT / "ChatGPT.app"


class SigningError(RuntimeError):
    pass


def run(command: list[str]) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(command, capture_output=True, check=False)


def macho_text_hash(executable: Path) -> str:
    """Hash arm64 Mach-O __TEXT,__text, excluding mutable signature metadata."""
    data = executable.read_bytes()
    if len(data) < 32 or data[:4] != b"\xcf\xfa\xed\xfe":
        raise SigningError("unsupported Mach-O executable format")
    command_count = struct.unpack_from("<I", data, 16)[0]
    offset = 32
    for _ in range(command_count):
        if offset + 8 > len(data):
            raise SigningError("truncated Mach-O load command")
        command, command_size = struct.unpack_from("<II", data, offset)
        end = offset + command_size
        if command_size < 8 or end > len(data):
            raise SigningError("invalid Mach-O load command")
        if command == 0x19:  # LC_SEGMENT_64
            if command_size < 72:
                raise SigningError("invalid Mach-O segment")
            section_count = struct.unpack_from("<I", data, offset + 64)[0]
            for index in range(section_count):
                section = offset + 72 + index * 80
                if section + 80 > end:
                    raise SigningError("invalid Mach-O section")
                if data[section:section + 16].rstrip(b"\0") != b"__text" or data[section + 16:section + 32].rstrip(b"\0") != b"__TEXT":
                    continue
                size = struct.unpack_from("<Q", data, section + 40)[0]
                file_offset = struct.unpack_from("<I", data, section + 48)[0]
                if not size or file_offset + size > len(data):
                    raise SigningError("invalid Mach-O __text bounds")
                return hashlib.sha256(data[file_offset:file_offset + size]).hexdigest()
        offset = end
    raise SigningError("Mach-O __TEXT,__text section is missing")


def assert_temporary_app(app: Path, temp_root: Path, source: Path) -> None:
    if app.is_symlink() or not app.is_dir() or app.name != "ChatGPT.app":
        raise SigningError("temporary App is missing or unsafe")
    actual = app.resolve()
    if actual.parent != temp_root.resolve() or actual == Path("/Applications/ChatGPT.app").resolve() or actual == source.resolve():
        raise SigningError("signing target is not the isolated temporary App")


def preflight(source: Path, app: Path, baseline_path: Path, temp_root: Path, *, allow_resigned_executable: bool = False) -> dict[str, object]:
    assert_temporary_app(app, temp_root, source)
    baseline = json.loads(baseline_path.read_text())
    matrix = build_matrix(source, baseline_path)
    if matrix["status"] != "PROPOSED_NOT_LAUNCH_VALIDATED":
        raise SigningError("official source component entitlement matrix is not approved")
    identity = fingerprint(app)
    if (
        identity.version != baseline["version"]
        or identity.build != baseline["build"]
        or identity.app_asar_sha256 != baseline["recipeValidation"]["deterministicPatchedAsarSha256"]
        or (not allow_resigned_executable and identity.executable_sha256 != baseline["executable"]["sha256"])
        or identity.integrity_expected != identity.asar_header_sha256
        or identity.asar_header_sha256 != baseline["recipeValidation"]["patchedElectronIntegrityHeaderSha256"]
    ):
        raise SigningError("temporary patched App fingerprint or Electron integrity differs")
    if allow_resigned_executable:
        executable = Path(str(baseline["executable"]["path"]))
        if macho_text_hash(source / executable) != macho_text_hash(app / executable):
            raise SigningError("temporary App executable code section differs from official source")
    planned = {str(row["component"]) for row in matrix["components"]}
    observed = {"." if path == app else path.relative_to(app).as_posix() for path in discover_components(app)}
    if planned != observed:
        raise SigningError("temporary App signed-component set differs from the official source")
    if any(row["unknownRisks"] or not row["hardenedRuntime"] for row in matrix["components"]):
        raise SigningError("unknown entitlement or missing Hardened Runtime")
    return matrix


def sign_temporary_app(
    source: Path = SOURCE_APP,
    app: Path = TEMP_APP,
    baseline_path: Path = BASELINE,
    temp_root: Path = TEMP_ROOT,
) -> dict[str, object]:
    matrix = preflight(source, app, baseline_path, temp_root)
    work = temp_root / "minimal-entitlements"
    work.mkdir(exist_ok=False)
    rows = sorted(matrix["components"], key=lambda row: (-len(Path(str(row["component"])).parts), str(row["component"])))
    removed_profiles = []
    signed = []
    for index, row in enumerate(rows):
        relative = str(row["component"])
        component = app if relative == "." else app / relative
        profile = component / "Contents/embedded.provisionprofile" if component.is_dir() else None
        if row["profilePresent"]:
            if profile is None or profile.is_symlink() or not profile.is_file():
                raise SigningError(f"source profile mismatch: {relative}")
            profile.unlink()  # temporary App only; never decode or copy contents
            removed_profiles.append(relative)
        elif profile is not None and profile.exists():
            raise SigningError(f"unexpected profile in temporary App: {relative}")
        command = ["codesign", "--force", "--sign", "-", "--options", "runtime"]
        proposed = row["testEntitlements"]
        if proposed:
            entitlement_file = work / f"component-{index:03d}.plist"
            entitlement_file.write_bytes(plistlib.dumps(proposed))
            command += ["--entitlements", str(entitlement_file)]
        command.append(str(component))
        result = run(command)
        if result.returncode:
            raise SigningError(f"codesign failed for {relative}: {result.stderr.decode('utf-8', 'replace')[:300]}")
        signed.append(relative)
    result = verify_signed_temp_app(source, app, baseline_path, temp_root)
    result["profileRemovedFromTemporaryComponents"] = removed_profiles
    return result


def verify_signed_temp_app(
    source: Path = SOURCE_APP,
    app: Path = TEMP_APP,
    baseline_path: Path = BASELINE,
    temp_root: Path = TEMP_ROOT,
) -> dict[str, object]:
    matrix = preflight(source, app, baseline_path, temp_root, allow_resigned_executable=True)
    verify = run(["codesign", "--verify", "--deep", "--strict", "--verbose=2", str(app)])
    if verify.returncode:
        raise SigningError("deep/strict signature verification failed")
    mismatched = []
    for row in matrix["components"]:
        relative = str(row["component"])
        component = app if relative == "." else app / relative
        actual = inspect_component(app, component)
        if actual["profilePresent"]:
            mismatched.append(relative + ":profile")
        if actual["originalEntitlements"] != row["testEntitlements"] or not actual["hardenedRuntime"]:
            mismatched.append(relative)
        if actual["teamIdentifier"] not in (None, "not set"):
            mismatched.append(relative + ":team")
    if mismatched:
        raise SigningError("signed entitlement/Hardened Runtime/Team mismatch: " + ", ".join(mismatched[:5]))
    observed = fingerprint(app)
    baseline = json.loads(baseline_path.read_text())
    if (
        observed.app_asar_sha256 != baseline["recipeValidation"]["deterministicPatchedAsarSha256"]
        or observed.integrity_expected != observed.asar_header_sha256
    ):
        raise SigningError("signing changed executable, ASAR, or Electron integrity")
    return {
        "status": "SIGNATURE_STRUCTURE_VALID_NOT_LAUNCH_PROVEN",
        "componentCount": len(matrix["components"]),
        "hardenedRuntime": "PASS",
        "actualEntitlementsMatchPlan": True,
        "codesignDeepStrict": "PASS",
        "executableCodeSectionUnchanged": True,
        "asarSha256": observed.app_asar_sha256,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-app", type=Path, default=SOURCE_APP)
    parser.add_argument("--temp-app", type=Path, default=TEMP_APP)
    parser.add_argument("--baseline", type=Path, default=BASELINE)
    parser.add_argument("--temp-root", type=Path, default=TEMP_ROOT)
    parser.add_argument("--verify-only", action="store_true", help="recheck a previously signed temporary App without signing it again")
    args = parser.parse_args()
    try:
        action = verify_signed_temp_app if args.verify_only else sign_temporary_app
        report = action(args.source_app, args.temp_app, args.baseline, args.temp_root)
    except (SigningError, OSError, ValueError) as error:
        print(json.dumps({"status": "BLOCKED", "reason": str(error)}))
        return 2
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
