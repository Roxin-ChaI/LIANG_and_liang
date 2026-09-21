from __future__ import annotations

import plistlib
import subprocess
from pathlib import Path

from tools import runtime_patch_app_copy_smoke as smoke


class FakeRunner:
    def __init__(self, responses: list[subprocess.CompletedProcess[str]]) -> None:
        self.responses = responses
        self.commands: list[list[str]] = []

    def run(self, command: list[str]) -> subprocess.CompletedProcess[str]:
        self.commands.append(command)
        return self.responses.pop(0)


def completed(code: int = 0, *, stdout: str = "", stderr: str = "") -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess([], code, stdout, stderr)


def valid_entitlements() -> str:
    return '<?xml version="1.0" encoding="UTF-8"?>\n<plist version="1.0"><dict><key>com.apple.security.cs.allow-jit</key><true/></dict></plist>\n'


def make_minimal_app(tmp_path: Path, *, version: str = "new", build: str = "9999") -> Path:
    app = tmp_path / "ChatGPT.app"
    (app / "Contents/Resources").mkdir(parents=True)
    (app / "Contents/MacOS").mkdir()
    (app / "Contents/Resources/app.asar").write_bytes(b"asar")
    (app / "Contents/MacOS/ChatGPT").write_bytes(b"executable")
    with (app / "Contents/Info.plist").open("wb") as handle:
        plistlib.dump({"CFBundleShortVersionString": version, "CFBundleVersion": build, "CFBundleIdentifier": "com.openai.codex"}, handle)
    return app


def test_signing_snapshot_records_identity_runtime_and_entitlements(tmp_path: Path) -> None:
    app = make_minimal_app(tmp_path)
    runner = FakeRunner([
        completed(0),
        completed(stderr="Identifier=com.openai.codex\nTeamIdentifier=TEAM\nflags=0x10000(runtime)\n"),
        completed(stdout=valid_entitlements()),
    ])
    result = smoke.signing_snapshot(app, runner)
    assert result.verification == "PASS"
    assert result.identifier == "com.openai.codex"
    assert result.team_identifier == "TEAM"
    assert result.hardened_runtime is True
    assert "allow-jit" in result.entitlements_xml


def test_invalid_entitlements_make_adhoc_strategy_unsafe(tmp_path: Path) -> None:
    app = make_minimal_app(tmp_path)
    baseline = smoke.SigningSnapshot("FAIL", "com.openai.codex", "TEAM", True, None, "")
    runner = FakeRunner([])
    result = smoke.adhoc_sign(app, baseline, runner, tmp_path)
    assert result["result"] == "ADHOC_SIGNING_UNSAFE"
    assert runner.commands == []


def test_adhoc_sign_preserves_entitlements_and_strictly_verifies(tmp_path: Path) -> None:
    app = make_minimal_app(tmp_path)
    baseline = smoke.SigningSnapshot("PASS", "com.openai.codex", "TEAM", True, valid_entitlements(), "")
    runner = FakeRunner([completed(0), completed(0)])
    result = smoke.adhoc_sign(app, baseline, runner, tmp_path)
    assert result["result"] == "PASS"
    assert runner.commands[0][:5] == ["codesign", "--force", "--deep", "--sign", "-"]
    assert "--entitlements" in runner.commands[0]
    assert runner.commands[1][1:4] == ["--verify", "--deep", "--strict"]


def test_adhoc_sign_failure_is_reported(tmp_path: Path) -> None:
    app = make_minimal_app(tmp_path)
    baseline = smoke.SigningSnapshot("PASS", "com.openai.codex", "TEAM", True, valid_entitlements(), "")
    runner = FakeRunner([completed(1, stderr="rejected")])
    assert smoke.adhoc_sign(app, baseline, runner, tmp_path)["result"] == "ADHOC_SIGNING_FAIL"


def test_build_mismatch_blocks_before_temp_copy(tmp_path: Path) -> None:
    app = make_minimal_app(tmp_path)
    spec = tmp_path / "spec.json"
    spec.write_text('{"target":{"version":"26.908.70816","build":"9275","appAsarSha256":"' + ("0" * 64) + '"}}')
    runner = FakeRunner([completed(1), completed(stderr="Identifier=com.openai.codex\nflags=0x10000(runtime)\n"), completed(stderr="invalid entitlements")])
    report, status = smoke.smoke(app, spec_path=spec, temp_parent=tmp_path / "must-not-exist", runner=runner)
    assert status == 2
    assert report["status"] == "BLOCKED_UNSUPPORTED_BUILD"
    assert report["tempCopyCreated"] is False
    assert report["sourceUnchanged"] is True
    assert not (tmp_path / "must-not-exist").exists()


def test_fingerprint_records_bundle_and_executable(tmp_path: Path) -> None:
    app = make_minimal_app(tmp_path)
    value = smoke.fingerprint(app)
    assert value.bundle_identifier == "com.openai.codex"
    assert len(value.executable_sha256) == 64
    assert len(value.app_asar_sha256) == 64


def test_signing_snapshot_uses_only_read_only_codesign_commands(tmp_path: Path) -> None:
    app = make_minimal_app(tmp_path)
    runner = FakeRunner([completed(), completed(), completed()])
    smoke.signing_snapshot(app, runner)
    assert all("--force" not in command and "--sign" not in command for command in runner.commands)
    assert runner.commands[0][1:4] == ["--verify", "--deep", "--strict"]
