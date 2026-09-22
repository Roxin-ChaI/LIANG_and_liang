#!/usr/bin/env python3
"""Read-only real-App preflight and temporary-copy signing smoke for Phase 7."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import plistlib
import shutil
import subprocess
import sys
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Protocol


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_APP = Path("/Applications/ChatGPT.app")
DEFAULT_SPEC = ROOT / "runtime-patch/builds/9275/patch-spec.json"
INSTALLER = ROOT / "installer/runtime-patch-installer.py"


class Runner(Protocol):
    def run(self, command: list[str]) -> subprocess.CompletedProcess[str]: ...


class SubprocessRunner:
    def run(self, command: list[str]) -> subprocess.CompletedProcess[str]:
        return subprocess.run(command, capture_output=True, text=True)


@dataclass(frozen=True)
class AppFingerprint:
    version: str
    build: str
    app_asar_sha256: str
    executable_sha256: str
    bundle_identifier: str


@dataclass(frozen=True)
class SigningSnapshot:
    verification: str
    identifier: str | None
    team_identifier: str | None
    hardened_runtime: bool
    entitlements_xml: str | None
    details: str


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def fingerprint(app: Path) -> AppFingerprint:
    with (app / "Contents/Info.plist").open("rb") as handle:
        info = plistlib.load(handle)
    executable = app / "Contents/MacOS/ChatGPT"
    return AppFingerprint(
        version=str(info["CFBundleShortVersionString"]),
        build=str(info["CFBundleVersion"]),
        app_asar_sha256=sha256_file(app / "Contents/Resources/app.asar"),
        executable_sha256=sha256_file(executable),
        bundle_identifier=str(info["CFBundleIdentifier"]),
    )


def _field(details: str, name: str) -> str | None:
    prefix = f"{name}="
    return next((line[len(prefix) :] for line in details.splitlines() if line.startswith(prefix)), None)


def signing_snapshot(app: Path, runner: Runner) -> SigningSnapshot:
    verify = runner.run(["codesign", "--verify", "--deep", "--strict", "--verbose=2", str(app)])
    details_result = runner.run(["codesign", "-dv", "--verbose=4", str(app)])
    entitlements_result = runner.run(["codesign", "-d", "--entitlements", ":-", str(app)])
    details = "\n".join(part for part in (details_result.stdout, details_result.stderr) if part)
    entitlements = "\n".join(part for part in (entitlements_result.stdout, entitlements_result.stderr) if part)
    xml_start = entitlements.find("<?xml")
    xml_end = entitlements.rfind("</plist>")
    xml = entitlements[xml_start : xml_end + len("</plist>")] if xml_start >= 0 and xml_end >= xml_start else None
    return SigningSnapshot(
        verification="PASS" if verify.returncode == 0 else "FAIL",
        identifier=_field(details, "Identifier"),
        team_identifier=_field(details, "TeamIdentifier"),
        hardened_runtime="flags=0x10000(runtime)" in details or "flags=0x10000" in details,
        entitlements_xml=xml,
        details=details,
    )


def _entitlement_keys(xml: str | None) -> list[str]:
    if xml is None:
        return []
    try:
        value = plistlib.loads(xml.encode())
    except plistlib.InvalidFileException:
        return []
    return sorted(value) if isinstance(value, dict) else []


def adhoc_sign(app: Path, baseline: SigningSnapshot, runner: Runner, work_dir: Path) -> dict[str, object]:
    if baseline.entitlements_xml is None:
        return {"result": "ADHOC_SIGNING_UNSAFE", "reason": "baseline entitlements are unavailable or invalid"}
    entitlements = work_dir / "preserved-entitlements.plist"
    entitlements.write_text(baseline.entitlements_xml)
    signed = runner.run(["codesign", "--force", "--deep", "--sign", "-", "--entitlements", str(entitlements), str(app)])
    if signed.returncode != 0:
        return {"result": "ADHOC_SIGNING_FAIL", "reason": "codesign rejected the preserved-entitlements strategy"}
    verified = runner.run(["codesign", "--verify", "--deep", "--strict", "--verbose=2", str(app)])
    after = signing_snapshot(app, runner)
    before_keys = _entitlement_keys(baseline.entitlements_xml)
    after_keys = _entitlement_keys(after.entitlements_xml)
    return {
        "result": "PASS" if verified.returncode == 0 else "FAIL",
        "reason": "preserved-entitlements ad-hoc signature",
        "expectedEntitlementKeys": before_keys,
        "actualEntitlementKeys": after_keys,
        "entitlementsPreserved": before_keys == after_keys,
    }


def _load_target(spec_path: Path) -> dict[str, str]:
    return json.loads(spec_path.read_text())["target"]


def preflight(app: Path, spec_path: Path = DEFAULT_SPEC) -> tuple[AppFingerprint, bool]:
    observed = fingerprint(app)
    target = _load_target(spec_path)
    supported = (
        observed.version == target["version"]
        and observed.build == target["build"]
        and observed.app_asar_sha256 == target["appAsarSha256"]
    )
    return observed, supported


def smoke(
    source_app: Path = DEFAULT_APP,
    *,
    spec_path: Path = DEFAULT_SPEC,
    temp_parent: Path | None = None,
    runner: Runner | None = None,
) -> tuple[dict[str, object], int]:
    command_runner = runner or SubprocessRunner()
    before, supported = preflight(source_app, spec_path)
    baseline_signing = signing_snapshot(source_app, command_runner)
    report: dict[str, object] = {
        "sourceBefore": asdict(before),
        "baselineSigning": asdict(baseline_signing),
        "target": _load_target(spec_path),
    }
    if not supported:
        after = fingerprint(source_app)
        report.update(
            {
                "status": "BLOCKED_UNSUPPORTED_BUILD",
                "tempCopyCreated": False,
                "patchedSigning": "NOT_TESTED_BUILD_MISMATCH",
                "adhocSigning": "NOT_TESTED_BUILD_MISMATCH",
                "entitlementsPreservation": "BLOCKED_BASELINE_ENTITLEMENTS_INVALID" if baseline_signing.entitlements_xml is None else "NOT_TESTED_BUILD_MISMATCH",
                "sourceUnchanged": after == before,
            }
        )
        return report, 2

    parent = temp_parent or Path(tempfile.gettempdir()) / "liang-no-henshin-app-test"
    if parent.exists():
        raise RuntimeError(f"temporary smoke destination already exists: {parent}")
    parent.mkdir(parents=True)
    temp_app = parent / "ChatGPT.app"
    shutil.copytree(source_app, temp_app, symlinks=True)
    copy_before = fingerprint(temp_app)
    temp_signing_before = signing_snapshot(temp_app, command_runner)
    if copy_before != before or temp_signing_before.verification != "PASS" or temp_signing_before.entitlements_xml is None:
        raise RuntimeError("TEMP_COPY_BASELINE_INVALID")
    patch = command_runner.run([sys.executable, str(INSTALLER), "--app", str(temp_app), "--spec", str(spec_path), "--patch"])
    if patch.returncode != 0:
        raise RuntimeError(f"temp patch failed: {patch.stderr or patch.stdout}")
    patched = fingerprint(temp_app)
    unsigned = signing_snapshot(temp_app, command_runner)
    signing = adhoc_sign(temp_app, temp_signing_before, command_runner, parent)
    signed_patched = fingerprint(temp_app)
    restore = command_runner.run([sys.executable, str(INSTALLER), "--app", str(temp_app), "--restore"])
    if restore.returncode != 0:
        raise RuntimeError(f"temp restore failed: {restore.stderr or restore.stdout}")
    restored = fingerprint(temp_app)
    source_after = fingerprint(source_app)
    report.update(
        {
            "status": "PASS",
            "tempCopyCreated": True,
            "tempBefore": asdict(copy_before),
            "tempSigningBefore": asdict(temp_signing_before),
            "tempPatched": asdict(patched),
            "patchedSigning": asdict(unsigned),
            "adhocSigning": signing,
            "patchedAsarUnchangedBySigning": signed_patched.app_asar_sha256 == patched.app_asar_sha256,
            "contentRestore": "PASS" if restored.app_asar_sha256 == copy_before.app_asar_sha256 else "FAIL",
            "signatureRestore": "NOT_RESTORED_BY_ASAR_CONTENT_RESTORE",
            "bundleIdUnchanged": restored.bundle_identifier == copy_before.bundle_identifier,
            "executableUnchangedByPatch": patched.executable_sha256 == copy_before.executable_sha256,
            "sourceUnchanged": source_after == before,
        }
    )
    (parent / "smoke-report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    return report, 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--app", type=Path, default=DEFAULT_APP)
    parser.add_argument("--spec", type=Path, default=DEFAULT_SPEC)
    parser.add_argument("--temp-parent", type=Path)
    args = parser.parse_args()
    report, status = smoke(args.app, spec_path=args.spec, temp_parent=args.temp_parent)
    print(json.dumps(report, indent=2, sort_keys=True))
    return status


if __name__ == "__main__":
    raise SystemExit(main())
