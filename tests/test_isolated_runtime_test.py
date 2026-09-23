from __future__ import annotations

import hashlib
import json
import os
import plistlib
import struct
import sys
from pathlib import Path

import pytest

from tools import isolated_runtime_test as harness


class FakeRunner:
    def __init__(
        self,
        *,
        codesign_ok: bool = True,
        trust_context_ok: bool = True,
        team_ok: bool = True,
        entitlements_ok: bool = True,
        gatekeeper_ok: bool = True,
    ) -> None:
        self.codesign_ok = codesign_ok
        self.trust_context_ok = trust_context_ok
        self.team_ok = team_ok
        self.entitlements_ok = entitlements_ok
        self.gatekeeper_ok = gatekeeper_ok
        self.commands: list[tuple[str, ...]] = []

    def run(self, argv):
        command = tuple(str(value) for value in argv)
        self.commands.append(command)
        if command[0] == "codesign" and "--verify" in command:
            allowed = self.trust_context_ok if command[-1] == str(harness.TRUST_CONTROL_APP) else self.codesign_ok
            return harness.CommandResult(
                command, 0 if allowed else 1, b"", b"" if allowed else b"invalid signature"
            )
        if command[:3] == ("codesign", "-dv", "--verbose=4"):
            team = "2DC432GLL2" if self.team_ok else "WRONGTEAM"
            return harness.CommandResult(
                command,
                0,
                b"",
                (
                    f"Identifier=com.openai.codex\nTeamIdentifier={team}\n"
                    "CodeDirectory flags=0x10000(runtime)\n"
                ).encode(),
            )
        if command[:3] == ("codesign", "-d", "--entitlements"):
            entitlements = {
                "com.apple.application-identifier": "2DC432GLL2.com.openai.codex",
                "com.apple.developer.team-identifier": "2DC432GLL2",
                "keychain-access-groups": ["2DC432GLL2.*", "2DC432GLL2.com.openai.shared"],
            }
            entitlements.update({f"fixture.key.{index}": True for index in range(11)})
            if not self.entitlements_ok:
                entitlements["keychain-access-groups"] = ["unexpected"]
            return harness.CommandResult(command, 0, plistlib.dumps(entitlements), b"")
        if command[0] == "spctl":
            return harness.CommandResult(
                command,
                0 if self.gatekeeper_ok else 1,
                b"",
                b"accepted\nsource=Notarized Developer ID\n" if self.gatekeeper_ok else b"rejected",
            )
        if command[0] == "ditto":
            raise AssertionError("fake preflight tests must not copy an App")
        return harness.CommandResult(command, 0)


def make_asar(payload: bytes = b"fixture") -> tuple[bytes, str]:
    encoded = json.dumps({"files": {}}, separators=(",", ":")).encode()
    aligned = (4 + len(encoded) + 1 + 3) & ~3
    header_size = 4 + aligned
    padding = aligned - (4 + len(encoded) + 1)
    archive = (
        struct.pack("<II", 4, header_size)
        + struct.pack("<II", aligned, len(encoded))
        + encoded
        + b"\0"
        + (b"\0" * padding)
        + payload
    )
    return archive, hashlib.sha256(encoded).hexdigest()


def make_fixture(tmp_path: Path) -> tuple[Path, Path]:
    app = tmp_path / "Source.app"
    resources = app / "Contents/Resources"
    executable_dir = app / "Contents/MacOS"
    resources.mkdir(parents=True)
    executable_dir.mkdir()
    archive, header_hash = make_asar()
    executable = b"fixture executable"
    (resources / "app.asar").write_bytes(archive)
    (executable_dir / "ChatGPT").write_bytes(executable)
    with (app / "Contents/Info.plist").open("wb") as handle:
        plistlib.dump(
            {
                "CFBundleShortVersionString": "26.915.31945",
                "CFBundleVersion": "9922",
                "CFBundleIdentifier": "com.openai.codex",
                "CFBundleExecutable": "ChatGPT",
                "ElectronAsarIntegrity": {
                    "Resources/app.asar": {
                        "algorithm": "SHA256",
                        "hash": header_hash,
                    }
                },
            },
            handle,
        )
    baseline = tmp_path / "trusted-baseline.json"
    baseline.write_text(
        json.dumps(
            {
                "formatVersion": 1,
                "classification": "TRUSTED_BASELINE",
                "version": "26.915.31945",
                "build": "9922",
                "identity": {
                    "bundleIdentifier": "com.openai.codex",
                    "teamIdentifier": "2DC432GLL2",
                },
                "appAsar": {
                    "sha256": hashlib.sha256(archive).hexdigest(),
                    "electronIntegrity": {"actual": header_hash},
                },
                "executable": {"sha256": hashlib.sha256(executable).hexdigest()},
            }
        )
        + "\n"
    )
    return app, baseline


def test_matching_source_passes_all_read_only_gates(tmp_path: Path) -> None:
    app, baseline = make_fixture(tmp_path)
    runner = FakeRunner()
    result = harness.verify_source(app, baseline_path=baseline, runner=runner)
    assert result.status == "PASS"
    assert result.fingerprint_matches is True
    assert result.integrity_matches is True
    assert result.codesign_deep_strict is True
    assert result.team_identifier_matches is True
    assert result.entitlements_valid is True
    assert result.gatekeeper_accepted is True
    assert runner.commands[0] == (
        "codesign", "--verify", "--deep", "--strict", "--verbose=4", str(app)
    )
    assert len(runner.commands) == 4


def test_fingerprint_mismatch_is_unsupported(tmp_path: Path) -> None:
    app, baseline = make_fixture(tmp_path)
    (app / "Contents/Resources/app.asar").write_bytes(make_asar(b"changed")[0])
    result = harness.verify_source(app, baseline_path=baseline, runner=FakeRunner())
    assert result.status == "UNSUPPORTED_BUILD"
    assert result.fingerprint_matches is False


def test_integrity_metadata_mismatch_blocks(tmp_path: Path) -> None:
    app, baseline = make_fixture(tmp_path)
    plist = app / "Contents/Info.plist"
    with plist.open("rb") as handle:
        value = plistlib.load(handle)
    value["ElectronAsarIntegrity"]["Resources/app.asar"]["hash"] = "0" * 64
    with plist.open("wb") as handle:
        plistlib.dump(value, handle)
    result = harness.verify_source(app, baseline_path=baseline, runner=FakeRunner())
    assert result.status == "ASAR_INTEGRITY_MISMATCH"


def test_signature_failure_blocks_even_when_hashes_match(tmp_path: Path) -> None:
    app, baseline = make_fixture(tmp_path)
    result = harness.verify_source(
        app, baseline_path=baseline, runner=FakeRunner(codesign_ok=False)
    )
    assert result.status == "SOURCE_SIGNATURE_INVALID"
    assert result.fingerprint_matches is True
    assert result.integrity_matches is True


def test_restricted_sectrust_context_blocks_without_downgrade(tmp_path: Path) -> None:
    app, baseline = make_fixture(tmp_path)
    runner = FakeRunner(codesign_ok=False, trust_context_ok=False)
    with pytest.raises(harness.IsolationError) as error:
        harness.verify_source(app, baseline_path=baseline, runner=runner)
    assert error.value.code == "TRUST_CONTEXT_UNAVAILABLE"
    assert runner.commands[1][-1] == str(harness.TRUST_CONTROL_APP)


def test_cli_reports_unavailable_trust_context_without_traceback(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def unavailable(*args: object, **kwargs: object) -> None:
        raise harness.IsolationError("TRUST_CONTEXT_UNAVAILABLE", "restricted context")

    monkeypatch.setattr(harness, "verify_source", unavailable)
    monkeypatch.setattr(sys, "argv", ["isolated_runtime_test.py"])
    assert harness.main() == 2
    assert json.loads(capsys.readouterr().out)["status"] == "TRUST_CONTEXT_UNAVAILABLE"


@pytest.mark.parametrize(
    ("runner", "status"),
    [
        (FakeRunner(team_ok=False), "SOURCE_IDENTITY_INVALID"),
        (FakeRunner(entitlements_ok=False), "SOURCE_ENTITLEMENTS_INVALID"),
        (FakeRunner(gatekeeper_ok=False), "SOURCE_GATEKEEPER_REJECTED"),
    ],
)
def test_source_identity_entitlement_and_gatekeeper_fail_closed(
    tmp_path: Path, runner: FakeRunner, status: str
) -> None:
    app, baseline = make_fixture(tmp_path)
    assert harness.verify_source(app, baseline_path=baseline, runner=runner).status == status


def test_layout_and_environment_are_confined_to_random_phase_root(
    tmp_path: Path,
) -> None:
    layout = harness.create_layout(tmp_path)
    try:
        environment = harness.isolated_environment(layout)
        command = harness.launch_command(layout)
        result = harness.verify_path_isolation(
            layout,
            environment,
            command,
            production_app=tmp_path / "Applications/ChatGPT.app",
            production_codex_home=tmp_path / "production/.codex",
        )
        assert layout.root.name.startswith(harness.PHASE_PREFIX)
        assert result["status"] == "PASS"
        assert all(result["withinPhaseRoot"].values())
        assert result["explicitUserData"] is True
        assert result["bootstrapUserDataOverride"] is True
        assert result["identityAndKeychainIsolationProven"] is False
        assert result["launchAllowed"] is False
        assert environment["HOME"] == str(layout.home)
        assert environment["CODEX_HOME"] == str(layout.codex_home)
        assert environment["CODEX_ELECTRON_USER_DATA_PATH"] == str(layout.user_data)
        assert environment["TMPDIR"] == f"{layout.temp}{os.sep}"
        assert not any("API_KEY" in name for name in environment)
        assert layout.socket_path.is_relative_to(layout.root)
    finally:
        harness.cleanup(layout)
    assert not layout.root.exists()


def test_production_alias_or_missing_user_data_flag_fails_closed(
    tmp_path: Path,
) -> None:
    layout = harness.create_layout(tmp_path)
    try:
        environment = harness.isolated_environment(layout)
        environment["CODEX_HOME"] = str(tmp_path / "production/.codex")
        result = harness.verify_path_isolation(
            layout,
            environment,
            [str(layout.executable)],
            production_app=tmp_path / "Applications/ChatGPT.app",
            production_codex_home=tmp_path / "production/.codex",
        )
        assert result["status"] == "ISOLATION_NOT_VERIFIED"
        assert result["explicitUserData"] is False
        assert result["withinPhaseRoot"]["codexHome"] is False
    finally:
        harness.cleanup(layout)


def test_missing_bootstrap_user_data_override_fails_closed(tmp_path: Path) -> None:
    layout = harness.create_layout(tmp_path)
    try:
        environment = harness.isolated_environment(layout)
        environment.pop("CODEX_ELECTRON_USER_DATA_PATH")
        result = harness.verify_path_isolation(
            layout,
            environment,
            harness.launch_command(layout),
            production_app=tmp_path / "Applications/ChatGPT.app",
            production_codex_home=tmp_path / "production/.codex",
        )
        assert result["status"] == "ISOLATION_NOT_VERIFIED"
        assert result["bootstrapUserDataOverride"] is False
        assert result["launchAllowed"] is False
    finally:
        harness.cleanup(layout)


def test_cleanup_refuses_unrelated_directory(tmp_path: Path) -> None:
    unrelated = tmp_path / "unrelated"
    unrelated.mkdir()
    layout = harness.IsolationLayout(
        unrelated,
        unrelated / "ChatGPT.app",
        unrelated / "home",
        unrelated / "codex-home",
        unrelated / "user-data",
        unrelated / "runtime",
        unrelated / "runtime/tmp",
        unrelated / "logs",
    )
    with pytest.raises(harness.IsolationError, match="non-Phase-8"):
        harness.cleanup(layout)
    assert unrelated.exists()
