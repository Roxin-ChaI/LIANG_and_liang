from __future__ import annotations

import json
import plistlib
import subprocess
import struct
from pathlib import Path
from types import SimpleNamespace

import pytest

from tools import sign_minimal_temp_codex as subject


def test_macho_text_hash_ignores_signature_bytes(tmp_path: Path) -> None:
    path = tmp_path / "ChatGPT"
    data = bytearray(256)
    data[:4] = b"\xcf\xfa\xed\xfe"
    struct.pack_into("<I", data, 16, 1)
    struct.pack_into("<II", data, 32, 0x19, 152)
    struct.pack_into("<I", data, 32 + 64, 1)
    data[104:110] = b"__text"
    data[120:126] = b"__TEXT"
    struct.pack_into("<Q", data, 104 + 40, 5)
    struct.pack_into("<I", data, 104 + 48, 200)
    data[200:205] = b"hello"
    path.write_bytes(data)
    before = subject.macho_text_hash(path)
    data[220:230] = b"signature!"
    path.write_bytes(data)
    assert subject.macho_text_hash(path) == before
    data[200] = ord("H")
    path.write_bytes(data)
    assert subject.macho_text_hash(path) != before


def test_signing_target_must_be_isolated_real_app(tmp_path: Path) -> None:
    root = tmp_path / "phase8f"
    root.mkdir()
    app = root / "ChatGPT.app"
    app.mkdir()
    subject.assert_temporary_app(app, root, tmp_path / "source.app")
    with pytest.raises(subject.SigningError):
        subject.assert_temporary_app(app, tmp_path / "other", tmp_path / "source.app")
    link = root / "link.app"
    link.symlink_to(app, target_is_directory=True)
    with pytest.raises(subject.SigningError):
        subject.assert_temporary_app(link, root, tmp_path / "source.app")


def test_preflight_refuses_unproven_matrix_before_signing(monkeypatch, tmp_path: Path) -> None:
    root = tmp_path / "work"
    app = root / "ChatGPT.app"
    app.mkdir(parents=True)
    baseline = tmp_path / "baseline.json"
    baseline.write_text("{}")
    monkeypatch.setattr(subject, "build_matrix", lambda *_args: {"status": "BLOCKED_COMPONENT_REVIEW"})
    with pytest.raises(subject.SigningError, match="matrix"):
        subject.preflight(tmp_path / "source.app", app, baseline, root)
    assert list(root.iterdir()) == [app]


def test_signs_inner_component_before_main_and_never_copies_profile(monkeypatch, tmp_path: Path) -> None:
    root = tmp_path / "work"
    app = root / "ChatGPT.app"
    helper = app / "Contents/Frameworks/Helper.app"
    (helper / "Contents").mkdir(parents=True)
    profile = helper / "Contents/embedded.provisionprofile"
    profile.write_bytes(b"fixture profile is never read")
    baseline = tmp_path / "baseline.json"
    baseline.write_text(json.dumps({
        "recipeValidation": {"deterministicPatchedAsarSha256": "patched"},
        "executable": {"sha256": "executable"},
    }))
    rows = [
        {"component": ".", "testEntitlements": {"com.apple.security.cs.allow-jit": True}, "profilePresent": False},
        {"component": "Contents/Frameworks/Helper.app", "testEntitlements": {}, "profilePresent": True},
    ]
    monkeypatch.setattr(subject, "preflight", lambda *_args, **_kwargs: {"components": rows})
    commands: list[list[str]] = []

    def fake_run(command: list[str]) -> subprocess.CompletedProcess[bytes]:
        commands.append(command)
        return subprocess.CompletedProcess(command, 0, b"", b"")

    monkeypatch.setattr(subject, "run", fake_run)
    monkeypatch.setattr(subject, "inspect_component", lambda _app, component: {
        "originalEntitlements": {} if component == helper else {"com.apple.security.cs.allow-jit": True},
        "hardenedRuntime": True,
        "teamIdentifier": "not set",
        "profilePresent": False,
    })
    monkeypatch.setattr(subject, "fingerprint", lambda _app: SimpleNamespace(
        app_asar_sha256="patched", executable_sha256="executable",
        integrity_expected="header", asar_header_sha256="header",
    ))
    result = subject.sign_temporary_app(tmp_path / "source.app", app, baseline, root)
    assert result["componentCount"] == 2
    assert result["profileRemovedFromTemporaryComponents"] == ["Contents/Frameworks/Helper.app"]
    assert not profile.exists()
    assert commands[0][-1] == str(helper)
    assert commands[1][-1] == str(app)
    assert all("--options" in command and "runtime" in command for command in commands[:2])
    assert "--deep" not in commands[0] and "--deep" not in commands[1]
    files = list((root / "minimal-entitlements").glob("*.plist"))
    assert len(files) == 1
    assert plistlib.loads(files[0].read_bytes()) == {"com.apple.security.cs.allow-jit": True}
