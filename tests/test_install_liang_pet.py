from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from tools import install_liang_pet as installer


ROOT = Path(__file__).resolve().parents[1]


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def snapshot(root: Path) -> dict[str, tuple[str, str]]:
    if not root.exists():
        return {}
    result: dict[str, tuple[str, str]] = {}
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root).as_posix()
        if path.is_symlink():
            result[relative] = ("link", os.readlink(path))
        elif path.is_dir():
            result[relative] = ("dir", "")
        else:
            result[relative] = ("file", digest(path))
    return result


@pytest.fixture(scope="session")
def payload(tmp_path_factory: pytest.TempPathFactory) -> Path:
    output = tmp_path_factory.mktemp("liang-payload") / "output"
    subprocess.run(
        ["node", str(ROOT / "installer/pet-payload.mjs"), "--output", str(output)],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return output / installer.PET_DIRECTORY


@pytest.fixture
def fake_home(tmp_path: Path) -> Path:
    home = tmp_path / ".codex"
    home.mkdir()
    return home


def clone_payload(payload: Path, target: Path, *, revision: str) -> Path:
    shutil.copytree(payload, target)
    pet_path = target / "pet.json"
    pet = json.loads(pet_path.read_text())
    pet["testRevision"] = revision
    pet_path.write_text(json.dumps(pet, indent=2, sort_keys=True) + "\n")
    manifest_path = target / installer.MANIFEST_NAME
    manifest = json.loads(manifest_path.read_text())
    manifest["files"]["pet.json"] = digest(pet_path)
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    return target


def make_other_pet(home: Path) -> Path:
    other = home / "pets/existing-test-pet"
    other.mkdir(parents=True)
    (other / "keep.txt").write_text("do not touch\n")
    return other


def error_code(callable_) -> str:
    with pytest.raises(installer.InstallerError) as caught:
        callable_()
    return caught.value.code


def test_first_install_places_complete_verified_pet(payload: Path, fake_home: Path) -> None:
    result = installer.install(codex_home=fake_home, payload=payload)
    destination = fake_home / "pets/liang-no-henshin"
    assert result.action == "INSTALL"
    assert result.changed is True
    assert Path(result.destination) == destination
    info = installer.validate_payload(payload)
    installer._owned_state(destination)
    state = json.loads((destination / installer.STATE_NAME).read_text())
    assert state["payloadManifestHash"] == info.manifest_hash


def test_install_path_is_scoped_to_fake_codex_home(payload: Path, fake_home: Path) -> None:
    installer.install(codex_home=fake_home, payload=payload)
    assert (fake_home / "pets/liang-no-henshin/pet.json").is_file()


def test_every_installed_hash_matches_manifest(payload: Path, fake_home: Path) -> None:
    installer.install(codex_home=fake_home, payload=payload)
    root = fake_home / "pets/liang-no-henshin"
    manifest = json.loads((root / installer.MANIFEST_NAME).read_text())
    assert all(digest(root / relative) == expected for relative, expected in manifest["files"].items())


def test_missing_config_gets_minimal_desktop_selection(payload: Path, fake_home: Path) -> None:
    installer.install(codex_home=fake_home, payload=payload)
    assert (fake_home / "config.toml").read_text() == '[desktop]\nselected-avatar-id = "custom:liang-no-henshin"\n'


def test_missing_desktop_section_is_appended(payload: Path, fake_home: Path) -> None:
    (fake_home / "config.toml").write_text("# user config\n[features]\nbeta = true\n")
    installer.install(codex_home=fake_home, payload=payload)
    text = (fake_home / "config.toml").read_text()
    assert text.startswith("# user config\n[features]\nbeta = true\n")
    assert '[desktop]\nselected-avatar-id = "custom:liang-no-henshin"\n' in text


def test_existing_desktop_section_only_gains_selection(payload: Path, fake_home: Path) -> None:
    before = "[desktop]\nscale = 2\n[other]\nname = 'kept'\n"
    (fake_home / "config.toml").write_text(before)
    installer.install(codex_home=fake_home, payload=payload)
    after = (fake_home / "config.toml").read_text()
    assert "scale = 2" in after and "name = 'kept'" in after
    assert after.count("selected-avatar-id") == 1


def test_previous_avatar_is_replaced_and_recorded(payload: Path, fake_home: Path) -> None:
    (fake_home / "config.toml").write_text('[desktop]\nselected-avatar-id = "custom:old"\n')
    installer.install(codex_home=fake_home, payload=payload)
    state = json.loads((fake_home / f"pets/{installer.PET_DIRECTORY}/{installer.STATE_NAME}").read_text())
    assert state["previousSelectedAvatarId"] == "custom:old"
    assert 'selected-avatar-id = "custom:liang-no-henshin"' in (fake_home / "config.toml").read_text()


def test_config_comments_and_formatting_are_preserved(payload: Path, fake_home: Path) -> None:
    before = "# top\n[desktop] # desktop\n  selected-avatar-id = 'custom:old' # choice\nkeep = 7\n\n[tail]\nvalue = 9\n"
    (fake_home / "config.toml").write_text(before)
    installer.install(codex_home=fake_home, payload=payload)
    after = (fake_home / "config.toml").read_text()
    assert "# top" in after and "# choice" in after and "[tail]\nvalue = 9" in after
    assert "  selected-avatar-id = 'custom:liang-no-henshin' # choice" in after


def test_idempotent_reinstall_is_already_current_without_pet_rewrite(payload: Path, fake_home: Path) -> None:
    installer.install(codex_home=fake_home, payload=payload)
    atlas = fake_home / "pets/liang-no-henshin/spritesheet.webp"
    inode = atlas.stat().st_ino
    result = installer.install(codex_home=fake_home, payload=payload)
    assert result.action == "ALREADY_CURRENT"
    assert result.changed is False
    assert atlas.stat().st_ino == inode


def test_owned_installation_updates_and_keeps_original_selection(payload: Path, fake_home: Path, tmp_path: Path) -> None:
    old_payload = clone_payload(payload, tmp_path / "old", revision="old")
    (fake_home / "config.toml").write_text('[desktop]\nselected-avatar-id = "custom:before"\n')
    installer.install(codex_home=fake_home, payload=old_payload)
    result = installer.install(codex_home=fake_home, payload=payload)
    state = json.loads((fake_home / f"pets/{installer.PET_DIRECTORY}/{installer.STATE_NAME}").read_text())
    assert result.action == "UPDATE"
    assert state["previousSelectedAvatarId"] == "custom:before"
    assert state["payloadManifestHash"] == digest(payload / installer.MANIFEST_NAME)


def test_unknown_existing_directory_is_refused_without_writes(payload: Path, fake_home: Path) -> None:
    destination = fake_home / "pets/liang-no-henshin"
    destination.mkdir(parents=True)
    (destination / "user.txt").write_text("mine\n")
    before = snapshot(fake_home)
    assert error_code(lambda: installer.install(codex_home=fake_home, payload=payload)) == "REFUSE_UNOWNED_DESTINATION"
    assert snapshot(fake_home) == before


def test_uninstall_removes_owned_pet_and_restores_previous_selection(payload: Path, fake_home: Path) -> None:
    (fake_home / "config.toml").write_text('[desktop]\nselected-avatar-id = "custom:old"\nkeep = true\n')
    installer.install(codex_home=fake_home, payload=payload)
    result = installer.uninstall(codex_home=fake_home)
    assert result.action == "UNINSTALL"
    assert not (fake_home / "pets/liang-no-henshin").exists()
    assert (fake_home / "config.toml").read_text() == '[desktop]\nselected-avatar-id = "custom:old"\nkeep = true\n'


def test_uninstall_removes_added_selection_but_preserves_desktop(payload: Path, fake_home: Path) -> None:
    (fake_home / "config.toml").write_text("[desktop]\nkeep = 4\n")
    installer.install(codex_home=fake_home, payload=payload)
    installer.uninstall(codex_home=fake_home)
    assert (fake_home / "config.toml").read_text() == "[desktop]\nkeep = 4\n"


def test_payload_hash_mismatch_is_rejected(payload: Path, fake_home: Path, tmp_path: Path) -> None:
    broken = shutil.copytree(payload, tmp_path / "broken")
    (broken / "pet.json").write_text("{}\n")
    assert error_code(lambda: installer.install(codex_home=fake_home, payload=broken)) == "PAYLOAD_HASH_MISMATCH"
    assert snapshot(fake_home) == {}


def test_copy_failure_cleans_partial_staging(payload: Path, fake_home: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    original = shutil.copytree

    def fail_copy(source: Path, destination: Path, **kwargs):
        Path(destination).mkdir()
        (Path(destination) / "partial").write_text("partial")
        raise OSError("simulated copy failure")

    monkeypatch.setattr(shutil, "copytree", fail_copy)
    with pytest.raises(OSError, match="simulated copy failure"):
        installer.install(codex_home=fake_home, payload=payload)
    monkeypatch.setattr(shutil, "copytree", original)
    assert snapshot(fake_home) == {}


def test_hash_failure_after_copy_rolls_back(payload: Path, fake_home: Path) -> None:
    def corrupt(stage: str, paths: dict[str, Path]) -> None:
        if stage == "after-copy":
            (paths["staging"] / "pet.json").write_text("corrupt")

    assert error_code(lambda: installer.install(codex_home=fake_home, payload=payload, fault_hook=corrupt)) == "PAYLOAD_HASH_MISMATCH"
    assert snapshot(fake_home) == {}


def test_config_failure_rolls_back_new_install(payload: Path, fake_home: Path) -> None:
    (fake_home / "config.toml").write_text("# before\n")
    before = snapshot(fake_home)

    def fail(stage: str, paths: dict[str, Path]) -> None:
        if stage == "before-config-write":
            raise OSError("simulated config failure")

    with pytest.raises(OSError, match="simulated config failure"):
        installer.install(codex_home=fake_home, payload=payload, fault_hook=fail)
    assert snapshot(fake_home) == before


def test_destination_rename_failure_restores_old_install(payload: Path, fake_home: Path, tmp_path: Path) -> None:
    old_payload = clone_payload(payload, tmp_path / "old", revision="old")
    installer.install(codex_home=fake_home, payload=old_payload)
    before = snapshot(fake_home)

    def fail(stage: str, paths: dict[str, Path]) -> None:
        if stage == "before-destination-rename":
            raise OSError("simulated rename failure")

    with pytest.raises(OSError, match="simulated rename failure"):
        installer.install(codex_home=fake_home, payload=payload, fault_hook=fail)
    assert snapshot(fake_home) == before


@pytest.mark.parametrize("kind", ["destination", "pets", "config", "payload"])
def test_symlink_inputs_are_rejected(payload: Path, fake_home: Path, tmp_path: Path, kind: str) -> None:
    target = tmp_path / f"target-{kind}"
    if kind == "destination":
        target.mkdir()
        (fake_home / "pets").mkdir()
        (fake_home / "pets/liang-no-henshin").symlink_to(target, target_is_directory=True)
        code = error_code(lambda: installer.install(codex_home=fake_home, payload=payload))
        assert code == "DESTINATION_SYMLINK"
    elif kind == "pets":
        target.mkdir()
        (fake_home / "pets").symlink_to(target, target_is_directory=True)
        code = error_code(lambda: installer.install(codex_home=fake_home, payload=payload))
        assert code == "PETS_PATH_SYMLINK"
    elif kind == "config":
        target.write_text("# target\n")
        (fake_home / "config.toml").symlink_to(target)
        code = error_code(lambda: installer.install(codex_home=fake_home, payload=payload))
        assert code == "CONFIG_SYMLINK"
    else:
        link = tmp_path / "payload-link"
        link.symlink_to(payload, target_is_directory=True)
        code = error_code(lambda: installer.install(codex_home=fake_home, payload=link))
        assert code == "PAYLOAD_SYMLINK"


def test_manifest_path_escape_is_rejected(payload: Path, fake_home: Path, tmp_path: Path) -> None:
    broken = shutil.copytree(payload, tmp_path / "path-escape")
    manifest_path = broken / installer.MANIFEST_NAME
    manifest = json.loads(manifest_path.read_text())
    manifest["files"]["../escape"] = "0" * 64
    manifest_path.write_text(json.dumps(manifest) + "\n")
    assert error_code(lambda: installer.install(codex_home=fake_home, payload=broken)) == "MANIFEST_PATH_ESCAPE"


def test_other_pet_is_never_touched(payload: Path, fake_home: Path) -> None:
    other = make_other_pet(fake_home)
    before = snapshot(other)
    installer.install(codex_home=fake_home, payload=payload)
    installer.uninstall(codex_home=fake_home)
    assert snapshot(other) == before


def test_dry_run_clean_install_has_zero_writes(payload: Path, fake_home: Path) -> None:
    before = snapshot(fake_home)
    result = installer.install(codex_home=fake_home, payload=payload, dry_run=True)
    assert result.action == "INSTALL"
    assert result.config_mutation == "SELECT_PET"
    assert result.changed is False
    assert snapshot(fake_home) == before


def test_dry_run_reports_refuse_for_unknown_destination(payload: Path, fake_home: Path) -> None:
    destination = fake_home / "pets/liang-no-henshin"
    destination.mkdir(parents=True)
    (destination / "mine").write_text("mine")
    before = snapshot(fake_home)
    result = installer.install(codex_home=fake_home, payload=payload, dry_run=True)
    assert result.action == "REFUSE"
    assert snapshot(fake_home) == before


def test_real_home_mutation_gate_precedes_all_install_work(payload: Path) -> None:
    assert error_code(lambda: installer.install(codex_home=installer.REAL_CODEX_HOME, payload=payload)) == "REAL_HOME_INSTALL_NOT_AUTHORIZED"


def test_duplicate_selection_is_rejected_without_reformatting(payload: Path, fake_home: Path) -> None:
    config = fake_home / "config.toml"
    config.write_text('[desktop]\nselected-avatar-id = "a"\nselected-avatar-id = "b"\n')
    before = config.read_bytes()
    assert error_code(lambda: installer.install(codex_home=fake_home, payload=payload)) == "INVALID_CONFIG"
    assert config.read_bytes() == before


def test_cli_dry_run_reports_machine_readable_plan(payload: Path, fake_home: Path) -> None:
    completed = subprocess.run(
        [sys.executable, str(ROOT / "tools/install_liang_pet.py"), "--codex-home", str(fake_home), "--payload", str(payload), "--dry-run"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    output = json.loads(completed.stdout)
    assert output["ok"] is True
    assert output["result"]["action"] == "INSTALL"
    assert output["result"]["pet_id"] == installer.PET_ID
    assert snapshot(fake_home) == {}
