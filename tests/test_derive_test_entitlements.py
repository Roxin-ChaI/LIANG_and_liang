from __future__ import annotations

import json
import plistlib
import subprocess
from pathlib import Path
from types import SimpleNamespace

from tools import derive_test_entitlements as subject


def test_per_component_policy_never_copies_identity_claims() -> None:
    main = subject.derive_component({
        "component": ".",
        "hardenedRuntime": True,
        "originalEntitlements": {
            "com.apple.application-identifier": "TEAM.com.openai.codex",
            "com.apple.developer.team-identifier": "TEAM",
            "com.apple.developer.aps-environment": "production",
            "com.apple.security.application-groups": ["TEAM.group"],
            "keychain-access-groups": ["TEAM.shared"],
            "com.apple.security.cs.allow-jit": True,
            "com.apple.security.device.camera": True,
            "com.apple.security.app-sandbox": False,
        },
    })
    assert main["testEntitlements"] == {"com.apple.security.cs.allow-jit": True}
    assert set(subject.IDENTITY_BOUND_KEYS) <= set(main["removed"])
    assert main["planStatus"] == "PROPOSED_NOT_LAUNCH_VALIDATED"


def test_each_helper_gets_only_its_own_original_runtime_exceptions() -> None:
    renderer = subject.derive_component({
        "component": "renderer.app", "hardenedRuntime": True,
        "originalEntitlements": {"com.apple.security.cs.allow-jit": True},
    })
    service = subject.derive_component({
        "component": "service.app", "hardenedRuntime": True,
        "originalEntitlements": {"com.apple.security.cs.disable-library-validation": True},
    })
    assert renderer["testEntitlements"] == {"com.apple.security.cs.allow-jit": True}
    assert service["testEntitlements"] == {"com.apple.security.cs.disable-library-validation": True}


def test_unknown_or_sandboxed_component_requires_review() -> None:
    for key, value in (("com.apple.private.unknown", True), ("com.apple.security.app-sandbox", True)):
        record = subject.derive_component({
            "component": "helper.app", "hardenedRuntime": True,
            "originalEntitlements": {key: value},
        })
        assert record["planStatus"] == "REVIEW_REQUIRED"
        assert key in record["unknownRisks"]


def test_component_discovery_skips_framework_symlink(tmp_path: Path) -> None:
    app = tmp_path / "ChatGPT.app"
    framework = app / "Contents/Frameworks/Codex Framework.framework"
    helpers = framework / "Versions/A/Helpers"
    helper = helpers / "Codex (Renderer).app"
    helper.mkdir(parents=True)
    (framework / "Versions/Current").symlink_to("A")
    (framework / "Current").symlink_to("Versions/A")
    dylib = framework / "Versions/A/test.dylib"
    dylib.write_bytes(b"fixture")
    names = [path.relative_to(app).as_posix() for path in subject.discover_components(app)]
    assert names[0] == "."
    assert sum(name.endswith("Codex (Renderer).app") for name in names) == 1
    assert "Contents/Frameworks/Codex Framework.framework/Versions/A/test.dylib" in names


def test_inspect_extracts_component_specific_values_without_reading_profile(tmp_path: Path) -> None:
    app = tmp_path / "ChatGPT.app"
    component = app / "Contents/Frameworks/Helper.app"
    (component / "Contents").mkdir(parents=True)
    (component / "Contents/embedded.provisionprofile").write_bytes(b"do not decode")
    calls = []

    def run(command: list[str]) -> subprocess.CompletedProcess[bytes]:
        calls.append(command)
        if "--entitlements" in command:
            return subprocess.CompletedProcess(command, 0, plistlib.dumps({"com.apple.security.cs.allow-jit": True}), b"")
        return subprocess.CompletedProcess(command, 0, b"", b"Identifier=test.helper\nTeamIdentifier=TEAM\nflags=0x10000(runtime)\n")

    result = subject.inspect_component(app, component, run)
    assert result["profilePresent"] is True
    assert result["hardenedRuntime"] is True
    assert result["originalEntitlements"] == {"com.apple.security.cs.allow-jit": True}
    assert len(calls) == 2


def test_wrong_build_blocks_before_any_component_inspection(monkeypatch, tmp_path: Path) -> None:
    baseline = tmp_path / "baseline.json"
    baseline.write_text(json.dumps({"classification": "TRUSTED_BASELINE", "version": "26.915.31945", "build": "9922", "appAsar": {"sha256": "old"}, "executable": {"sha256": "oldexe"}}))
    monkeypatch.setattr(subject, "fingerprint", lambda _app: SimpleNamespace(
        version="26.924", build="10789", app_asar_sha256="new", executable_sha256="newexe"
    ))
    monkeypatch.setattr(subject, "verify_source", lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("must not run preflight")))
    monkeypatch.setattr(subject, "discover_components", lambda *_args: (_ for _ in ()).throw(AssertionError("must not inspect")))
    report = subject.build_matrix(tmp_path / "ChatGPT.app", baseline)
    assert report == {"status": "BLOCKED_SOURCE_UNSUPPORTED_BUILD", "sourceBuild": "10789", "components": []}


def test_matching_source_produces_matrix_but_not_launch_pass(monkeypatch, tmp_path: Path) -> None:
    app = tmp_path / "ChatGPT.app"
    baseline = tmp_path / "baseline.json"
    baseline.write_text(json.dumps({"classification": "TRUSTED_BASELINE", "version": "26.915.31945", "build": "9922", "appAsar": {"sha256": "old"}, "executable": {"sha256": "oldexe"}}))
    monkeypatch.setattr(subject, "fingerprint", lambda _app: SimpleNamespace(
        version="26.915.31945", build="9922", app_asar_sha256="old", executable_sha256="oldexe"
    ))
    monkeypatch.setattr(subject, "verify_source", lambda *_args, **_kwargs: SimpleNamespace(
        status="PASS", fingerprint=SimpleNamespace(build="9922")
    ))
    monkeypatch.setattr(subject, "discover_components", lambda _app: [app, app / "Contents/Frameworks/Helper.app"])
    monkeypatch.setattr(subject, "inspect_component", lambda _app, path, _run: {
        "component": "." if path == app else "Helper.app",
        "hardenedRuntime": True,
        "originalEntitlements": {"com.apple.security.cs.allow-jit": True},
    })
    report = subject.build_matrix(app, baseline)
    assert report["status"] == "PROPOSED_NOT_LAUNCH_VALIDATED"
    assert len(report["components"]) == 2
