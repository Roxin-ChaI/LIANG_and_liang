#!/usr/bin/env python3
"""Discover and validate clean Codex Desktop App references without mutation."""

from __future__ import annotations

import argparse
import json
import plistlib
from pathlib import Path
from typing import Callable, Sequence

try:
    from validate_clean_codex_reference import (
        INSTALLED_UNTRUSTED_APP,
        SubprocessRunner,
        sha256_file,
        validate_candidate,
    )
except ModuleNotFoundError:  # Imported as tools.find_clean_codex_reference.
    from tools.validate_clean_codex_reference import (
        INSTALLED_UNTRUSTED_APP,
        SubprocessRunner,
        sha256_file,
        validate_candidate,
    )


Validator = Callable[[Path], dict[str, object]]


def candidate_paths(
    *,
    explicit_apps: Sequence[Path] = (),
    home: Path | None = None,
    volumes_root: Path = Path("/Volumes"),
) -> list[Path]:
    user_home = home or Path.home()
    values: list[Path] = [Path(value) for value in explicit_apps]
    if volumes_root.is_dir():
        for volume in sorted(volumes_root.iterdir()):
            if volume.is_dir():
                values.extend((volume / "ChatGPT.app", volume / "Codex.app"))
    for directory in (user_home / "Downloads", user_home / "Desktop"):
        if directory.is_dir():
            values.extend(sorted(directory.glob("ChatGPT*.app")))
            values.extend(sorted(directory.glob("Codex*.app")))

    unique: list[Path] = []
    seen: set[str] = set()
    for value in values:
        if not value.exists() and not value.is_symlink():
            continue
        key = str(value.absolute())
        if key not in seen:
            seen.add(key)
            unique.append(value)
    return unique


def _installed_summary(app: Path = INSTALLED_UNTRUSTED_APP) -> dict[str, object] | None:
    if not app.is_dir() or app.is_symlink():
        return None
    try:
        with (app / "Contents/Info.plist").open("rb") as handle:
            info = plistlib.load(handle)
        executable_name = info.get("CFBundleExecutable", "ChatGPT")
        executable = app / "Contents/MacOS" / executable_name
        archive = app / "Contents/Resources/app.asar"
        metadata = info.get("ElectronAsarIntegrity")
        record = metadata.get("Resources/app.asar") if isinstance(metadata, dict) else None
        strict = SubprocessRunner().run(
            ("codesign", "--verify", "--deep", "--strict", "--verbose=4", str(app))
        )
    except (OSError, plistlib.InvalidFileException):
        return None
    hashes = {
        "Info.plist": sha256_file(app / "Contents/Info.plist"),
        "app.asar": sha256_file(archive),
    }
    if executable.is_file():
        hashes["executable"] = sha256_file(executable)
    code_resources = app / "Contents/_CodeSignature/CodeResources"
    if code_resources.is_file():
        hashes["CodeResources"] = sha256_file(code_resources)
    return {
        "version": str(info.get("CFBundleShortVersionString", "")),
        "build": str(info.get("CFBundleVersion", "")),
        "appAsarSha256": hashes["app.asar"],
        "asarIntegrityExpected": record.get("hash") if isinstance(record, dict) else None,
        "codesignStrictReturncode": strict.returncode,
        "criticalHashes": hashes,
    }


def _comparison(clean: dict[str, object], installed: dict[str, object]) -> dict[str, object]:
    clean_hashes = clean.get("criticalHashes")
    installed_hashes = installed.get("criticalHashes")
    changed: dict[str, dict[str, object]] = {}
    if isinstance(clean_hashes, dict) and isinstance(installed_hashes, dict):
        for name in sorted(set(clean_hashes) | set(installed_hashes)):
            clean_value = clean_hashes.get(name)
            installed_value = installed_hashes.get(name)
            if clean_value != installed_value:
                changed[name] = {"clean": clean_value, "installed": installed_value}
    asar = clean.get("asarIntegrity")
    return {
        "sameVersion": clean.get("version") == installed.get("version"),
        "sameBuild": clean.get("build") == installed.get("build"),
        "cleanVersion": clean.get("version"),
        "installedVersion": installed.get("version"),
        "cleanBuild": clean.get("build"),
        "installedBuild": installed.get("build"),
        "cleanAppAsarSha256": clean.get("appAsarSha256"),
        "installedAppAsarSha256": installed.get("appAsarSha256"),
        "cleanAsarIntegrityExpected": asar.get("expected") if isinstance(asar, dict) else None,
        "installedAsarIntegrityExpected": installed.get("asarIntegrityExpected"),
        "cleanCodesignStrictReturncode": clean.get("codesign", {}).get("returncode")
        if isinstance(clean.get("codesign"), dict)
        else None,
        "installedCodesignStrictReturncode": installed.get("codesignStrictReturncode"),
        "changedCriticalHashes": changed,
    }


def discover_and_validate(
    *,
    explicit_apps: Sequence[Path] = (),
    home: Path | None = None,
    volumes_root: Path = Path("/Volumes"),
    validator: Validator = validate_candidate,
    installed_app: Path = INSTALLED_UNTRUSTED_APP,
) -> dict[str, object]:
    candidates = candidate_paths(
        explicit_apps=explicit_apps,
        home=home,
        volumes_root=volumes_root,
    )
    results = [validator(candidate) for candidate in candidates]
    passed = [result for result in results if result.get("classification") == "CLEAN_REFERENCE_PASS"]
    if passed:
        status = "CLEAN_REFERENCE_PASS"
    elif candidates:
        status = "CLEAN_REFERENCE_INVALID"
    else:
        status = "CLEAN_OFFICIAL_APP_REQUIRED"
    installed = _installed_summary(installed_app) if passed else None
    comparisons = [
        {"cleanApp": item.get("app"), **_comparison(item, installed)}
        for item in passed
        if installed is not None
    ]
    return {
        "formatVersion": 1,
        "status": status,
        "candidateCount": len(candidates),
        "passCount": len(passed),
        "candidates": results,
        "installedComparison": comparisons,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--app", action="append", default=[], type=Path)
    args = parser.parse_args()
    result = discover_and_validate(explicit_apps=args.app)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] == "CLEAN_REFERENCE_PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
