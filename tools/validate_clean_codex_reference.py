#!/usr/bin/env python3
"""Read-only validation for a clean official Codex Desktop App reference."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import plistlib
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, Sequence


INSTALLED_UNTRUSTED_APP = Path("/Applications/ChatGPT.app")
EXPECTED_BUNDLE_ID = "com.openai.codex"
# Confirmed from the Build 9922 signature container during Phase 7A. It is a
# secondary identity check; strict codesign and Gatekeeper validation remain
# mandatory and prevent this value from blessing an ad-hoc lookalike.
PHASE7A_CONFIRMED_TEAM_ID = "2DC432GLL2"


class ReferenceValidationError(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class CommandResult:
    argv: tuple[str, ...]
    returncode: int
    stdout: bytes
    stderr: bytes
    available: bool = True

    def summary(self) -> dict[str, object]:
        stdout = self.stdout.decode("utf-8", "replace").strip()
        stderr = self.stderr.decode("utf-8", "replace").strip()
        return {
            "available": self.available,
            "returncode": self.returncode,
            "stdoutBytes": len(self.stdout),
            "stderrBytes": len(self.stderr),
            "diagnostic": (stderr or stdout)[:1000],
        }


class CommandRunner(Protocol):
    def run(self, argv: Sequence[str]) -> CommandResult: ...


class SubprocessRunner:
    def run(self, argv: Sequence[str]) -> CommandResult:
        values = tuple(str(value) for value in argv)
        try:
            completed = subprocess.run(values, capture_output=True, check=False)
        except FileNotFoundError as error:
            return CommandResult(values, 127, b"", str(error).encode(), False)
        return CommandResult(values, completed.returncode, completed.stdout, completed.stderr)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _tree_snapshot(root: Path) -> tuple[tuple[object, ...], ...]:
    rows: list[tuple[object, ...]] = []
    for directory, names, files in os.walk(root, followlinks=False):
        base = Path(directory)
        for name in sorted([*names, *files]):
            path = base / name
            stat = path.lstat()
            rows.append(
                (
                    path.relative_to(root).as_posix(),
                    stat.st_mode,
                    stat.st_size,
                    stat.st_mtime_ns,
                    os.readlink(path) if path.is_symlink() else None,
                )
            )
    return tuple(rows)


def _critical_hashes(app: Path, executable: Path | None = None) -> dict[str, str]:
    candidates = {
        "Info.plist": app / "Contents/Info.plist",
        "executable": executable or app / "Contents/MacOS/ChatGPT",
        "app.asar": app / "Contents/Resources/app.asar",
        "CodeResources": app / "Contents/_CodeSignature/CodeResources",
    }
    return {
        name: sha256_file(path)
        for name, path in candidates.items()
        if path.is_file() and not path.is_symlink()
    }


def _run(runner: CommandRunner, *argv: str) -> CommandResult:
    try:
        return runner.run(argv)
    except FileNotFoundError as error:
        return CommandResult(tuple(argv), 127, b"", str(error).encode(), False)


def _combined(result: CommandResult) -> str:
    return "\n".join(
        part.decode("utf-8", "replace") for part in (result.stdout, result.stderr) if part
    )


def _read_info(app: Path) -> dict[str, object]:
    try:
        with (app / "Contents/Info.plist").open("rb") as handle:
            value = plistlib.load(handle)
    except (OSError, plistlib.InvalidFileException) as error:
        raise ReferenceValidationError("INVALID_STRUCTURE", "unable to parse Info.plist") from error
    if not isinstance(value, dict):
        raise ReferenceValidationError("INVALID_STRUCTURE", "Info.plist is not a dictionary")
    return value


def _parse_codesign_details(result: CommandResult) -> dict[str, object]:
    fields: dict[str, str] = {}
    authorities: list[str] = []
    text = _combined(result)
    for line in text.splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key, value = key.strip(), value.strip()
        if key == "Authority":
            authorities.append(value)
        else:
            fields[key] = value
    lower = text.lower()
    return {
        "command": result.summary(),
        "identifier": fields.get("Identifier"),
        "teamIdentifier": fields.get("TeamIdentifier"),
        "authorities": authorities,
        "hardenedRuntime": "(runtime)" in lower or "runtime version=" in lower,
        "notarizationTicket": fields.get("Notarization Ticket"),
    }


def _parse_entitlements(result: CommandResult) -> dict[str, object]:
    value: object | None = None
    valid = False
    if result.stdout:
        try:
            value = plistlib.loads(result.stdout)
            valid = isinstance(value, dict)
        except plistlib.InvalidFileException:
            valid = False
    text = _combined(result).lower()
    if not result.available:
        status = "COMMAND_UNAVAILABLE"
    elif result.returncode != 0:
        status = "COMMAND_FAILED"
    elif valid:
        status = "VALID_XML"
    elif "invalid entitlements blob" in text:
        status = "MALFORMED_XML_BLOB"
    elif not result.stdout:
        status = "NO_ENTITLEMENTS"
    else:
        status = "UNPARSEABLE_ENTITLEMENTS"
    return {
        "status": status,
        "keys": sorted(value) if isinstance(value, dict) else [],
        "command": result.summary(),
    }


def _asar_integrity(info: dict[str, object], archive: Path) -> dict[str, object]:
    metadata = info.get("ElectronAsarIntegrity")
    record = metadata.get("Resources/app.asar") if isinstance(metadata, dict) else None
    algorithm = record.get("algorithm") if isinstance(record, dict) else None
    expected = record.get("hash") if isinstance(record, dict) else None
    actual = sha256_file(archive)
    if not isinstance(expected, str):
        status = "ASAR_INTEGRITY_METADATA_MISSING"
    elif algorithm != "SHA256":
        status = "ASAR_INTEGRITY_ALGORITHM_UNSUPPORTED"
    elif expected.lower() == actual:
        status = "ASAR_INTEGRITY_MATCH"
    else:
        status = "ASAR_INTEGRITY_MISMATCH"
    return {
        "status": status,
        "algorithm": algorithm,
        "expected": expected,
        "actual": actual,
    }


def _nested_candidates(app: Path, executable: Path) -> list[Path]:
    values: set[Path] = {executable}
    for directory, names, files in os.walk(app / "Contents", followlinks=False):
        base = Path(directory)
        for name in names:
            candidate = base / name
            if candidate.suffix in {".app", ".framework", ".xpc"}:
                values.add(candidate)
        for name in files:
            candidate = base / name
            if candidate.suffix in {".dylib", ".node"}:
                values.add(candidate)
    return sorted(values, key=lambda value: value.relative_to(app).as_posix())


def _verify_nested(
    app: Path,
    executable: Path,
    runner: CommandRunner,
    components: Sequence[Path] | None,
) -> dict[str, object]:
    checks: list[dict[str, object]] = []
    first_failure: str | None = None
    for component in components if components is not None else _nested_candidates(app, executable):
        result = _run(runner, "codesign", "--verify", "--strict", "--verbose=4", str(component))
        status = "PASS" if result.returncode == 0 else "FAIL"
        if status == "FAIL" and first_failure is None:
            first_failure = str(component)
        checks.append({"path": str(component), "status": status, **result.summary()})
    return {
        "status": "PASS" if first_failure is None else "FAIL",
        "firstFailingComponent": first_failure,
        "checks": checks,
    }


def _same_path(left: Path, right: Path) -> bool:
    try:
        return left.resolve() == right.resolve()
    except OSError:
        return left.absolute() == right.absolute()


def _rejection(
    app: Path,
    classification: str,
    reason: str,
    *,
    zero_mutation: bool = True,
) -> dict[str, object]:
    return {
        "formatVersion": 1,
        "app": str(app),
        "classification": classification,
        "reason": reason,
        "zeroMutation": zero_mutation,
    }


def validate_candidate(
    app: Path,
    *,
    runner: CommandRunner | None = None,
    nested_components: Sequence[Path] | None = None,
    installed_app: Path = INSTALLED_UNTRUSTED_APP,
    expected_bundle_id: str = EXPECTED_BUNDLE_ID,
    expected_team_id: str = PHASE7A_CONFIRMED_TEAM_ID,
) -> dict[str, object]:
    candidate = Path(app)
    if _same_path(candidate, installed_app):
        return _rejection(candidate, "REJECT_STRUCTURE", "installed App is an untrusted reference")
    if candidate.is_symlink() or not candidate.is_dir():
        return _rejection(candidate, "REJECT_STRUCTURE", "candidate is not a safe App directory")

    try:
        info = _read_info(candidate)
    except ReferenceValidationError as error:
        return _rejection(candidate, "REJECT_STRUCTURE", str(error))
    executable_name = info.get("CFBundleExecutable")
    if not isinstance(executable_name, str) or not executable_name:
        return _rejection(candidate, "REJECT_STRUCTURE", "CFBundleExecutable is missing")
    executable = candidate / "Contents/MacOS" / executable_name
    archive = candidate / "Contents/Resources/app.asar"
    code_resources = candidate / "Contents/_CodeSignature/CodeResources"
    required = (executable, archive, code_resources)
    if any(path.is_symlink() or not path.is_file() for path in required):
        return _rejection(candidate, "REJECT_STRUCTURE", "required signed App resources are missing")

    before_tree = _tree_snapshot(candidate)
    before_hashes = _critical_hashes(candidate, executable)
    command_runner = runner or SubprocessRunner()

    architecture = _run(command_runner, "lipo", "-archs", str(executable))
    details_result = _run(command_runner, "codesign", "-dv", "--verbose=4", str(candidate))
    strict = _run(
        command_runner,
        "codesign",
        "--verify",
        "--deep",
        "--strict",
        "--verbose=4",
        str(candidate),
    )
    gatekeeper = _run(
        command_runner,
        "spctl",
        "--assess",
        "--type",
        "execute",
        "--verbose=4",
        str(candidate),
    )
    entitlement_result = _run(
        command_runner,
        "codesign",
        "--display",
        "--entitlements",
        "-",
        "--xml",
        str(candidate),
    )
    nested = _verify_nested(candidate, executable, command_runner, nested_components)
    details = _parse_codesign_details(details_result)
    entitlements = _parse_entitlements(entitlement_result)
    asar = _asar_integrity(info, archive)

    bundle_id = info.get("CFBundleIdentifier")
    if bundle_id != expected_bundle_id:
        classification, reason = "REJECT_IDENTITY", "bundle identifier is not the expected Codex identity"
    elif strict.returncode != 0 or gatekeeper.returncode != 0 or nested["status"] != "PASS":
        classification, reason = "REJECT_SIGNATURE", "strict, Gatekeeper, or nested signature validation failed"
    elif entitlements["status"] != "VALID_XML":
        classification, reason = "REJECT_ENTITLEMENTS", "entitlements are not a valid XML plist"
    elif asar["status"] != "ASAR_INTEGRITY_MATCH":
        classification, reason = "REJECT_ASAR_INTEGRITY", "Electron ASAR integrity metadata does not match"
    elif (
        details["identifier"] != expected_bundle_id
        or details["teamIdentifier"] != expected_team_id
        or not details["authorities"]
    ):
        classification, reason = "REJECT_IDENTITY", "signature identity or authority chain is not official"
    elif not details["hardenedRuntime"]:
        classification, reason = "REJECT_SIGNATURE", "hardened runtime is not present"
    elif architecture.returncode != 0 or not architecture.stdout.strip():
        classification, reason = "REJECT_STRUCTURE", "unable to determine executable architecture"
    else:
        classification, reason = "CLEAN_REFERENCE_PASS", "all clean official baseline gates passed"

    after_hashes = _critical_hashes(candidate, executable)
    after_tree = _tree_snapshot(candidate)
    if before_hashes != after_hashes or before_tree != after_tree:
        raise ReferenceValidationError(
            "REFERENCE_MUTATED", "read-only validation detected a candidate mutation"
        )

    architectures = architecture.stdout.decode("utf-8", "replace").strip().split()
    return {
        "formatVersion": 1,
        "app": str(candidate),
        "classification": classification,
        "reason": reason,
        "bundleIdentifier": bundle_id,
        "version": str(info.get("CFBundleShortVersionString", "")),
        "build": str(info.get("CFBundleVersion", "")),
        "architectures": architectures,
        "executable": executable.relative_to(candidate).as_posix(),
        "executableSha256": sha256_file(executable),
        "appAsarSha256": asar["actual"],
        "codesign": strict.summary(),
        "gatekeeper": gatekeeper.summary(),
        "signatureIdentity": details,
        "nestedSignatures": nested,
        "entitlements": entitlements,
        "asarIntegrity": asar,
        "criticalHashes": before_hashes,
        "zeroMutation": True,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--app", required=True, type=Path)
    parser.add_argument("--expected-team-id", default=PHASE7A_CONFIRMED_TEAM_ID)
    args = parser.parse_args()
    try:
        result = validate_candidate(args.app, expected_team_id=args.expected_team_id)
    except ReferenceValidationError as error:
        print(json.dumps({"ok": False, "error": {"code": error.code, "message": str(error)}}))
        return 2
    print(json.dumps({"ok": result["classification"] == "CLEAN_REFERENCE_PASS", "result": result}, indent=2, sort_keys=True))
    return 0 if result["classification"] == "CLEAN_REFERENCE_PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
