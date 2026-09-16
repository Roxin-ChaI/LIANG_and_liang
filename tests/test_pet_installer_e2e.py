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


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def tree_snapshot(root: Path) -> dict[str, tuple[str, str]]:
    result: dict[str, tuple[str, str]] = {}
    if not root.exists():
        return result
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root).as_posix()
        if path.is_symlink():
            result[relative] = ("link", os.readlink(path))
        elif path.is_dir():
            result[relative] = ("dir", "")
        else:
            result[relative] = ("file", sha256(path))
    return result


@pytest.fixture(scope="session")
def built_payload(tmp_path_factory: pytest.TempPathFactory) -> Path:
    output = tmp_path_factory.mktemp("liang-e2e-payload") / "payload"
    subprocess.run(
        ["node", str(ROOT / "installer/pet-payload.mjs"), "--output", str(output)],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return output / installer.PET_DIRECTORY


@pytest.fixture
def complete_home(tmp_path: Path) -> Path:
    home = tmp_path / ".codex"
    other = home / "pets/existing-test-pet"
    other.mkdir(parents=True)
    (other / "pet.json").write_text('{"id":"existing-test-pet"}\n')
    (home / "config.toml").write_text(
        "# retained heading\n"
        "[desktop]\n"
        'selected-avatar-id = "custom:existing-test-pet" # retained choice\n'
        "reduce-motion = true\n\n"
        "[features]\n"
        "experimental = false\n"
    )
    return home


def revised_payload(source: Path, destination: Path, revision: str) -> Path:
    shutil.copytree(source, destination)
    pet_path = destination / "pet.json"
    pet = json.loads(pet_path.read_text())
    pet["payloadRevision"] = revision
    pet_path.write_text(json.dumps(pet, indent=2, sort_keys=True) + "\n")
    manifest_path = destination / installer.MANIFEST_NAME
    manifest = json.loads(manifest_path.read_text())
    manifest["files"]["pet.json"] = sha256(pet_path)
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    return destination


def test_case_a_clean_install_is_complete_and_scoped(built_payload: Path, complete_home: Path) -> None:
    other_before = tree_snapshot(complete_home / "pets/existing-test-pet")
    result = installer.install(codex_home=complete_home, payload=built_payload)
    destination = complete_home / "pets/liang-no-henshin"
    assert result.action == "INSTALL"
    assert destination.is_dir()
    installer._owned_state(destination)
    assert tree_snapshot(complete_home / "pets/existing-test-pet") == other_before
    assert 'selected-avatar-id = "custom:liang-no-henshin"' in (complete_home / "config.toml").read_text()


def test_case_b_user_config_round_trip_is_minimal(built_payload: Path, complete_home: Path) -> None:
    before = (complete_home / "config.toml").read_text()
    installer.install(codex_home=complete_home, payload=built_payload)
    installed = (complete_home / "config.toml").read_text()
    assert installed.replace("custom:liang-no-henshin", "custom:existing-test-pet") == before
    installer.uninstall(codex_home=complete_home)
    assert (complete_home / "config.toml").read_text() == before


def test_case_c_upgrade_is_atomic_and_keeps_preinstall_selection(
    built_payload: Path, complete_home: Path, tmp_path: Path
) -> None:
    old = revised_payload(built_payload, tmp_path / "older", "older")
    installer.install(codex_home=complete_home, payload=old)
    old_state = json.loads((complete_home / f"pets/{installer.PET_DIRECTORY}/{installer.STATE_NAME}").read_text())
    assert old_state["previousSelectedAvatarId"] == "custom:existing-test-pet"

    result = installer.install(codex_home=complete_home, payload=built_payload)
    destination = complete_home / "pets/liang-no-henshin"
    state = installer._owned_state(destination)
    assert result.action == "UPDATE"
    assert state["payloadManifestHash"] == sha256(built_payload / installer.MANIFEST_NAME)
    assert state["previousSelectedAvatarId"] == "custom:existing-test-pet"
    assert not list((complete_home / "pets").glob(".liang-no-henshin.*"))


def test_case_d_unknown_pet_refuses_with_zero_destructive_writes(
    built_payload: Path, complete_home: Path
) -> None:
    unknown = complete_home / "pets/liang-no-henshin"
    unknown.mkdir()
    (unknown / "user-owned.txt").write_text("keep\n")
    before = tree_snapshot(complete_home)
    with pytest.raises(installer.InstallerError, match="not installer-owned") as caught:
        installer.install(codex_home=complete_home, payload=built_payload)
    assert caught.value.code == "REFUSE_UNOWNED_DESTINATION"
    assert tree_snapshot(complete_home) == before


def test_case_e_update_config_failure_restores_pet_and_config(
    built_payload: Path, complete_home: Path, tmp_path: Path
) -> None:
    old = revised_payload(built_payload, tmp_path / "older", "older")
    installer.install(codex_home=complete_home, payload=old)
    before = tree_snapshot(complete_home)

    def fail(stage: str, paths: dict[str, Path]) -> None:
        if stage == "before-config-write":
            raise OSError("injected config failure")

    with pytest.raises(OSError, match="injected config failure"):
        installer.install(codex_home=complete_home, payload=built_payload, fault_hook=fail)
    assert tree_snapshot(complete_home) == before


def test_case_f_install_then_uninstall_restores_complete_home(
    built_payload: Path, complete_home: Path
) -> None:
    before = tree_snapshot(complete_home)
    installer.install(codex_home=complete_home, payload=built_payload)
    installer.uninstall(codex_home=complete_home)
    assert tree_snapshot(complete_home) == before


def test_cli_dry_run_reports_all_install_plan_actions_without_writes(
    built_payload: Path, complete_home: Path, tmp_path: Path
) -> None:
    def cli(home: Path, payload: Path) -> dict:
        before = tree_snapshot(home)
        completed = subprocess.run(
            [
                sys.executable,
                str(ROOT / "tools/install_liang_pet.py"),
                "--codex-home",
                str(home),
                "--payload",
                str(payload),
                "--dry-run",
            ],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        assert tree_snapshot(home) == before
        return json.loads(completed.stdout)["result"]

    assert cli(complete_home, built_payload)["action"] == "INSTALL"
    installer.install(codex_home=complete_home, payload=built_payload)
    assert cli(complete_home, built_payload)["action"] == "ALREADY_CURRENT"
    changed = revised_payload(built_payload, tmp_path / "newer", "newer")
    assert cli(complete_home, changed)["action"] == "UPDATE"

    refused_home = tmp_path / "refused/.codex"
    (refused_home / "pets/liang-no-henshin").mkdir(parents=True)
    (refused_home / "pets/liang-no-henshin/mine").write_text("mine")
    assert cli(refused_home, built_payload)["action"] == "REFUSE"


def test_real_home_install_and_uninstall_are_hard_blocked(built_payload: Path) -> None:
    with pytest.raises(installer.InstallerError) as install_error:
        installer.install(codex_home=installer.REAL_CODEX_HOME, payload=built_payload)
    assert install_error.value.code == "REAL_HOME_INSTALL_NOT_AUTHORIZED"
    with pytest.raises(installer.InstallerError) as uninstall_error:
        installer.uninstall(codex_home=installer.REAL_CODEX_HOME)
    assert uninstall_error.value.code == "REAL_HOME_INSTALL_NOT_AUTHORIZED"
