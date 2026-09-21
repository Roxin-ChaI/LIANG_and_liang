#!/usr/bin/env python3
"""Read-only Codex app signing, entitlement, and ASAR-integrity diagnosis."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import plistlib
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Protocol, Sequence


class SigningDiagnosisError(RuntimeError):
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
        stderr = self.stderr.decode("utf-8", "replace").strip()
        stdout = self.stdout.decode("utf-8", "replace").strip()
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
            relative = path.relative_to(root).as_posix()
            target = os.readlink(path) if path.is_symlink() else None
            rows.append((relative, stat.st_mode, stat.st_size, stat.st_mtime_ns, target))
    return tuple(rows)


def _critical_hashes(app: Path) -> dict[str, str]:
    candidates = {
        "Info.plist": app / "Contents/Info.plist",
        "executable": app / "Contents/MacOS/ChatGPT",
        "app.asar": app / "Contents/Resources/app.asar",
        "CodeResources": app / "Contents/_CodeSignature/CodeResources",
    }
    return {name: sha256_file(path) for name, path in candidates.items() if path.is_file()}


def _read_info(app: Path) -> dict[str, object]:
    path = app / "Contents/Info.plist"
    try:
        with path.open("rb") as handle:
            value = plistlib.load(handle)
    except (OSError, plistlib.InvalidFileException) as error:
        raise SigningDiagnosisError("INVALID_APP", "unable to read app Info.plist") from error
    if not isinstance(value, dict):
        raise SigningDiagnosisError("INVALID_APP", "app Info.plist is not a dictionary")
    return value


def _run(runner: CommandRunner, *argv: str) -> CommandResult:
    try:
        return runner.run(argv)
    except FileNotFoundError as error:
        return CommandResult(tuple(argv), 127, b"", str(error).encode(), False)


def _combined(result: CommandResult) -> str:
    return "\n".join(
        part.decode("utf-8", "replace") for part in (result.stdout, result.stderr) if part
    )


def _parse_codesign_details(result: CommandResult) -> dict[str, object]:
    text = _combined(result)
    fields: dict[str, str] = {}
    for line in text.splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            fields[key.strip()] = value.strip()
    return {
        "command": result.summary(),
        "identifier": fields.get("Identifier"),
        "teamIdentifier": fields.get("TeamIdentifier"),
        "authority": fields.get("Authority"),
        "flags": fields.get("CodeDirectory", ""),
        "runtime": fields.get("Runtime Version"),
        "notarizationTicket": fields.get("Notarization Ticket"),
        "infoPlistBinding": fields.get("Info.plist"),
    }


def _entitlement_status(
    abstract: CommandResult,
    xml: CommandResult,
    der: CommandResult,
    legacy: CommandResult,
) -> dict[str, object]:
    xml_value: object | None = None
    xml_valid = False
    if xml.stdout:
        try:
            xml_value = plistlib.loads(xml.stdout)
            xml_valid = isinstance(xml_value, dict)
        except plistlib.InvalidFileException:
            xml_valid = False
    xml_text = _combined(xml).lower()
    legacy_text = _combined(legacy).lower()
    if not xml.available:
        status = "COMMAND_UNAVAILABLE"
    elif xml.returncode != 0:
        status = "COMMAND_FAILED"
    elif xml_valid:
        status = "VALID_XML"
    elif "invalid entitlements blob" in xml_text or "invalid entitlements blob" in legacy_text:
        status = "MALFORMED_XML_BLOB"
    elif not xml.stdout and not abstract.stdout and not der.stdout:
        status = "NO_ENTITLEMENTS"
    else:
        status = "UNPARSEABLE_ENTITLEMENTS"
    keys = sorted(xml_value) if isinstance(xml_value, dict) else []
    return {
        "status": status,
        "xmlValid": xml_valid,
        "keys": keys,
        "abstract": abstract.summary(),
        "xml": xml.summary(),
        "der": {**der.summary(), "present": bool(der.stdout)},
        "legacyColon": legacy.summary(),
    }


def _asar_integrity(info: dict[str, object], archive: Path) -> dict[str, object]:
    metadata = info.get("ElectronAsarIntegrity")
    record = metadata.get("Resources/app.asar") if isinstance(metadata, dict) else None
    expected = record.get("hash") if isinstance(record, dict) else None
    algorithm = record.get("algorithm") if isinstance(record, dict) else None
    actual = sha256_file(archive)
    if not isinstance(expected, str):
        status = "ASAR_INTEGRITY_METADATA_MISSING"
    elif algorithm != "SHA256":
        status = "ASAR_INTEGRITY_ALGORITHM_UNSUPPORTED"
    elif expected.lower() == actual:
        status = "ASAR_INTEGRITY_MATCH"
    else:
        status = "ASAR_INTEGRITY_MISMATCH"
    return {"status": status, "algorithm": algorithm, "expected": expected, "actual": actual}


def _nested_candidates(app: Path) -> list[Path]:
    values: set[Path] = {app / "Contents/MacOS/ChatGPT"}
    for directory, names, files in os.walk(app / "Contents", followlinks=False):
        base = Path(directory)
        for name in names:
            path = base / name
            if path.suffix in {".app", ".framework", ".xpc"}:
                values.add(path)
        for name in files:
            path = base / name
            if path.suffix in {".dylib", ".node"}:
                values.add(path)
    return sorted(values, key=lambda path: path.relative_to(app).as_posix())


def _verify_components(
    app: Path, runner: CommandRunner, components: Sequence[Path] | None
) -> dict[str, object]:
    checks: list[dict[str, object]] = []
    first_failure: str | None = None
    main = _run(runner, "codesign", "--verify", "--strict", "--verbose=4", str(app))
    if main.returncode != 0:
        first_failure = str(app)
    checks.append({"path": str(app), "kind": "main", **main.summary()})
    for component in components if components is not None else _nested_candidates(app):
        result = _run(runner, "codesign", "--verify", "--strict", "--verbose=4", str(component))
        text = _combined(result).lower()
        if result.returncode == 0:
            status = "PASS"
        elif "not signed at all" in text:
            status = "UNSIGNED"
        elif not result.available:
            status = "COMMAND_UNAVAILABLE"
        else:
            status = "FAIL"
            if first_failure is None:
                first_failure = str(component)
        checks.append({"path": str(component), "kind": "nested", "status": status, **result.summary()})
    return {
        "firstFailingComponent": first_failure,
        "checks": checks,
        "passCount": sum(item.get("returncode") == 0 for item in checks),
        "failCount": sum(item.get("status") == "FAIL" or (item["kind"] == "main" and item.get("returncode") != 0) for item in checks),
        "unsignedCount": sum(item.get("status") == "UNSIGNED" for item in checks),
    }


def _clean_reference(app: Path, roots: Sequence[Path] | None) -> dict[str, object]:
    search_roots = list(roots) if roots is not None else [Path("/Applications"), Path.home() / "Applications"]
    matches: list[str] = []
    for root in search_roots:
        if not root.is_dir():
            continue
        for candidate in sorted(root.glob("*.app")):
            try:
                if candidate.resolve() == app.resolve():
                    continue
                info = _read_info(candidate)
            except (OSError, SigningDiagnosisError):
                continue
            if info.get("CFBundleIdentifier") == "com.openai.codex":
                matches.append(str(candidate))
    return {
        "status": "CLEAN_REFERENCE_AVAILABLE" if matches else "CLEAN_REFERENCE_UNAVAILABLE",
        "candidates": matches,
    }


def _historical_evidence(app: Path, runner: CommandRunner) -> dict[str, object]:
    resources = app / "Contents/Resources"
    remnants: list[str] = []
    for name in (
        "app.asar.liang-original",
        ".liang-runtime-patch-state.json",
        "app.asar.backup",
        "app.asar.bak",
    ):
        if (resources / name).exists():
            remnants.append(name)
    archive = resources / "app.asar"
    executable = app / "Contents/MacOS/ChatGPT"
    xattrs = _run(runner, "xattr", "-l", str(app))
    return {
        "remnants": remnants,
        "appMtimeNs": app.stat().st_mtime_ns,
        "asarMtimeNs": archive.stat().st_mtime_ns,
        "executableMtimeNs": executable.stat().st_mtime_ns,
        "xattrs": xattrs.summary(),
        "mtimeInference": "NOT_USED_AS_CAUSE",
    }


def diagnose(
    app: Path,
    *,
    runner: CommandRunner | None = None,
    nested_components: Sequence[Path] | None = None,
    clean_roots: Sequence[Path] | None = None,
) -> dict[str, object]:
    candidate = Path(app)
    if not candidate.is_dir() or candidate.is_symlink():
        raise SigningDiagnosisError("INVALID_APP", "app must be an existing non-symlink directory")
    archive = candidate / "Contents/Resources/app.asar"
    if not archive.is_file() or archive.is_symlink():
        raise SigningDiagnosisError("INVALID_APP", "app.asar is missing or unsafe")
    command_runner = runner or SubprocessRunner()
    before_tree = _tree_snapshot(candidate)
    before_hashes = _critical_hashes(candidate)
    info = _read_info(candidate)

    details = _run(command_runner, "codesign", "-dv", "--verbose=4", str(candidate))
    deep_verify = _run(
        command_runner, "codesign", "--verify", "--deep", "--strict", "--verbose=4", str(candidate)
    )
    abstract_entitlements = _run(
        command_runner, "codesign", "--display", "--entitlements", "-", str(candidate)
    )
    xml_entitlements = _run(
        command_runner, "codesign", "--display", "--entitlements", "-", "--xml", str(candidate)
    )
    der_entitlements = _run(
        command_runner, "codesign", "--display", "--entitlements", "-", "--der", str(candidate)
    )
    legacy_entitlements = _run(
        command_runner, "codesign", "--display", "--entitlements", ":-", str(candidate)
    )
    gatekeeper = _run(
        command_runner, "spctl", "--assess", "--type", "execute", "--verbose=4", str(candidate)
    )

    entitlements = _entitlement_status(
        abstract_entitlements, xml_entitlements, der_entitlements, legacy_entitlements
    )
    asar = _asar_integrity(info, archive)
    components = _verify_components(candidate, command_runner, nested_components)
    clean = _clean_reference(candidate, clean_roots)
    historical = _historical_evidence(candidate, command_runner)

    causes: list[dict[str, str]] = []
    if asar["status"] == "ASAR_INTEGRITY_MISMATCH":
        causes.append(
            {
                "cause": "ASAR_INTEGRITY_MISMATCH",
                "confidence": "CONFIRMED",
                "meaning": "app.asar differs from the SHA256 sealed in ElectronAsarIntegrity",
            }
        )
    if entitlements["status"] == "MALFORMED_XML_BLOB":
        causes.append(
            {
                "cause": "MALFORMED_XML_ENTITLEMENTS_BLOB",
                "confidence": "CONFIRMED",
                "meaning": "codesign can expose abstract/DER data but cannot extract a valid XML entitlement plist",
            }
        )
    if deep_verify.returncode != 0 and not causes:
        causes.append(
            {
                "cause": "SIGNATURE_VERIFY_FAILURE",
                "confidence": "UNKNOWN",
                "meaning": "strict verification failed without a more specific confirmed cause",
            }
        )
    if causes and all(item["confidence"] == "CONFIRMED" for item in causes):
        classification = "BASELINE_SIGNING_CAUSE_CONFIRMED"
    elif causes:
        classification = "BASELINE_SIGNING_CAUSE_LIKELY"
    else:
        classification = "BASELINE_SIGNING_CAUSE_UNKNOWN"
    temp_signing = (
        "TEMP_SIGNING_EXPERIMENT_ALLOWED"
        if entitlements["status"] == "VALID_XML"
        else "TEMP_SIGNING_EXPERIMENT_BLOCKED"
    )

    after_hashes = _critical_hashes(candidate)
    after_tree = _tree_snapshot(candidate)
    if before_hashes != after_hashes or before_tree != after_tree:
        raise SigningDiagnosisError("APP_MUTATED", "read-only diagnosis detected an app bundle mutation")

    return {
        "formatVersion": 1,
        "app": str(candidate),
        "bundleIdentifier": info.get("CFBundleIdentifier"),
        "version": str(info.get("CFBundleShortVersionString", "")),
        "build": str(info.get("CFBundleVersion", "")),
        "codesignDetails": _parse_codesign_details(details),
        "codesignDeepStrict": deep_verify.summary(),
        "gatekeeper": gatekeeper.summary(),
        "entitlements": entitlements,
        "asarIntegrity": asar,
        "components": components,
        "historicalEvidence": historical,
        "cleanReference": clean,
        "causeClassification": classification,
        "causes": causes,
        "tempSigningExperiment": temp_signing,
        "zeroMutation": True,
        "criticalHashes": before_hashes,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--app", type=Path, default=Path("/Applications/ChatGPT.app"))
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()
    try:
        report = diagnose(args.app)
    except SigningDiagnosisError as error:
        print(json.dumps({"ok": False, "error": {"code": error.code, "message": str(error)}}))
        return 1
    encoded = json.dumps({"ok": True, "result": report}, indent=2, sort_keys=True) + "\n"
    if args.json_out is not None:
        args.json_out.write_text(encoded)
    print(encoded, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
