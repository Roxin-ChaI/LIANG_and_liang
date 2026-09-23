from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image

from tools import run_electron_harness as harness


def test_isolated_environment_does_not_inherit_credentials(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "production-secret")
    monkeypatch.setenv("CODEX_API_KEY", "production-secret")
    environment = harness.isolated_environment(tmp_path)
    assert environment["HOME"] == str(tmp_path / "home")
    assert environment["CODEX_HOME"] == str(tmp_path / "codex-home")
    assert environment["LNH_HARNESS_BUNDLE_ID"] == harness.TEST_BUNDLE_ID
    assert not any("KEY" in key or "TOKEN" in key for key in environment)
    assert "production-secret" not in environment.values()


def test_missing_independent_binary_blocks_before_copy(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(harness, "ELECTRON_APP", tmp_path / "missing.app")
    with pytest.raises(harness.HarnessError, match="independent Electron binary"):
        harness.prepare_app(tmp_path)
    assert not (tmp_path / "LiangHarness.app").exists()


def geometry_event(name: str, size: tuple[int, int], offset: tuple[int, int]) -> dict[str, object]:
    return {
        "type": "renderer", "transitionId": name,
        "normal": {"x": 96, "y": 42, "width": 192, "height": 208},
        "overlay": {"x": 96 + offset[0], "y": 42 + offset[1],
                    "width": size[0], "height": size[1]},
        "overlayPointerEvents": "none", "normalPointerEvents": "auto",
        "overlayNaturalWidth": size[0], "overlayNaturalHeight": size[1],
    }


def evidence_fixture(tmp_path: Path) -> tuple[list[dict[str, object]], Path]:
    events = [
        geometry_event("gu_to_feng", (224, 240), (-16, -18)),
        geometry_event("feng_to_gu", (208, 224), (-9, -14)),
        {"type": "edge", "bounds": {"x": 1020, "y": 540, "width": 420, "height": 360},
         "workArea": {"x": 0, "y": 30, "width": 1440, "height": 870}},
    ]
    for name in ("idle", "gu_to_feng_edge", "feng_to_gu"):
        image = Image.new("RGB", (840, 656), (24, 32, 43))
        for x in range(200, 400):
            for y in range(80, 430):
                image.putpixel((x, y), (30, 100, 190))
        image.save(tmp_path / f"{name}.png")
    return events, tmp_path


def test_visual_geometry_and_screenshots_pass(tmp_path: Path) -> None:
    events, evidence = evidence_fixture(tmp_path)
    result = harness.validate_visual(events, evidence)
    assert result["geometry"]["gu_to_feng"]["size"] == (224, 240)
    assert result["screenshots"]["idle"]["pixels"] == [840, 656]
    assert result["physicalScreenCompositorVerified"] is False


def test_visual_validation_rejects_drag_hitbox_change(tmp_path: Path) -> None:
    events, evidence = evidence_fixture(tmp_path)
    events[0]["normal"]["width"] = 193
    with pytest.raises(harness.HarnessError, match="drag hitbox"):
        harness.validate_visual(events, evidence)
