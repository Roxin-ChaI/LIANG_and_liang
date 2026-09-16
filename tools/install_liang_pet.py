#!/usr/bin/env python3
"""Atomic, ownership-aware installer for the Liang no Henshin Pet payload."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import stat
import tempfile
import tomllib
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from PIL import Image


PET_DIRECTORY = "liang-no-henshin"
PET_ID = "custom:liang-no-henshin"
MANIFEST_NAME = ".liang-install-manifest.json"
STATE_NAME = ".liang-install-state.json"
REAL_CODEX_HOME = (Path.home() / ".codex").resolve()
FaultHook = Callable[[str, dict[str, Path]], None]


class InstallerError(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class PayloadInfo:
    root: Path
    manifest: dict[str, Any]
    manifest_hash: str


@dataclass(frozen=True)
class InstallResult:
    action: str
    destination: str
    pet_id: str
    config_mutation: str
    changed: bool


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _safe_relative(value: object) -> bool:
    if not isinstance(value, str) or not value or "\0" in value or "\\" in value:
        return False
    candidate = Path(value)
    return not candidate.is_absolute() and all(part not in {"", ".", ".."} for part in value.split("/"))


def _inside(root: Path, candidate: Path) -> bool:
    try:
        candidate.relative_to(root)
        return candidate != root
    except ValueError:
        return False


def _load_json(path: Path, code: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as error:
        raise InstallerError(code, f"invalid {path.name}") from error
    if not isinstance(value, dict):
        raise InstallerError(code, f"{path.name} must contain an object")
    return value


def _walk_regular_files(root: Path, *, allowed_extra: set[str] | None = None) -> set[str]:
    files: set[str] = set()
    for entry in root.rglob("*"):
        details = entry.lstat()
        relative = entry.relative_to(root).as_posix()
        if stat.S_ISLNK(details.st_mode):
            raise InstallerError("PAYLOAD_SYMLINK", f"symlink rejected: {relative}")
        if entry.is_file():
            files.add(relative)
        elif not entry.is_dir():
            raise InstallerError("PAYLOAD_SPECIAL_FILE", f"special file rejected: {relative}")
    return files - (allowed_extra or set())


def _verify_manifest_files(root: Path, manifest: dict[str, Any], *, installed: bool = False) -> None:
    if set(manifest) != {"formatVersion", "petId", "files"} or manifest.get("formatVersion") != 1 or manifest.get("petId") != PET_ID:
        raise InstallerError("INVALID_MANIFEST", "install manifest identity is invalid")
    files = manifest.get("files")
    if not isinstance(files, dict):
        raise InstallerError("INVALID_MANIFEST", "install manifest files must be an object")
    for relative, expected_hash in files.items():
        if not _safe_relative(relative) or not isinstance(expected_hash, str) or not re.fullmatch(r"[0-9a-f]{64}", expected_hash):
            raise InstallerError("MANIFEST_PATH_ESCAPE", "manifest contains an unsafe path or hash")
    listed = set(files)
    actual = _walk_regular_files(root, allowed_extra={MANIFEST_NAME, STATE_NAME} if installed else {MANIFEST_NAME})
    if listed != actual:
        raise InstallerError("MANIFEST_FILE_SET_MISMATCH", "payload file set does not match manifest")
    for relative, expected_hash in files.items():
        candidate = (root / relative).resolve()
        if not _inside(root, candidate):
            raise InstallerError("MANIFEST_PATH_ESCAPE", "manifest path escapes payload root")
        if sha256_file(candidate) != expected_hash:
            raise InstallerError("PAYLOAD_HASH_MISMATCH", f"hash mismatch: {relative}")


def validate_payload(payload: Path) -> PayloadInfo:
    root_input = Path(payload)
    if not root_input.exists():
        raise InstallerError("PAYLOAD_NOT_FOUND", "payload does not exist")
    input_stat = root_input.lstat()
    if stat.S_ISLNK(input_stat.st_mode) or not root_input.is_dir():
        raise InstallerError("PAYLOAD_SYMLINK", "payload root must be a real directory")
    root = root_input.resolve()
    manifest_path = root / MANIFEST_NAME
    manifest = _load_json(manifest_path, "INVALID_MANIFEST")
    _verify_manifest_files(root, manifest)

    pet = _load_json(root / "pet.json", "INVALID_PET_JSON")
    if pet.get("id") != PET_DIRECTORY or pet.get("displayName") != "Liang no Henshin" or pet.get("spriteVersionNumber") != 2 or pet.get("spritesheetPath") != "spritesheet.webp":
        raise InstallerError("INVALID_PET_JSON", "native Pet metadata mismatch")
    runtime = _load_json(root / "liang-runtime.json", "INVALID_RUNTIME_SIDECAR")
    if runtime.get("schemaVersion") != 1 or runtime.get("initialForm") != "gu":
        raise InstallerError("INVALID_RUNTIME_SIDECAR", "runtime sidecar identity mismatch")

    atlas_paths = [
        root / "spritesheet.webp",
        root / "forms/gu/spritesheet.webp",
        root / "forms/feng/spritesheet.webp",
    ]
    for atlas in atlas_paths:
        with Image.open(atlas) as image:
            if image.size != (1536, 2288) or image.mode != "RGBA":
                raise InstallerError("INVALID_ATLAS", f"invalid v2 atlas: {atlas.name}")
    if sha256_file(atlas_paths[0]) != sha256_file(atlas_paths[1]):
        raise InstallerError("INVALID_FALLBACK", "native fallback is not Gu")

    expected = {"gu_to_feng": 10, "feng_to_gu": 8}
    transitions = runtime.get("transitions")
    if not isinstance(transitions, dict) or set(transitions) != set(expected):
        raise InstallerError("INVALID_RUNTIME_SIDECAR", "transition set mismatch")
    for name, count in expected.items():
        transition = transitions[name]
        frames = transition.get("frames") if isinstance(transition, dict) else None
        layout = transition.get("layout") if isinstance(transition, dict) else None
        if not isinstance(frames, list) or len(frames) != count or transition.get("frameDurationMs") != 140 or not isinstance(layout, dict):
            raise InstallerError("INVALID_RUNTIME_SIDECAR", f"{name} metadata mismatch")
        for relative in frames:
            if not _safe_relative(relative):
                raise InstallerError("MANIFEST_PATH_ESCAPE", "unsafe transition path")
            frame = (root / relative).resolve()
            if not _inside(root, frame):
                raise InstallerError("MANIFEST_PATH_ESCAPE", "transition path escapes payload")
            with Image.open(frame) as image:
                if image.mode != "RGBA" or image.size != (layout.get("canvasWidth"), layout.get("canvasHeight")):
                    raise InstallerError("INVALID_TRANSITION", f"{name} frame geometry mismatch")
    return PayloadInfo(root=root, manifest=manifest, manifest_hash=sha256_file(manifest_path))


def _read_config(config: Path) -> tuple[str, str | None]:
    if not config.exists():
        return "", None
    if config.is_symlink() or not config.is_file():
        raise InstallerError("CONFIG_SYMLINK", "config.toml must be a regular file")
    text = config.read_text()
    try:
        parsed = tomllib.loads(text)
    except tomllib.TOMLDecodeError as error:
        raise InstallerError("INVALID_CONFIG", "config.toml is not valid TOML") from error
    desktop = parsed.get("desktop", {})
    previous = desktop.get("selected-avatar-id") if isinstance(desktop, dict) else None
    if previous is not None and not isinstance(previous, str):
        raise InstallerError("INVALID_CONFIG", "desktop selected-avatar-id must be a string")
    return text, previous


_SECTION = re.compile(r"^\s*\[([^]]+)]\s*(?:#.*)?$")
_SELECTION = re.compile(r"^(\s*)selected-avatar-id(\s*=\s*)([\"'])(.*?)(\3)(\s*(?:#.*)?)(\r?\n?)$")


def patch_config(text: str, selection: str | None) -> str:
    lines = text.splitlines(keepends=True)
    desktop_start = None
    desktop_end = len(lines)
    for index, line in enumerate(lines):
        match = _SECTION.match(line.rstrip("\r\n"))
        if match and match.group(1).strip() == "desktop":
            desktop_start = index
            for end in range(index + 1, len(lines)):
                if _SECTION.match(lines[end].rstrip("\r\n")):
                    desktop_end = end
                    break
            break
    if desktop_start is None:
        if selection is None:
            return text
        prefix = text
        if prefix and not prefix.endswith(("\n", "\r")):
            prefix += "\n"
        if prefix and not prefix.endswith("\n\n"):
            prefix += "\n"
        return prefix + f'[desktop]\nselected-avatar-id = "{selection}"\n'

    selected_index = None
    selected_match = None
    for index in range(desktop_start + 1, desktop_end):
        match = _SELECTION.match(lines[index])
        if match:
            if selected_index is not None:
                raise InstallerError("INVALID_CONFIG", "duplicate desktop selected-avatar-id")
            selected_index, selected_match = index, match
    if selected_index is not None and selected_match is not None:
        if selection is None:
            del lines[selected_index]
        else:
            quote = selected_match.group(3)
            lines[selected_index] = (
                f"{selected_match.group(1)}selected-avatar-id{selected_match.group(2)}"
                f"{quote}{selection}{quote}{selected_match.group(6)}{selected_match.group(7)}"
            )
        return "".join(lines)
    if selection is None:
        return text
    newline = "\r\n" if any(line.endswith("\r\n") for line in lines) else "\n"
    lines.insert(desktop_end, f'selected-avatar-id = "{selection}"{newline}')
    return "".join(lines)


def _fsync_tree(root: Path) -> None:
    for file in root.rglob("*"):
        if file.is_file():
            with file.open("rb") as handle:
                os.fsync(handle.fileno())
    directory_fd = os.open(root, os.O_RDONLY)
    try:
        os.fsync(directory_fd)
    finally:
        os.close(directory_fd)


def _atomic_write(path: Path, content: str) -> None:
    descriptor, temporary_name = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise


def _restore_config(config: Path, existed: bool, content: str) -> None:
    if existed:
        _atomic_write(config, content)
    else:
        config.unlink(missing_ok=True)


def _assert_safe_home(codex_home: Path, *, mutating: bool) -> tuple[Path, Path, Path]:
    home = Path(codex_home)
    if not home.exists() or home.is_symlink() or not home.is_dir():
        raise InstallerError("INVALID_CODEX_HOME", "Codex home must be an existing real directory")
    resolved = home.resolve()
    if mutating and resolved == REAL_CODEX_HOME:
        raise InstallerError("REAL_HOME_INSTALL_NOT_AUTHORIZED", "real ~/.codex mutation is disabled in Phase 6")
    pets = resolved / "pets"
    config = resolved / "config.toml"
    if pets.exists() and (pets.is_symlink() or not pets.is_dir()):
        raise InstallerError("PETS_PATH_SYMLINK", "pets path must be a real directory")
    if config.exists() and (config.is_symlink() or not config.is_file()):
        raise InstallerError("CONFIG_SYMLINK", "config.toml must be a regular file")
    destination = pets / PET_DIRECTORY
    if destination.exists() and (destination.is_symlink() or not destination.is_dir()):
        raise InstallerError("DESTINATION_SYMLINK", "Liang destination must be a real directory")
    if not _inside(resolved, destination):
        raise InstallerError("DESTINATION_ESCAPE", "destination escapes Codex home")
    return resolved, pets, config


def _owned_state(destination: Path) -> dict[str, Any]:
    state_path = destination / STATE_NAME
    manifest_path = destination / MANIFEST_NAME
    if not state_path.is_file() or state_path.is_symlink() or not manifest_path.is_file() or manifest_path.is_symlink():
        raise InstallerError("REFUSE_UNOWNED_DESTINATION", "existing Liang directory is not installer-owned")
    state = _load_json(state_path, "REFUSE_UNOWNED_DESTINATION")
    manifest = _load_json(manifest_path, "REFUSE_UNOWNED_DESTINATION")
    if set(state) != {"formatVersion", "previousSelectedAvatarId", "installedPetId", "payloadManifestHash"} or state.get("formatVersion") != 1 or state.get("installedPetId") != PET_ID:
        raise InstallerError("REFUSE_UNOWNED_DESTINATION", "invalid Liang ownership state")
    if state.get("previousSelectedAvatarId") is not None and not isinstance(state.get("previousSelectedAvatarId"), str):
        raise InstallerError("REFUSE_UNOWNED_DESTINATION", "invalid previous avatar state")
    if state.get("payloadManifestHash") != sha256_file(manifest_path):
        raise InstallerError("REFUSE_UNOWNED_DESTINATION", "owned manifest hash mismatch")
    _verify_manifest_files(destination.resolve(), manifest, installed=True)
    return state


def _result(action: str, destination: Path, config_mutation: str, changed: bool) -> InstallResult:
    return InstallResult(action, str(destination), PET_ID, config_mutation, changed)


def install(
    *,
    codex_home: Path,
    payload: Path,
    dry_run: bool = False,
    fault_hook: FaultHook | None = None,
) -> InstallResult:
    _, pets, config = _assert_safe_home(codex_home, mutating=not dry_run)
    info = validate_payload(payload)
    destination = pets / PET_DIRECTORY
    config_before, selected_before = _read_config(config)
    try:
        owned = _owned_state(destination) if destination.exists() else None
    except InstallerError as error:
        if dry_run and error.code == "REFUSE_UNOWNED_DESTINATION":
            return _result("REFUSE", destination, "NONE", False)
        raise
    action = "INSTALL" if owned is None else "ALREADY_CURRENT" if owned["payloadManifestHash"] == info.manifest_hash else "UPDATE"
    desired_config = patch_config(config_before, PET_ID)
    config_mutation = "NONE" if desired_config == config_before else "SELECT_PET"
    if dry_run:
        return _result(action, destination, config_mutation, False)
    if action == "ALREADY_CURRENT":
        if desired_config != config_before:
            _atomic_write(config, desired_config)
        return _result(action, destination, config_mutation, desired_config != config_before)

    pets_created = not pets.exists()
    pets.mkdir(parents=False, exist_ok=True)
    staging = Path(tempfile.mkdtemp(dir=pets, prefix=f".{PET_DIRECTORY}.staging-"))
    staging.rmdir()
    backup = pets / f".{PET_DIRECTORY}.backup-{uuid.uuid4().hex}"
    config_existed = config.exists()
    previous_selection = owned["previousSelectedAvatarId"] if owned is not None else selected_before
    paths = {"staging": staging, "backup": backup, "destination": destination, "config": config}
    old_moved = False
    new_moved = False
    try:
        shutil.copytree(info.root, staging, symlinks=False)
        if fault_hook:
            fault_hook("after-copy", paths)
        _verify_manifest_files(staging.resolve(), _load_json(staging / MANIFEST_NAME, "INVALID_MANIFEST"))
        state = {
            "formatVersion": 1,
            "previousSelectedAvatarId": previous_selection,
            "installedPetId": PET_ID,
            "payloadManifestHash": info.manifest_hash,
        }
        (staging / STATE_NAME).write_text(json.dumps(state, indent=2) + "\n")
        _fsync_tree(staging)
        if destination.exists():
            os.replace(destination, backup)
            old_moved = True
        if fault_hook:
            fault_hook("before-destination-rename", paths)
        os.replace(staging, destination)
        new_moved = True
        if fault_hook:
            fault_hook("before-config-write", paths)
        _atomic_write(config, desired_config)
        installed_state = _owned_state(destination)
        if installed_state["payloadManifestHash"] != info.manifest_hash:
            raise InstallerError("INSTALL_VERIFY_FAILED", "installed payload verification failed")
        if backup.exists():
            shutil.rmtree(backup)
        return _result(action, destination, config_mutation, True)
    except Exception:
        if new_moved and destination.exists():
            shutil.rmtree(destination)
        if old_moved and backup.exists():
            os.replace(backup, destination)
        if staging.exists():
            shutil.rmtree(staging)
        _restore_config(config, config_existed, config_before)
        if pets_created and pets.exists() and not any(pets.iterdir()):
            pets.rmdir()
        raise


def uninstall(
    *,
    codex_home: Path,
    dry_run: bool = False,
    fault_hook: FaultHook | None = None,
) -> InstallResult:
    _, pets, config = _assert_safe_home(codex_home, mutating=not dry_run)
    destination = pets / PET_DIRECTORY
    if not destination.exists():
        raise InstallerError("NOT_INSTALLED", "Liang Pet is not installed")
    state = _owned_state(destination)
    config_before, _ = _read_config(config)
    desired_config = patch_config(config_before, state["previousSelectedAvatarId"])
    config_mutation = "RESTORE_PREVIOUS" if state["previousSelectedAvatarId"] is not None else "REMOVE_SELECTION"
    if dry_run:
        return _result("UNINSTALL", destination, config_mutation, False)
    backup = pets / f".{PET_DIRECTORY}.uninstall-{uuid.uuid4().hex}"
    config_existed = config.exists()
    try:
        os.replace(destination, backup)
        if fault_hook:
            fault_hook("before-config-write", {"backup": backup, "destination": destination, "config": config})
        _atomic_write(config, desired_config)
        shutil.rmtree(backup)
        return _result("UNINSTALL", destination, config_mutation, True)
    except Exception:
        if backup.exists() and not destination.exists():
            os.replace(backup, destination)
        _restore_config(config, config_existed, config_before)
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--codex-home", type=Path, default=REAL_CODEX_HOME)
    parser.add_argument("--payload", type=Path)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--dry-run", action="store_true")
    modes.add_argument("--install", action="store_true")
    modes.add_argument("--uninstall", action="store_true")
    args = parser.parse_args()
    try:
        if args.uninstall:
            result = uninstall(codex_home=args.codex_home)
        else:
            if args.payload is None:
                parser.error("--payload is required for install or dry-run")
            result = install(codex_home=args.codex_home, payload=args.payload, dry_run=args.dry_run)
    except InstallerError as error:
        print(json.dumps({"ok": False, "error": {"code": error.code, "message": str(error)}}))
        return 1
    print(json.dumps({"ok": True, "result": result.__dict__}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
