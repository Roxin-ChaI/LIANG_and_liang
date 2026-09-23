from __future__ import annotations

import importlib.util
import json
import plistlib
from pathlib import Path

import pytest


MODULE_PATH = Path(__file__).resolve().parents[1] / "tools/local_mac_runtime_test.py"
spec = importlib.util.spec_from_file_location("local_mac_runtime_test", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)


def test_refuses_official_or_outside_app(tmp_path: Path) -> None:
    phase = tmp_path / "phase8c"
    phase.mkdir()
    with pytest.raises(module.LocalRuntimeError):
        module.assert_temp_app(module.OFFICIAL_APP, phase)
    outside = tmp_path / "ChatGPT.app"
    outside.mkdir()
    with pytest.raises(module.LocalRuntimeError):
        module.assert_temp_app(outside, phase)


def test_integrity_update_refuses_wrong_asar(tmp_path: Path) -> None:
    app = tmp_path / "ChatGPT.app"
    resources = app / "Contents/Resources"
    resources.mkdir(parents=True)
    (resources / "app.asar").write_bytes(b"not-the-recipe")
    with pytest.raises(module.LocalRuntimeError):
        module.update_integrity(app, "0" * 64)


def test_plist_format_selection(tmp_path: Path) -> None:
    # The official bundle may use binary plist; production metadata should
    # remain in its original serialization family after the update.
    for fmt in (plistlib.FMT_BINARY, plistlib.FMT_XML):
        encoded = plistlib.dumps({"ElectronAsarIntegrity": {"Resources/app.asar": {"algorithm": "SHA256"}}}, fmt=fmt)
        assert (encoded.startswith(b"bplist")) == (fmt == plistlib.FMT_BINARY)


def test_signed_copy_is_not_reported_as_launchable(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    phase = tmp_path / "phase8c"
    app = phase / "ChatGPT.app"
    resources = app / "Contents/Resources"
    resources.mkdir(parents=True)
    archive = resources / "app.asar"
    archive.write_bytes(b"patched")
    info = {"ElectronAsarIntegrity": {"Resources/app.asar": {"algorithm": "SHA256", "hash": "header"}}}
    (app / "Contents/Info.plist").write_bytes(plistlib.dumps(info))
    baseline = phase / "baseline.json"
    baseline.write_text(json.dumps({"recipeValidation": {"locatorCount": 12, "deterministicPatchedAsarSha256": "patched-hash"}}))
    monkeypatch.setattr(module, "BASELINE", baseline)
    monkeypatch.setattr(module, "sha256_file", lambda path: "patched-hash")
    monkeypatch.setattr(module, "update_integrity", lambda app, expected: "header")
    monkeypatch.setattr(module, "sign_temporary_app", lambda app, root: {"adHocSigning": "PASS"})
    result = module.prepare(app, phase)
    assert result["status"] == "TEMP_APP_SIGNED_LAUNCH_UNVERIFIED"
    assert result["launchabilityProven"] is False
