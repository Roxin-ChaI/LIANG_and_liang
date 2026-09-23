from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from tools import isolated_runtime_test as harness


class WhoRunner:
    def __init__(self, text: str) -> None:
        self.text = text
        self.commands: list[tuple[str, ...]] = []

    def run(self, argv):
        command = tuple(argv)
        self.commands.append(command)
        return harness.CommandResult(command, 0, self.text.encode())


def source_with_status(status: str) -> harness.SourcePreflight:
    return harness.SourcePreflight(
        status=status,
        fingerprint=harness.AppFingerprint(
            "26.915.31945", "9922", "com.openai.codex", "a" * 64,
            "b" * 64, "c" * 64, "SHA256", "c" * 64,
        ),
        fingerprint_matches=True,
        integrity_matches=True,
        codesign_deep_strict=status == "PASS",
        team_identifier_matches=True,
        entitlements_valid=True,
        gatekeeper_accepted=True,
    )


def test_no_vm_or_other_gui_session_blocks(tmp_path: Path) -> None:
    runner = WhoRunner("mac console Sep 15 15:38\nmac ttys000 Sep 17 15:54\n")
    candidates = harness.inspect_host_isolation_candidates(
        runner=runner, current_user="mac", vm_apps=(tmp_path / "missing.app",),
        which=lambda name: None,
    )
    assert candidates.other_console_session_count == 0
    assert not candidates.vm_apps_present
    assert candidates.independent_vm_proven is False
    result = harness.audit_real_app_isolation(source_with_status("PASS"), candidates=candidates)
    assert result["status"] == "REAL_APP_ISOLATION_BLOCKED"
    assert result["sourceTrusted"] is True
    assert result["launchAllowed"] is False


def test_installed_vm_and_other_user_are_only_candidates(tmp_path: Path) -> None:
    vm = tmp_path / "Test VM.app"
    vm.mkdir()
    runner = WhoRunner("mac console Sep 15 15:38\ntester console Sep 20 10:00\n")
    candidates = harness.inspect_host_isolation_candidates(
        runner=runner, current_user="mac", vm_apps=(vm,),
        which=lambda name: "/usr/local/bin/vmrun" if name == "vmrun" else None,
    )
    assert candidates.other_console_session_count == 1
    assert candidates.vm_apps_present == (str(vm),)
    assert candidates.vm_commands_present == ("vmrun",)
    assert candidates.authorized_gui_test_session_proven is False
    assert harness.audit_real_app_isolation(source_with_status("PASS"), candidates=candidates)["launchAllowed"] is False


def test_trust_failure_never_opens_real_app_gate() -> None:
    candidates = harness.HostIsolationCandidates((), (), 0, False, False)
    result = harness.audit_real_app_isolation(source_with_status("SOURCE_SIGNATURE_INVALID"), candidates=candidates)
    assert "trusted-source-preflight" in result["unverifiedRequirements"]
    assert result["launchAllowed"] is False


def test_even_asserted_candidate_proof_does_not_replace_keychain_and_instance_checks() -> None:
    candidates = harness.HostIsolationCandidates((), (), 1, True, True)
    result = harness.audit_real_app_isolation(source_with_status("PASS"), candidates=candidates)
    assert "production-keychain-separation" in result["unverifiedRequirements"]
    assert "single-instance-non-redirection" in result["unverifiedRequirements"]
    assert result["launchAllowed"] is False


def test_cli_audit_reports_blocked_without_preparing_app(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(harness, "verify_source", lambda *args, **kwargs: source_with_status("PASS"))
    monkeypatch.setattr(harness, "inspect_host_isolation_candidates", lambda: harness.HostIsolationCandidates((), (), 0, False, False))
    monkeypatch.setattr(sys, "argv", ["isolated_runtime_test.py", "--audit-real-app"])
    assert harness.main() == 2
    report = json.loads(capsys.readouterr().out)
    assert report["realAppGate"]["launchAllowed"] is False
    assert "layout" not in report
