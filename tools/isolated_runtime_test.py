#!/usr/bin/env python3
"""Safety-gated harness for a fully isolated Codex runtime test copy.

The harness deliberately separates source verification from mutation.  It will
not create or launch a temporary App unless the installed source matches the
frozen trusted baseline *and* its Apple signature passes deep/strict
verification.  Unit tests use a fake bundle and a fake command runner.
"""

from __future__ import annotations

import argparse
import getpass
import hashlib
import json
import os
import plistlib
import shutil
import struct
import subprocess
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable, Mapping, Protocol, Sequence


ROOT = Path(__file__).resolve().parents[1]
REAL_APP = Path("/Applications/ChatGPT.app")
REAL_CODEX_HOME = Path.home() / ".codex"
TRUST_CONTROL_APP = Path("/System/Applications/Calculator.app")
DEFAULT_BASELINE = ROOT / "runtime-patch/builds/9922/trusted-baseline.json"
EXPECTED_BUNDLE_ID = "com.openai.codex"
PHASE_PREFIX = "liang-no-henshin-phase8-"
SOCKET_NAMESPACE = "liang-no-henshin"
VM_APP_CANDIDATES = (
    Path("/Applications/UTM.app"),
    Path("/Applications/Parallels Desktop.app"),
    Path("/Applications/VMware Fusion.app"),
    Path("/Applications/VirtualBox.app"),
)
VM_COMMAND_CANDIDATES = ("prlctl", "vmrun", "VBoxManage", "qemu-system-aarch64", "virsh")


class IsolationError(RuntimeError):
    """A stable fail-closed error raised by the Phase 8 harness."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class CommandResult:
    argv: tuple[str, ...]
    returncode: int
    stdout: bytes = b""
    stderr: bytes = b""


class Runner(Protocol):
    def run(self, argv: Sequence[str]) -> CommandResult: ...


class SubprocessRunner:
    def run(self, argv: Sequence[str]) -> CommandResult:
        values = tuple(str(value) for value in argv)
        try:
            completed = subprocess.run(values, capture_output=True, check=False)
        except FileNotFoundError as error:
            return CommandResult(values, 127, b"", str(error).encode())
        return CommandResult(
            values, completed.returncode, completed.stdout, completed.stderr
        )


@dataclass(frozen=True)
class AppFingerprint:
    version: str
    build: str
    bundle_identifier: str
    app_asar_sha256: str
    executable_sha256: str
    asar_header_sha256: str
    integrity_algorithm: str | None
    integrity_expected: str | None


@dataclass(frozen=True)
class SourcePreflight:
    status: str
    fingerprint: AppFingerprint
    fingerprint_matches: bool
    integrity_matches: bool
    codesign_deep_strict: bool
    team_identifier_matches: bool
    entitlements_valid: bool
    gatekeeper_accepted: bool


@dataclass(frozen=True)
class IsolationLayout:
    root: Path
    app: Path
    home: Path
    codex_home: Path
    user_data: Path
    runtime: Path
    temp: Path
    logs: Path

    @property
    def executable(self) -> Path:
        return self.app / "Contents/MacOS/ChatGPT"

    @property
    def socket_path(self) -> Path:
        return (
            self.temp
            / f"{SOCKET_NAMESPACE}-{os.getuid()}"
            / "runtime.sock"
        )


@dataclass(frozen=True)
class HostIsolationCandidates:
    vm_apps_present: tuple[str, ...]
    vm_commands_present: tuple[str, ...]
    other_console_session_count: int
    independent_vm_proven: bool
    authorized_gui_test_session_proven: bool


def inspect_host_isolation_candidates(
    *,
    runner: Runner | None = None,
    current_user: str | None = None,
    vm_apps: Sequence[Path] = VM_APP_CANDIDATES,
    which: Callable[[str], str | None] = shutil.which,
) -> HostIsolationCandidates:
    """Read-only candidate discovery, never an authorization or launch proof."""

    command_runner = runner or SubprocessRunner()
    login = current_user or getpass.getuser()
    sessions = command_runner.run(["who"])
    console_users = set()
    if sessions.returncode == 0:
        for line in sessions.stdout.decode("utf-8", "replace").splitlines():
            fields = line.split()
            if len(fields) >= 2 and fields[1] == "console" and fields[0] != login:
                console_users.add(fields[0])
    return HostIsolationCandidates(
        vm_apps_present=tuple(str(path) for path in vm_apps if path.is_dir()),
        vm_commands_present=tuple(
            name for name in VM_COMMAND_CANDIDATES if which(name) is not None
        ),
        other_console_session_count=len(console_users),
        # An installed hypervisor or another login name is not proof of a
        # running isolated VM, permission, separate Keychain or GUI session.
        independent_vm_proven=False,
        authorized_gui_test_session_proven=False,
    )


def audit_real_app_isolation(
    source: SourcePreflight,
    *,
    candidates: HostIsolationCandidates | None = None,
) -> dict[str, object]:
    """Fail closed before any patched Codex launch under the current account."""

    observed = candidates or inspect_host_isolation_candidates()
    failures = []
    if source.status != "PASS":
        failures.append("trusted-source-preflight")
    if not observed.independent_vm_proven and not observed.authorized_gui_test_session_proven:
        failures.append("independent-authorized-gui-environment")
    failures.extend((
        "production-keychain-separation",
        "single-instance-non-redirection",
        "temporary-patched-app-signature-and-integrity",
    ))
    return {
        "status": "REAL_APP_ISOLATION_BLOCKED",
        "sourceTrusted": source.status == "PASS",
        "candidateDiscovery": asdict(observed),
        "unverifiedRequirements": failures,
        "productionKeychainAccessExcluded": False,
        "productionUserDataAccessExcluded": False,
        "singleInstanceRedirectExcluded": False,
        "launchAllowed": False,
    }


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def asar_raw_json_header_hash(archive: Path) -> str:
    """Return ElectronAsarIntegrity's raw JSON header digest."""

    try:
        with archive.open("rb") as handle:
            prefix = handle.read(8)
            if len(prefix) != 8:
                raise ValueError("truncated ASAR prefix")
            pickle_size, header_size = struct.unpack("<II", prefix)
            if pickle_size != 4 or not 12 <= header_size <= 64 * 1024 * 1024:
                raise ValueError("invalid ASAR header size")
            header = handle.read(header_size)
            if len(header) != header_size:
                raise ValueError("truncated ASAR header")
            payload_size, json_size = struct.unpack("<II", header[:8])
            if payload_size != header_size - 4 or json_size > header_size - 8:
                raise ValueError("invalid ASAR pickle header")
    except (OSError, struct.error, ValueError) as error:
        raise IsolationError("INVALID_ASAR", "unable to parse ASAR header") from error
    return hashlib.sha256(header[8 : 8 + json_size]).hexdigest()


def _read_plist(app: Path) -> dict[str, object]:
    plist = app / "Contents/Info.plist"
    try:
        with plist.open("rb") as handle:
            value = plistlib.load(handle)
    except (OSError, plistlib.InvalidFileException) as error:
        raise IsolationError("INVALID_APP", "Info.plist is unavailable") from error
    if not isinstance(value, dict):
        raise IsolationError("INVALID_APP", "Info.plist is not a dictionary")
    return value


def fingerprint(app: Path) -> AppFingerprint:
    app = Path(app)
    if app.is_symlink() or not app.is_dir():
        raise IsolationError("INVALID_APP", "App must be a real bundle directory")
    info = _read_plist(app)
    archive = app / "Contents/Resources/app.asar"
    executable_name = info.get("CFBundleExecutable", "ChatGPT")
    executable = app / "Contents/MacOS" / str(executable_name)
    if any(path.is_symlink() or not path.is_file() for path in (archive, executable)):
        raise IsolationError("INVALID_APP", "App executable or app.asar is missing")
    metadata = info.get("ElectronAsarIntegrity")
    record = (
        metadata.get("Resources/app.asar") if isinstance(metadata, dict) else None
    )
    return AppFingerprint(
        version=str(info.get("CFBundleShortVersionString", "")),
        build=str(info.get("CFBundleVersion", "")),
        bundle_identifier=str(info.get("CFBundleIdentifier", "")),
        app_asar_sha256=sha256_file(archive),
        executable_sha256=sha256_file(executable),
        asar_header_sha256=asar_raw_json_header_hash(archive),
        integrity_algorithm=(
            str(record.get("algorithm")) if isinstance(record, dict) else None
        ),
        integrity_expected=(
            str(record.get("hash")) if isinstance(record, dict) else None
        ),
    )


def _load_baseline(path: Path) -> dict[str, object]:
    try:
        value = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as error:
        raise IsolationError(
            "INVALID_BASELINE", "trusted baseline is unavailable"
        ) from error
    if value.get("classification") != "TRUSTED_BASELINE":
        raise IsolationError("INVALID_BASELINE", "baseline is not trusted")
    return value


def verify_source(
    app: Path = REAL_APP,
    *,
    baseline_path: Path = DEFAULT_BASELINE,
    runner: Runner | None = None,
) -> SourcePreflight:
    """Verify the immutable source before any temporary copy is created."""

    observed = fingerprint(app)
    baseline = _load_baseline(baseline_path)
    identity = baseline.get("identity", {})
    archive = baseline.get("appAsar", {})
    executable = baseline.get("executable", {})
    integrity = archive.get("electronIntegrity", {}) if isinstance(archive, dict) else {}
    fingerprint_matches = all(
        (
            observed.version == str(baseline.get("version", "")),
            observed.build == str(baseline.get("build", "")),
            observed.bundle_identifier
            == str(identity.get("bundleIdentifier", EXPECTED_BUNDLE_ID)),
            observed.app_asar_sha256 == str(archive.get("sha256", "")),
            observed.executable_sha256 == str(executable.get("sha256", "")),
        )
    )
    integrity_matches = all(
        (
            observed.integrity_algorithm == "SHA256",
            observed.integrity_expected == observed.asar_header_sha256,
            observed.asar_header_sha256 == str(integrity.get("actual", "")),
        )
    )
    command_runner = runner or SubprocessRunner()
    signature = command_runner.run(
        [
            "codesign",
            "--verify",
            "--deep",
            "--strict",
            "--verbose=4",
            str(app),
        ]
    )
    codesign_ok = signature.returncode == 0
    if not codesign_ok:
        # Phase 8A proved that a restricted execution context can falsely
        # reject even unchanged Apple-signed system Apps. Never downgrade this
        # gate or treat a hash match as a substitute for SecTrust.
        control = command_runner.run(
            ["codesign", "--verify", "--deep", "--strict", "--verbose=4", str(TRUST_CONTROL_APP)]
        )
        if control.returncode != 0:
            raise IsolationError(
                "TRUST_CONTEXT_UNAVAILABLE",
                "strict signature evaluation also failed for the system trust control",
            )
    details = command_runner.run(["codesign", "-dv", "--verbose=4", str(app)])
    detail_text = (details.stdout + details.stderr).decode("utf-8", "replace")
    expected_team = str(identity.get("teamIdentifier", ""))
    team_matches = (
        details.returncode == 0
        and bool(expected_team)
        and f"TeamIdentifier={expected_team}" in detail_text.splitlines()
        and f"Identifier={observed.bundle_identifier}" in detail_text.splitlines()
        and "flags=0x10000(runtime)" in detail_text
    )
    entitlement_result = command_runner.run(
        ["codesign", "-d", "--entitlements", "-", "--xml", str(app)]
    )
    entitlements_valid = False
    if entitlement_result.returncode == 0:
        try:
            entitlements = plistlib.loads(entitlement_result.stdout)
        except (ValueError, plistlib.InvalidFileException):
            entitlements = None
        entitlements_valid = (
            isinstance(entitlements, dict)
            and len(entitlements) == 14
            and entitlements.get("com.apple.application-identifier")
            == f"{expected_team}.{observed.bundle_identifier}"
            and entitlements.get("com.apple.developer.team-identifier") == expected_team
            and entitlements.get("keychain-access-groups")
            == [f"{expected_team}.*", f"{expected_team}.com.openai.shared"]
        )
    gatekeeper = command_runner.run(
        ["spctl", "--assess", "--type", "execute", "--verbose=4", str(app)]
    )
    gatekeeper_text = (gatekeeper.stdout + gatekeeper.stderr).decode("utf-8", "replace")
    gatekeeper_accepted = (
        gatekeeper.returncode == 0
        and "accepted" in gatekeeper_text
        and "source=Notarized Developer ID" in gatekeeper_text
    )
    if not fingerprint_matches:
        status = "UNSUPPORTED_BUILD"
    elif not integrity_matches:
        status = "ASAR_INTEGRITY_MISMATCH"
    elif not codesign_ok:
        status = "SOURCE_SIGNATURE_INVALID"
    elif not team_matches:
        status = "SOURCE_IDENTITY_INVALID"
    elif not entitlements_valid:
        status = "SOURCE_ENTITLEMENTS_INVALID"
    elif not gatekeeper_accepted:
        status = "SOURCE_GATEKEEPER_REJECTED"
    else:
        status = "PASS"
    return SourcePreflight(
        status=status,
        fingerprint=observed,
        fingerprint_matches=fingerprint_matches,
        integrity_matches=integrity_matches,
        codesign_deep_strict=codesign_ok,
        team_identifier_matches=team_matches,
        entitlements_valid=entitlements_valid,
        gatekeeper_accepted=gatekeeper_accepted,
    )


def create_layout(temp_parent: Path | None = None) -> IsolationLayout:
    root = Path(
        tempfile.mkdtemp(prefix=PHASE_PREFIX, dir=temp_parent)
    ).resolve()
    layout = IsolationLayout(
        root=root,
        app=root / "ChatGPT.app",
        home=root / "home",
        codex_home=root / "codex-home",
        user_data=root / "user-data",
        runtime=root / "runtime",
        temp=root / "runtime/tmp",
        logs=root / "logs",
    )
    for directory in (
        layout.home,
        layout.codex_home,
        layout.user_data,
        layout.runtime,
        layout.temp,
        layout.logs,
    ):
        directory.mkdir(parents=True, exist_ok=False)
    return layout


def isolated_environment(layout: IsolationLayout) -> dict[str, str]:
    """Build a minimal environment without inherited credentials or tokens."""

    environment = {
        "HOME": str(layout.home),
        "CODEX_HOME": str(layout.codex_home),
        # Build 9922 bootstrap sets Electron userData from this environment
        # variable; --user-data-dir alone does not control that code path.
        "CODEX_ELECTRON_USER_DATA_PATH": str(layout.user_data),
        "TMPDIR": f"{layout.temp}{os.sep}",
        "XDG_CONFIG_HOME": str(layout.home / ".config"),
        "XDG_CACHE_HOME": str(layout.home / ".cache"),
        "XDG_DATA_HOME": str(layout.home / ".local/share"),
        "PATH": os.environ.get("PATH", "/usr/bin:/bin:/usr/sbin:/sbin"),
        "LANG": os.environ.get("LANG", "en_US.UTF-8"),
        "ELECTRON_ENABLE_LOGGING": "1",
    }
    return environment


def launch_command(layout: IsolationLayout) -> list[str]:
    return [
        str(layout.executable),
        f"--user-data-dir={layout.user_data}",
        "--no-first-run",
    ]


def _is_within(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
    except (OSError, ValueError):
        return False
    return True


def verify_path_isolation(
    layout: IsolationLayout,
    environment: Mapping[str, str],
    command: Sequence[str],
    *,
    production_app: Path = REAL_APP,
    production_codex_home: Path = REAL_CODEX_HOME,
) -> dict[str, object]:
    """Prove filesystem/socket isolation; identity isolation is a later gate."""

    resolved_values = {
        "app": layout.app,
        "home": Path(environment.get("HOME", "")),
        "codexHome": Path(environment.get("CODEX_HOME", "")),
        "tmpDir": Path(environment.get("TMPDIR", "")),
        "userData": layout.user_data,
        "socket": layout.socket_path,
    }
    within_root = {
        name: _is_within(path, layout.root) for name, path in resolved_values.items()
    }
    command_has_user_data = (
        f"--user-data-dir={layout.user_data}" in command
    )
    bootstrap_has_user_data = (
        environment.get("CODEX_ELECTRON_USER_DATA_PATH") == str(layout.user_data)
    )
    no_production_alias = all(
        (
            layout.app.resolve() != production_app.resolve(),
            layout.codex_home.resolve() != production_codex_home.resolve(),
            not _is_within(layout.socket_path, Path(tempfile.gettempdir()) / f"{SOCKET_NAMESPACE}-{os.getuid()}"),
        )
    )
    passed = (
        all(within_root.values())
        and command_has_user_data
        and bootstrap_has_user_data
        and no_production_alias
    )
    return {
        "status": "PASS" if passed else "ISOLATION_NOT_VERIFIED",
        "withinPhaseRoot": within_root,
        "explicitUserData": command_has_user_data,
        "bootstrapUserDataOverride": bootstrap_has_user_data,
        "noProductionAlias": no_production_alias,
        "bridgeSocket": str(layout.socket_path),
        # Ad-hoc signing and a separate single-instance audit are required
        # before this can become true.  Path checks alone are insufficient.
        "identityAndKeychainIsolationProven": False,
        "keychainRisk": (
            "The source App carries production keychain-access-groups; "
            "ad-hoc re-signing and temporary filesystem paths alone do not "
            "prove that production Keychain items cannot be accessed."
        ),
        "launchAllowed": False,
    }


def copy_verified_app(
    source: Path,
    layout: IsolationLayout,
    *,
    baseline_path: Path = DEFAULT_BASELINE,
    runner: Runner | None = None,
) -> SourcePreflight:
    command_runner = runner or SubprocessRunner()
    source_result = verify_source(
        source, baseline_path=baseline_path, runner=command_runner
    )
    if source_result.status != "PASS":
        raise IsolationError(source_result.status, "source App preflight failed")
    copied = command_runner.run(
        ["ditto", "--rsrc", "--extattr", "--acl", str(source), str(layout.app)]
    )
    if copied.returncode != 0:
        raise IsolationError("COPY_FAILED", "ditto failed to copy source App")
    target_result = verify_source(
        layout.app, baseline_path=baseline_path, runner=command_runner
    )
    if target_result.status != "PASS":
        raise IsolationError("TEMP_COPY_INVALID", "temporary App verification failed")
    return target_result


def cleanup(layout: IsolationLayout) -> None:
    if not layout.root.name.startswith(PHASE_PREFIX):
        raise IsolationError("UNSAFE_CLEANUP", "refusing to remove non-Phase-8 root")
    shutil.rmtree(layout.root)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-app", type=Path, default=REAL_APP)
    parser.add_argument("--baseline", type=Path, default=DEFAULT_BASELINE)
    parser.add_argument("--prepare", action="store_true")
    parser.add_argument("--audit-real-app", action="store_true")
    parser.add_argument("--temp-parent", type=Path)
    parser.add_argument("--keep", action="store_true")
    args = parser.parse_args()

    try:
        preflight = verify_source(args.source_app, baseline_path=args.baseline)
    except IsolationError as error:
        print(json.dumps({"status": error.code, "message": str(error)}, indent=2))
        return 2
    report: dict[str, object] = {"sourcePreflight": asdict(preflight)}
    if preflight.status != "PASS":
        print(json.dumps(report, indent=2, default=str, sort_keys=True))
        return 2
    if args.audit_real_app:
        report["realAppGate"] = audit_real_app_isolation(preflight)
        print(json.dumps(report, indent=2, default=str, sort_keys=True))
        return 2
    if not args.prepare:
        print(json.dumps(report, indent=2, default=str, sort_keys=True))
        return 0

    layout = create_layout(args.temp_parent)
    try:
        copy_verified_app(
            args.source_app,
            layout,
            baseline_path=args.baseline,
        )
        environment = isolated_environment(layout)
        isolation = verify_path_isolation(
            layout, environment, launch_command(layout)
        )
        report.update(
            {
                "layout": {key: str(value) for key, value in asdict(layout).items()},
                "pathIsolation": isolation,
            }
        )
        print(json.dumps(report, indent=2, default=str, sort_keys=True))
        return 0
    finally:
        if not args.keep:
            cleanup(layout)


if __name__ == "__main__":
    raise SystemExit(main())
