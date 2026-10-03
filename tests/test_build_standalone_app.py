from pathlib import Path

import pytest

from tools import build_standalone_app as subject


def test_bundle_inventory_contains_exact_form_and_transition_inputs() -> None:
    files = subject.source_files()
    paths = {relative.as_posix() for _, relative in files}
    assert len(paths) == len(files) == 43
    assert "assets/builds/gu/spritesheet.webp" in paths
    assert "assets/builds/feng/spritesheet.webp" in paths
    assert sum(path.startswith("assets/transform-overlay/gu_to_feng/") for path in paths) == 10
    assert sum(path.startswith("assets/transform-overlay/feng_to_gu/") for path in paths) == 8
    assert {"standalone-app/codex-events.mjs", "tools/codex_hook_receiver.py",
            "tools/codex_hook_probe.py"} <= paths
    assert not any("app.asar" in path or ".codex" in path for path in paths)


def test_build_refuses_existing_destination_before_copy(tmp_path: Path) -> None:
    destination = tmp_path / "Liang no Henshin.app"
    destination.mkdir()
    with pytest.raises(RuntimeError, match="already exists"):
        subject.build(destination)
