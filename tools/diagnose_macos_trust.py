#!/usr/bin/env python3
"""Read-only macOS code-signing trust environment diagnosis.

This tool never changes trust settings, keychains, applications, Gatekeeper,
or running security services.  Certificate extraction is confined to a
temporary directory and the certificate files are deleted after inspection.
"""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import os
import plistlib
import re
import shutil
import struct
import subprocess
import tempfile
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator, Protocol, Sequence


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REPORT = ROOT / "docs/macos-trust-diagnosis.md"
TRUSTED_BASELINE = ROOT / "runtime-patch/builds/9922/trusted-baseline.json"
OFFICIAL_DMG_URL = "https://persistent.oaistatic.com/codex-app-prod/ChatGPT.dmg"
OFFICIAL_DMG_SHA256 = "f4bc8e95f921f45c3f1d1891ead21eafdbe8e40612eb34cf0be173988c1996dd"
OFFICIAL_DMG_SIZE = 645_200_049
SYSTEM_TARGETS = (
    Path("/System/Applications/Calculator.app"),
    Path("/System/Applications/TextEdit.app"),
)
INSTALLED_CHATGPT = Path("/Applications/ChatGPT.app")

STRUCTURAL_FAILURE_MARKERS = (
    "a sealed resource is missing or invalid",
    "sealed resource is missing or invalid",
    "code object is not signed at all",
    "invalid signature",
    "code or signature have been modified",
    "resource envelope is obsolete",
    "unsealed contents present",
    "modified resource",
)
TRUST_FAILURE_MARKERS = (
    "cssmerr_tp_not_trusted",
    "certificate chain had an error",
    "not trusted",
)
EXPLICIT_DENY_MARKERS = ("deny", "trustroot = 3", "trustasroot = 3")


@dataclass(frozen=True)
class CommandResult:
    argv: tuple[str, ...]
    returncode: int
    stdout: str = ""
    stderr: str = ""

    @property
    def combined(self) -> str:
        return "\n".join(part for part in (self.stdout, self.stderr) if part)


class Runner(Protocol):
    def run(
        self, argv: Sequence[str], *, cwd: Path | None = None
    ) -> CommandResult: ...


class SubprocessRunner:
    def run(
        self, argv: Sequence[str], *, cwd: Path | None = None
    ) -> CommandResult:
        values = tuple(str(value) for value in argv)
        try:
            completed = subprocess.run(
                values,
                cwd=cwd,
                capture_output=True,
                text=True,
                check=False,
            )
        except FileNotFoundError as error:
            return CommandResult(values, 127, "", str(error))
        return CommandResult(
            values, completed.returncode, completed.stdout, completed.stderr
        )


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def raw_asar_header_hash(path: Path) -> str | None:
    try:
        with path.open("rb") as handle:
            prefix = handle.read(8)
            pickle_size, header_size = struct.unpack("<II", prefix)
            if pickle_size != 4 or not 12 <= header_size <= 64 * 1024 * 1024:
                return None
            header = handle.read(header_size)
            payload_size, json_size = struct.unpack("<II", header[:8])
            if len(header) != header_size or payload_size != header_size - 4:
                return None
            if json_size > header_size - 8:
                return None
    except (OSError, struct.error):
        return None
    return hashlib.sha256(header[8 : 8 + json_size]).hexdigest()


def _redact(text: str) -> str:
    user = os.environ.get("USER") or ""
    home = os.fspath(Path.home())
    value = text.replace(home, "<HOME>")
    if user:
        value = re.sub(rf"(?<![A-Za-z0-9]){re.escape(user)}(?![A-Za-z0-9])", "<USER>", value)
    value = re.sub(
        r"/private/(?:var/folders|tmp)/[^\s\"']+", "<TEMP>", value
    )
    return value


def _summary(result: CommandResult, *, limit: int = 4000) -> dict[str, object]:
    return {
        "returncode": result.returncode,
        "output": _redact(result.combined.strip())[:limit],
    }


def parse_verification(result: CommandResult) -> dict[str, object]:
    lower = result.combined.lower()
    structural_markers = [
        marker for marker in STRUCTURAL_FAILURE_MARKERS if marker in lower
    ]
    trust_markers = [marker for marker in TRUST_FAILURE_MARKERS if marker in lower]
    if result.returncode == 0:
        structural = "STRUCTURAL_SIGNATURE_INTACT"
        trust = "TRUST_EVALUATION_PASS"
    elif structural_markers:
        structural = "STRUCTURAL_SIGNATURE_FAILED"
        trust = "NOT_SEPARABLE_FROM_STRUCTURAL_FAILURE"
    elif trust_markers:
        structural = "STRUCTURAL_SIGNATURE_INTACT"
        trust = "TRUST_EVALUATION_FAILED"
    else:
        structural = "STRUCTURAL_SIGNATURE_UNKNOWN"
        trust = "TRUST_EVALUATION_UNKNOWN"
    return {
        "structural": structural,
        "trust": trust,
        "structuralMarkers": structural_markers,
        "trustMarkers": trust_markers,
        **_summary(result),
    }


def parse_certificate_text(text: str, now: datetime) -> dict[str, object]:
    fields: dict[str, str] = {}
    for line in text.splitlines():
        if "=" in line:
            key, value = line.strip().split("=", 1)
            fields[key.lower()] = value.strip()
    result: dict[str, object] = {
        "subject": fields.get("subject"),
        "issuer": fields.get("issuer"),
        "serial": fields.get("serial"),
        "notBefore": fields.get("notbefore"),
        "notAfter": fields.get("notafter"),
        "sha256Fingerprint": fields.get("sha256 fingerprint"),
        "dateValidity": "UNKNOWN",
    }
    try:
        not_before = datetime.strptime(fields["notbefore"], "%b %d %H:%M:%S %Y %Z").replace(tzinfo=timezone.utc)
        not_after = datetime.strptime(fields["notafter"], "%b %d %H:%M:%S %Y %Z").replace(tzinfo=timezone.utc)
        current = now.astimezone(timezone.utc)
        if current < not_before:
            result["dateValidity"] = "NOT_YET_VALID"
        elif current > not_after:
            result["dateValidity"] = "EXPIRED"
        else:
            result["dateValidity"] = "VALID"
    except (KeyError, ValueError):
        pass
    return result


def _extract_certificates(
    app: Path, runner: Runner, now: datetime
) -> tuple[list[dict[str, object]], list[Path], Path]:
    directory = Path(tempfile.mkdtemp(prefix="liang-trust-certs-"))
    prefix = directory / "signer"
    extraction = runner.run(
        ["codesign", "-d", "--extract-certificates", str(prefix), str(app)]
    )
    paths = sorted(directory.glob("signer*")) if extraction.returncode == 0 else []
    certificates: list[dict[str, object]] = []
    for path in paths:
        parsed = runner.run(
            [
                "openssl",
                "x509",
                "-inform",
                "DER",
                "-in",
                str(path),
                "-noout",
                "-subject",
                "-issuer",
                "-serial",
                "-dates",
                "-fingerprint",
                "-sha256",
            ]
        )
        item = parse_certificate_text(parsed.stdout, now)
        item["index"] = len(certificates)
        item["parseReturncode"] = parsed.returncode
        certificates.append(item)
    return certificates, paths, directory


def _verify_certificate_chain(
    paths: list[Path], runner: Runner
) -> dict[str, object]:
    if not paths:
        return {"status": "CERTIFICATE_CHAIN_UNAVAILABLE", "returncode": None, "output": ""}
    command = ["security", "verify-cert"]
    for path in paths:
        command.extend(("-c", str(path)))
    command.extend(("-p", "codeSign", "-v"))
    result = runner.run(command)
    lower = result.combined.lower()
    status = (
        "SUCCESS"
        if result.returncode == 0
        else "CSSMERR_TP_NOT_TRUSTED"
        if "cssmerr_tp_not_trusted" in lower or "not trusted" in lower
        else "FAILED"
    )
    return {"status": status, **_summary(result)}


def inspect_app(
    name: str,
    app: Path,
    *,
    runner: Runner,
    now: datetime,
) -> dict[str, object]:
    if not app.is_dir():
        return {"name": name, "path": str(app), "present": False}
    details = runner.run(["codesign", "-dv", "--verbose=4", str(app)])
    verify4 = runner.run(
        ["codesign", "--verify", "--deep", "--strict", "--verbose=4", str(app)]
    )
    verify6 = runner.run(
        ["codesign", "--verify", "--deep", "--strict", "--verbose=6", str(app)]
    )
    requirement = runner.run(["codesign", "-d", "-r-", str(app)])
    gatekeeper = runner.run(
        ["spctl", "--assess", "--type", "execute", "--verbose=4", str(app)]
    )
    certificates, cert_paths, cert_directory = _extract_certificates(app, runner, now)
    try:
        chain = _verify_certificate_chain(cert_paths, runner)
    finally:
        shutil.rmtree(cert_directory, ignore_errors=True)
    verify = parse_verification(verify6)
    result: dict[str, object] = {
        "name": name,
        "path": _redact(str(app)),
        "present": True,
        "details": _summary(details),
        "verifyVerbose4": parse_verification(verify4),
        "verifyVerbose6": verify,
        "designatedRequirement": {
            "parseable": requirement.returncode == 0 and "designated" in requirement.combined,
            **_summary(requirement),
        },
        "certificates": certificates,
        "certificateChain": chain,
        "gatekeeper": {
            "status": "ACCEPTED" if gatekeeper.returncode == 0 else "REJECTED",
            **_summary(gatekeeper),
        },
    }
    plist_path = app / "Contents/Info.plist"
    archive = app / "Contents/Resources/app.asar"
    if plist_path.is_file() and archive.is_file():
        try:
            with plist_path.open("rb") as handle:
                info = plistlib.load(handle)
            record = info.get("ElectronAsarIntegrity", {}).get("Resources/app.asar", {})
            actual_header = raw_asar_header_hash(archive)
            result["identity"] = {
                "bundleIdentifier": info.get("CFBundleIdentifier"),
                "version": info.get("CFBundleShortVersionString"),
                "build": info.get("CFBundleVersion"),
            }
            result["asarIntegrity"] = {
                "archiveSha256": sha256_file(archive),
                "algorithm": record.get("algorithm"),
                "expected": record.get("hash"),
                "actual": actual_header,
                "status": (
                    "PASS"
                    if record.get("algorithm") == "SHA256"
                    and record.get("hash") == actual_header
                    else "FAIL"
                ),
            }
        except (OSError, plistlib.InvalidFileException):
            result["asarIntegrity"] = {"status": "UNAVAILABLE"}
    return result


def inspect_trust_settings(runner: Runner) -> dict[str, object]:
    scopes = {
        "user": ["security", "dump-trust-settings"],
        "admin": ["security", "dump-trust-settings", "-d"],
        "system": ["security", "dump-trust-settings", "-s"],
    }
    result: dict[str, object] = {}
    for name, command in scopes.items():
        observed = runner.run(command)
        lower = observed.combined.lower()
        result[name] = {
            "status": "READABLE" if observed.returncode == 0 else "UNAVAILABLE",
            "explicitDeny": any(marker in lower for marker in EXPLICIT_DENY_MARKERS),
            **_summary(observed, limit=2000),
        }
    return result


def inspect_roots(runner: Runner) -> dict[str, object]:
    names = (
        "Apple Root CA",
        "Apple Root CA - G2",
        "Apple Root CA - G3",
        "Developer ID Certification Authority",
        "Apple Worldwide Developer Relations Certification Authority",
    )
    values: dict[str, object] = {}
    for name in names:
        result = runner.run(["security", "find-certificate", "-a", "-c", name, "-Z"])
        values[name] = {
            "present": result.returncode == 0 and "SHA-256 hash:" in result.combined,
            "returncode": result.returncode,
        }
    return values


def _service_status(runner: Runner, label: str) -> dict[str, object]:
    result = runner.run(["launchctl", "print", label])
    return {
        "status": "RUNNING" if result.returncode == 0 and "state = running" in result.combined else "UNAVAILABLE_OR_NOT_RUNNING",
        **_summary(result, limit=1000),
    }


def inspect_services(runner: Runner) -> dict[str, object]:
    uid = os.getuid()
    trustd_system = _service_status(runner, "system/com.apple.trustd")
    trustd_gui = _service_status(runner, f"gui/{uid}/com.apple.trustd")
    securityd = _service_status(runner, "system/com.apple.securityd")
    processes = runner.run(["ps", "-axo", "pid=,comm="])
    process_text = processes.stdout.lower()
    return {
        "trustdSystem": trustd_system,
        "trustdGui": trustd_gui,
        "securityd": securityd,
        "processCheck": {
            "trustd": "trustd" in process_text,
            "securityd": "securityd" in process_text,
            "returncode": processes.returncode,
        },
    }


def inspect_logs(runner: Runner) -> dict[str, object]:
    result = runner.run(
        [
            "/usr/bin/log",
            "show",
            "--last",
            "10m",
            "--style",
            "compact",
            "--predicate",
            'process == "trustd" OR process == "securityd"',
        ]
    )
    interesting = [
        line
        for line in result.combined.splitlines()
        if "error" in line.lower() or "fault" in line.lower()
    ][:50]
    return {
        "status": "READABLE" if result.returncode == 0 else "UNAVAILABLE",
        "findings": [_redact(line) for line in interesting],
        "returncode": result.returncode,
    }


def system_context(runner: Runner, now: datetime) -> dict[str, object]:
    commands = {
        "swVers": ["sw_vers"],
        "uname": ["uname", "-a"],
        "architecture": ["uname", "-m"],
    }
    return {
        **{name: _summary(runner.run(command)) for name, command in commands.items()},
        "currentTime": now.isoformat(),
        "utcOffset": now.strftime("%z"),
        "clockPlausible": 2020 <= now.year <= 2100,
    }


def classify_diagnosis(evidence: dict[str, object]) -> dict[str, object]:
    apps = [item for item in evidence.get("apps", []) if item.get("present")]
    system_apps = [item for item in apps if item.get("kind") == "system"]
    official = next((item for item in apps if item.get("kind") == "official-chatgpt"), None)
    trust_settings = evidence.get("trustSettings", {})
    explicit_deny = any(
        isinstance(item, dict) and item.get("explicitDeny")
        for item in trust_settings.values()
    )
    roots = evidence.get("roots", {})
    root_present = any(
        isinstance(value, dict) and value.get("present")
        for name, value in roots.items()
        if name.startswith("Apple Root CA")
    )
    intermediate_present = any(
        isinstance(value, dict) and value.get("present")
        for name, value in roots.items()
        if "Developer ID" in name or "Worldwide" in name
    )
    certificates = [cert for app in apps for cert in app.get("certificates", [])]
    invalid_dates = [
        cert for cert in certificates if cert.get("dateValidity") in {"EXPIRED", "NOT_YET_VALID"}
    ]
    structural_failures = [
        app
        for app in apps
        if app.get("verifyVerbose6", {}).get("structural")
        == "STRUCTURAL_SIGNATURE_FAILED"
    ]
    system_trust_failed = bool(system_apps) and all(
        app.get("verifyVerbose6", {}).get("trust") == "TRUST_EVALUATION_FAILED"
        for app in system_apps
    )
    official_trust_failed = bool(official) and official.get("verifyVerbose6", {}).get("trust") == "TRUST_EVALUATION_FAILED"
    if not evidence.get("system", {}).get("clockPlausible", False) or invalid_dates:
        classification = "CLOCK_OR_CERT_VALIDITY_FAILURE"
    elif explicit_deny:
        classification = "TRUST_OVERRIDE_FAILURE"
    elif not root_present or not intermediate_present:
        classification = "ROOT_CHAIN_FAILURE"
    elif structural_failures:
        only_chatgpt = all(app.get("kind") in {"official-chatgpt", "installed-chatgpt"} for app in structural_failures)
        classification = "CHATGPT_SIGNATURE_SPECIFIC_FAILURE" if only_chatgpt else "UNKNOWN_TRUST_FAILURE"
    elif system_trust_failed and official_trust_failed:
        classification = "SYSTEM_WIDE_TRUST_EVALUATION_BROKEN"
    elif official_trust_failed:
        classification = "CHATGPT_SIGNATURE_SPECIFIC_FAILURE"
    elif apps and all(app.get("verifyVerbose6", {}).get("trust") == "TRUST_EVALUATION_PASS" for app in apps):
        classification = "TRUST_ENVIRONMENT_HEALTHY"
    else:
        classification = "UNKNOWN_TRUST_FAILURE"
    degraded = classification == "SYSTEM_WIDE_TRUST_EVALUATION_BROKEN"
    return {
        "classification": classification,
        "strictTrustGateUsable": classification == "TRUST_ENVIRONMENT_HEALTHY",
        "degradedGateSafeToConsider": degraded,
        "phase8Decision": (
            "SYSTEM_TRUST_GATE_UNUSABLE"
            if degraded
            else "TRUST_FAILURE_MUST_BE_FIXED_FIRST"
            if classification != "TRUST_ENVIRONMENT_HEALTHY"
            else "STRICT_TRUST_GATE_USABLE"
        ),
    }


def diagnose(
    *,
    official_app: Path,
    runner: Runner | None = None,
    now: datetime | None = None,
) -> dict[str, object]:
    command_runner = runner or SubprocessRunner()
    current = now or datetime.now().astimezone()
    targets = [
        ("Calculator", SYSTEM_TARGETS[0], "system"),
        ("TextEdit", SYSTEM_TARGETS[1], "system"),
        ("Installed ChatGPT", INSTALLED_CHATGPT, "installed-chatgpt"),
        ("Official clean ChatGPT", official_app, "official-chatgpt"),
    ]
    apps: list[dict[str, object]] = []
    for name, path, kind in targets:
        inspected = inspect_app(name, path, runner=command_runner, now=current)
        inspected["kind"] = kind
        apps.append(inspected)
    evidence: dict[str, object] = {
        "system": system_context(command_runner, current),
        "apps": apps,
        "keychains": _summary(command_runner.run(["security", "list-keychains"])),
        "trustSettings": inspect_trust_settings(command_runner),
        "roots": inspect_roots(command_runner),
        "services": inspect_services(command_runner),
        "logs": inspect_logs(command_runner),
    }
    evidence["decision"] = classify_diagnosis(evidence)
    return evidence


def render_markdown(evidence: dict[str, object]) -> str:
    decision = evidence["decision"]
    lines = [
        "# macOS Code Signing Trust Diagnosis",
        "",
        "> Read-only Phase 8A evidence. No trust setting, keychain, App bundle,",
        "> Gatekeeper policy, or security service was modified.",
        "",
        "## Decision",
        "",
        f"- Classification: `{decision['classification']}`",
        f"- Phase 8 decision: `{decision['phase8Decision']}`",
        f"- Strict trust gate usable: `{str(decision['strictTrustGateUsable']).lower()}`",
        f"- Degraded gate safe to consider: `{str(decision['degradedGateSafeToConsider']).lower()}`",
        "",
        "## System context",
        "",
        f"- Current time: `{evidence['system']['currentTime']}`",
        f"- UTC offset: `{evidence['system']['utcOffset']}`",
        f"- Clock plausible: `{str(evidence['system']['clockPlausible']).lower()}`",
        f"- sw_vers: `{evidence['system']['swVers']['output'].replace(chr(10), '; ')}`",
        f"- Architecture: `{evidence['system']['architecture']['output'].strip()}`",
        "",
        "## App evidence",
        "",
        "| Target | Structural | Trust | Requirement | Gatekeeper | ASAR |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for app in evidence["apps"]:
        if not app.get("present"):
            lines.append(f"| {app['name']} | ABSENT | NOT_TESTED | NOT_TESTED | NOT_TESTED | N/A |")
            continue
        verify = app["verifyVerbose6"]
        requirement = "PASS" if app["designatedRequirement"]["parseable"] else "FAIL"
        asar = app.get("asarIntegrity", {}).get("status", "N/A")
        lines.append(
            f"| {app['name']} | {verify['structural']} | {verify['trust']} | {requirement} | {app['gatekeeper']['status']} | {asar} |"
        )
    lines.extend(("", "## Detailed evidence", "", "```json", json.dumps(evidence, indent=2, sort_keys=True), "```", ""))
    return "\n".join(lines)


@contextlib.contextmanager
def official_app_from_dmg() -> Iterator[Path]:
    """Download, checksum, verify, and read-only mount the frozen official DMG."""

    root = Path(tempfile.mkdtemp(prefix="liang-phase8a-official-"))
    dmg = root / "ChatGPT.dmg"
    mount = root / "mount"
    mount.mkdir()
    device: str | None = None
    try:
        with urllib.request.urlopen(OFFICIAL_DMG_URL) as response, dmg.open("wb") as output:
            shutil.copyfileobj(response, output)
        if dmg.stat().st_size != OFFICIAL_DMG_SIZE or sha256_file(dmg) != OFFICIAL_DMG_SHA256:
            raise RuntimeError("OFFICIAL_DMG_FINGERPRINT_MISMATCH")
        verified = subprocess.run(["hdiutil", "verify", str(dmg)], capture_output=True, text=True)
        if verified.returncode != 0:
            raise RuntimeError("OFFICIAL_DMG_VERIFY_FAILED")
        attached = subprocess.run(
            ["hdiutil", "attach", "-readonly", "-nobrowse", "-noautoopen", "-mountpoint", str(mount), str(dmg)],
            capture_output=True,
            text=True,
        )
        if attached.returncode != 0:
            raise RuntimeError("OFFICIAL_DMG_ATTACH_FAILED")
        match = re.search(r"^(/dev/disk\S+)", attached.stdout, re.MULTILINE)
        device = match.group(1) if match else None
        app = mount / "ChatGPT.app"
        if not app.is_dir():
            raise RuntimeError("OFFICIAL_APP_MISSING")
        yield app
    finally:
        if device:
            subprocess.run(["hdiutil", "detach", device], capture_output=True)
        shutil.rmtree(root, ignore_errors=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--official-app", type=Path)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()
    manager = contextlib.nullcontext(args.official_app) if args.official_app else official_app_from_dmg()
    with manager as official_app:
        evidence = diagnose(official_app=Path(official_app))
    args.report.write_text(render_markdown(evidence))
    if args.json_out:
        args.json_out.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n")
    print(json.dumps(evidence["decision"], sort_keys=True))
    return 0 if evidence["decision"]["classification"] == "TRUST_ENVIRONMENT_HEALTHY" else 2


if __name__ == "__main__":
    raise SystemExit(main())
