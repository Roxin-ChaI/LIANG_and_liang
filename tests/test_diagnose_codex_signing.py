from __future__ import annotations

import importlib.util
import plistlib
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
MODULE_SPEC = importlib.util.spec_from_file_location(
    "diagnose_codex_signing_module", ROOT / "tools/diagnose_codex_signing.py"
)
assert MODULE_SPEC and MODULE_SPEC.loader
diagnosis = importlib.util.module_from_spec(MODULE_SPEC)
sys.modules[MODULE_SPEC.name] = diagnosis
MODULE_SPEC.loader.exec_module(diagnosis)


def entitlement_plist() -> bytes:
    return plistlib.dumps(
        {
            "com.apple.application-identifier": "TEAM.com.openai.codex",
            "com.apple.security.cs.allow-jit": True,
        }
    )


class FakeRunner:
    def __init__(self) -> None:
        self.commands: list[tuple[str, ...]] = []
        self.main_verify_returncode = 0
        self.nested_failures: set[str] = set()
        self.entitlement_mode = "valid"
        self.codesign_available = True
        self.on_run = None

    def result(
        self,
        argv: tuple[str, ...],
        returncode: int = 0,
        stdout: bytes = b"",
        stderr: bytes = b"",
        available: bool = True,
    ):
        return diagnosis.CommandResult(argv, returncode, stdout, stderr, available)

    def run(self, argv):
        command = tuple(str(value) for value in argv)
        self.commands.append(command)
        if self.on_run is not None:
            self.on_run(command)
        if command[0] == "codesign" and not self.codesign_available:
            return self.result(command, 127, stderr=b"codesign unavailable", available=False)
        if command[:3] == ("codesign", "-dv", "--verbose=4"):
            return self.result(
                command,
                stderr=(
                    b"Identifier=com.openai.codex\n"
                    b"CodeDirectory v=20500 flags=0x10000(runtime)\n"
                    b"TeamIdentifier=TEAM\nNotarization Ticket=stapled\n"
                ),
            )
        if command[:4] == ("codesign", "--verify", "--deep", "--strict"):
            return self.result(
                command,
                self.main_verify_returncode,
                stderr=b"invalid signature" if self.main_verify_returncode else b"",
            )
        if command[:3] == ("codesign", "--verify", "--strict"):
            target = command[-1]
            failed = target in self.nested_failures or (
                target.endswith("ChatGPT.app") and self.main_verify_returncode != 0
            )
            return self.result(command, int(failed), stderr=b"invalid signature" if failed else b"")
        if command[:4] == ("codesign", "--display", "--entitlements", "-"):
            if "--xml" in command:
                if self.entitlement_mode == "valid":
                    return self.result(command, stdout=entitlement_plist())
                if self.entitlement_mode == "malformed":
                    return self.result(command, stderr=b"warning: invalid entitlements blob")
                return self.result(command)
            if "--der" in command:
                return self.result(command, stdout=b"DER" if self.entitlement_mode != "none" else b"")
            return self.result(
                command,
                stdout=b"[Dict]\n[Key] allow-jit\n" if self.entitlement_mode != "none" else b"",
            )
        if command[:4] == ("codesign", "--display", "--entitlements", ":-"):
            stderr = b"warning: invalid entitlements blob" if self.entitlement_mode == "malformed" else b""
            return self.result(command, stdout=entitlement_plist() if self.entitlement_mode == "valid" else b"", stderr=stderr)
        return self.result(command)


def make_app(root: Path, *, integrity_matches: bool = True) -> Path:
    app = root / "ChatGPT.app"
    resources = app / "Contents/Resources"
    resources.mkdir(parents=True)
    (app / "Contents/MacOS").mkdir()
    (app / "Contents/_CodeSignature").mkdir()
    archive = resources / "app.asar"
    archive.write_bytes(b"current asar")
    executable = app / "Contents/MacOS/ChatGPT"
    executable.write_bytes(b"executable")
    (app / "Contents/_CodeSignature/CodeResources").write_bytes(b"seal")
    expected = diagnosis.sha256_file(archive) if integrity_matches else "0" * 64
    with (app / "Contents/Info.plist").open("wb") as handle:
        plistlib.dump(
            {
                "CFBundleIdentifier": "com.openai.codex",
                "CFBundleShortVersionString": "26.915.31945",
                "CFBundleVersion": "9922",
                "ElectronAsarIntegrity": {
                    "Resources/app.asar": {"algorithm": "SHA256", "hash": expected}
                },
            },
            handle,
        )
    return app


def run(app: Path, runner: FakeRunner, *, nested_components=()):
    return diagnosis.diagnose(
        app,
        runner=runner,
        nested_components=nested_components,
        clean_roots=[app.parent / "clean-references"],
    )


def test_valid_signature_and_entitlements_are_reported(tmp_path: Path) -> None:
    app = make_app(tmp_path)
    result = run(app, FakeRunner())
    assert result["codesignDeepStrict"]["returncode"] == 0
    assert result["entitlements"]["status"] == "VALID_XML"
    assert result["tempSigningExperiment"] == "TEMP_SIGNING_EXPERIMENT_ALLOWED"


def test_nested_failure_is_narrowed_to_first_component(tmp_path: Path) -> None:
    app = make_app(tmp_path)
    nested = tmp_path / "Nested.app"
    runner = FakeRunner()
    runner.nested_failures.add(str(nested))
    result = run(app, runner, nested_components=[nested])
    assert result["components"]["firstFailingComponent"] == str(nested)
    assert result["components"]["failCount"] == 1


def test_main_failure_is_reported_before_nested_components(tmp_path: Path) -> None:
    app = make_app(tmp_path)
    runner = FakeRunner()
    runner.main_verify_returncode = 1
    result = run(app, runner, nested_components=[tmp_path / "Nested.app"])
    assert result["components"]["firstFailingComponent"] == str(app)
    assert result["codesignDeepStrict"]["returncode"] == 1


def test_malformed_entitlement_output_blocks_temp_signing(tmp_path: Path) -> None:
    app = make_app(tmp_path)
    runner = FakeRunner()
    runner.entitlement_mode = "malformed"
    result = run(app, runner)
    assert result["entitlements"]["status"] == "MALFORMED_XML_BLOB"
    assert result["entitlements"]["der"]["present"] is True
    assert result["tempSigningExperiment"] == "TEMP_SIGNING_EXPERIMENT_BLOCKED"


def test_no_entitlements_are_distinguished_from_malformed(tmp_path: Path) -> None:
    app = make_app(tmp_path)
    runner = FakeRunner()
    runner.entitlement_mode = "none"
    result = run(app, runner)
    assert result["entitlements"]["status"] == "NO_ENTITLEMENTS"


def test_asar_integrity_match(tmp_path: Path) -> None:
    result = run(make_app(tmp_path, integrity_matches=True), FakeRunner())
    assert result["asarIntegrity"]["status"] == "ASAR_INTEGRITY_MATCH"


def test_asar_integrity_mismatch_is_a_confirmed_cause(tmp_path: Path) -> None:
    result = run(make_app(tmp_path, integrity_matches=False), FakeRunner())
    assert result["asarIntegrity"]["status"] == "ASAR_INTEGRITY_MISMATCH"
    assert result["causeClassification"] == "BASELINE_SIGNING_CAUSE_CONFIRMED"


def test_command_unavailable_is_explicit(tmp_path: Path) -> None:
    app = make_app(tmp_path)
    runner = FakeRunner()
    runner.codesign_available = False
    result = run(app, runner)
    assert result["entitlements"]["status"] == "COMMAND_UNAVAILABLE"
    assert result["codesignDetails"]["command"]["available"] is False


def test_clean_reference_unavailable(tmp_path: Path) -> None:
    result = run(make_app(tmp_path), FakeRunner())
    assert result["cleanReference"] == {
        "status": "CLEAN_REFERENCE_UNAVAILABLE",
        "candidates": [],
    }


def test_zero_mutation_guard_detects_runner_side_effect(tmp_path: Path) -> None:
    app = make_app(tmp_path)
    runner = FakeRunner()
    changed = False

    def mutate_once(_command) -> None:
        nonlocal changed
        if not changed:
            changed = True
            (app / "Contents/Resources/app.asar").write_bytes(b"mutated")

    runner.on_run = mutate_once
    with pytest.raises(diagnosis.SigningDiagnosisError) as caught:
        run(app, runner)
    assert caught.value.code == "APP_MUTATED"


def test_diagnosis_uses_only_read_only_commands(tmp_path: Path) -> None:
    runner = FakeRunner()
    result = run(make_app(tmp_path), runner)
    assert result["zeroMutation"] is True
    assert not any("--sign" in command or "--force" in command for command in runner.commands)
    assert not any(command[:2] in {("xattr", "-w"), ("chmod", "-R"), ("chown", "-R")} for command in runner.commands)
