from __future__ import annotations

import json
import struct
from pathlib import Path

import pytest

from tools import inspect_runtime_isolation as recon


def test_bootstrap_order_and_explicit_override_are_confirmed() -> None:
    source = (
        "CODEX_ELECTRON_USER_DATA_PATH;"
        "o.app.setPath(`userData`,pk(...));"
        "hasExplicitUserDataPath:!!process.env.CODEX_ELECTRON_USER_DATA_PATH?.trim();"
        "if(bj&&!o.app.requestSingleInstanceLock());"
        "o.app.on(`second-instance`"
    )
    result = recon.analyze_bootstrap(source)
    assert result["status"] == "CONFIRMED"
    assert result["userDataBeforeLock"] is True
    assert result["lockScopedAwayFromProduction"] == "NOT_PROVEN"


def test_bootstrap_order_fails_closed_if_unknown() -> None:
    result = recon.analyze_bootstrap("if(bj&&!o.app.requestSingleInstanceLock())")
    assert result["status"] == "NOT_PROVEN"
    assert result["userDataBeforeLock"] is False


def test_entitlement_keys_are_not_effective_ad_hoc_permissions() -> None:
    values = {
        "keychain-access-groups": ["2DC432GLL2.*", "2DC432GLL2.com.openai.shared"]
    }
    result = recon.classify_entitlements(values, "2DC432GLL2")
    assert result["productionKeychainGroupsDeclared"] is True
    assert result["sameAppleTeamAfterAdHocSigning"] is False
    assert result["effectiveKeychainAccessAfterAdHocSigning"] == "NOT_PROVEN"


def test_read_one_packed_asar_entry_without_extraction(tmp_path: Path) -> None:
    payload = b"owned test bytes"
    header_json = json.dumps({"files": {"a.js": {"offset": "0", "size": len(payload)}}}).encode()
    aligned = (4 + len(header_json) + 1 + 3) & ~3
    header_size = 4 + aligned
    archive = tmp_path / "fixture.asar"
    archive.write_bytes(
        struct.pack("<II", 4, header_size)
        + struct.pack("<II", aligned, len(header_json))
        + header_json
        + b"\0" * (aligned - 4 - len(header_json))
        + payload
    )
    assert recon.packed_asar_file(archive, "a.js") == payload
    assert sorted(path.name for path in tmp_path.iterdir()) == ["fixture.asar"]


def test_wrong_or_truncated_asar_is_rejected(tmp_path: Path) -> None:
    archive = tmp_path / "invalid.asar"
    archive.write_bytes(b"invalid")
    with pytest.raises(ValueError):
        recon.packed_asar_file(archive, "bootstrap.js")
