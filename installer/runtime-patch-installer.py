#!/usr/bin/env python3
"""Fingerprint-gated, atomic runtime patch installer for temporary App copies."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import plistlib
import shutil
import stat
import struct
import subprocess
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable, Iterator


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SPEC = ROOT / "runtime-patch/builds/9275/patch-spec.json"
PATCH_RECIPE = ROOT / "runtime-patch/builds/9275/build-patch.mjs"
REAL_APP = Path("/Applications/ChatGPT.app").resolve()
BACKUP_NAME = "app.asar.liang-original"
STATE_NAME = ".liang-runtime-patch-state.json"
CONTEXT_NAME = ".liang-build-context.json"
REPORT_NAME = "patch-report.json"
FaultHook = Callable[[str, dict[str, Path]], None]


class RuntimePatchError(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class PatchResult:
    action: str
    version: str
    build: str
    original_asar_sha256: str
    current_asar_sha256: str
    patched_asar_sha256: str | None
    changed: bool


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _fail(code: str, message: str) -> None:
    raise RuntimePatchError(code, message)


def _safe_segment(value: str) -> bool:
    return bool(value) and value not in {".", ".."} and "/" not in value and "\\" not in value and "\0" not in value


def _read_asar_header(archive: Path) -> tuple[dict[str, Any], int]:
    try:
        with archive.open("rb") as handle:
            prefix = handle.read(8)
            if len(prefix) != 8:
                _fail("INVALID_ASAR", "ASAR prefix is truncated")
            pickle_size, header_size = struct.unpack("<II", prefix)
            if pickle_size != 4 or header_size < 12 or header_size > 64 * 1024 * 1024:
                _fail("INVALID_ASAR", "ASAR header size is invalid")
            buffer = handle.read(header_size)
            if len(buffer) != header_size:
                _fail("INVALID_ASAR", "ASAR header is truncated")
            payload_size, json_size = struct.unpack("<II", buffer[:8])
            if payload_size != header_size - 4 or json_size > header_size - 8:
                _fail("INVALID_ASAR", "ASAR pickle header is invalid")
            header = json.loads(buffer[8 : 8 + json_size].decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, struct.error) as error:
        raise RuntimePatchError("INVALID_ASAR", "unable to parse app.asar") from error
    if not isinstance(header, dict) or not isinstance(header.get("files"), dict):
        _fail("INVALID_ASAR", "ASAR file tree is invalid")
    return header, 8 + header_size


def _walk_asar(
    node: dict[str, Any], prefix: tuple[str, ...] = ()
) -> Iterator[tuple[tuple[str, ...], dict[str, Any]]]:
    files = node.get("files")
    if not isinstance(files, dict):
        _fail("INVALID_ASAR", "ASAR directory has no file map")
    for name, entry in files.items():
        if not isinstance(name, str) or not _safe_segment(name) or not isinstance(entry, dict):
            _fail("INVALID_ASAR", "ASAR contains an unsafe entry")
        parts = (*prefix, name)
        if "files" in entry:
            yield from _walk_asar(entry, parts)
        else:
            yield parts, entry


def _packed_entry(header: dict[str, Any], relative: str) -> dict[str, Any]:
    entry: dict[str, Any] = header
    for part in relative.split("/"):
        if not _safe_segment(part):
            _fail("INVALID_ASAR", "unsafe ASAR path")
        entry = entry.get("files", {}).get(part)
        if not isinstance(entry, dict):
            _fail("UNSUPPORTED_BUILD", f"required ASAR entry is absent: {relative}")
    if entry.get("unpacked") or "link" in entry or not isinstance(entry.get("size"), int):
        _fail("UNSUPPORTED_BUILD", f"required ASAR entry is not packed: {relative}")
    try:
        int(entry["offset"])
    except (KeyError, TypeError, ValueError) as error:
        raise RuntimePatchError("INVALID_ASAR", "invalid packed ASAR offset") from error
    return entry


def read_asar_file(archive: Path, relative: str) -> bytes:
    header, data_offset = _read_asar_header(archive)
    entry = _packed_entry(header, relative)
    with archive.open("rb") as handle:
        handle.seek(data_offset + int(entry["offset"]))
        data = handle.read(entry["size"])
    if len(data) != entry["size"]:
        _fail("INVALID_ASAR", f"truncated ASAR entry: {relative}")
    return data


def extract_asar(archive: Path, destination: Path) -> dict[str, Any]:
    header, data_offset = _read_asar_header(archive)
    destination.mkdir(parents=True, exist_ok=False)
    with archive.open("rb") as handle:
        for parts, entry in _walk_asar(header):
            if entry.get("unpacked") or "link" in entry:
                continue
            if not isinstance(entry.get("size"), int):
                _fail("INVALID_ASAR", "ASAR packed entry size is invalid")
            try:
                offset = int(entry["offset"])
            except (KeyError, TypeError, ValueError) as error:
                raise RuntimePatchError("INVALID_ASAR", "ASAR packed entry offset is invalid") from error
            target = destination.joinpath(*parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            handle.seek(data_offset + offset)
            data = handle.read(entry["size"])
            if len(data) != entry["size"]:
                _fail("INVALID_ASAR", "ASAR packed entry is truncated")
            target.write_bytes(data)
            if entry.get("executable"):
                target.chmod(target.stat().st_mode | stat.S_IXUSR)
    return header


def _integrity(data: bytes, block_size: int = 4 * 1024 * 1024) -> dict[str, Any]:
    return {
        "algorithm": "SHA256",
        "hash": hashlib.sha256(data).hexdigest(),
        "blockSize": block_size,
        "blocks": [hashlib.sha256(data[index : index + block_size]).hexdigest() for index in range(0, len(data), block_size)],
    }


def _header_pickle(header: dict[str, Any]) -> bytes:
    encoded = json.dumps(header, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    aligned = (4 + len(encoded) + 1 + 3) & ~3
    header_size = 4 + aligned
    padding = aligned - (4 + len(encoded) + 1)
    return struct.pack("<II", 4, header_size) + struct.pack("<II", aligned, len(encoded)) + encoded + b"\0" + (b"\0" * padding)


def pack_asar(tree: Path, header_template: dict[str, Any], output: Path) -> None:
    header = copy.deepcopy(header_template)
    packed: list[tuple[Path, bytes]] = []
    offset = 0
    for parts, entry in _walk_asar(header):
        if entry.get("unpacked") or "link" in entry:
            continue
        source = tree.joinpath(*parts)
        if source.is_symlink() or not source.is_file():
            _fail("REPACK_FAILED", f"packed file is missing: {'/'.join(parts)}")
        data = source.read_bytes()
        entry["size"] = len(data)
        entry["offset"] = str(offset)
        block_size = entry.get("integrity", {}).get("blockSize", 4 * 1024 * 1024)
        entry["integrity"] = _integrity(data, block_size)
        offset += len(data)
        packed.append((source, data))
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("xb") as handle:
        handle.write(_header_pickle(header))
        for _, data in packed:
            handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())


def create_asar_from_directory(tree: Path, output: Path) -> None:
    def directory(path: Path) -> dict[str, Any]:
        files: dict[str, Any] = {}
        for child in sorted(path.iterdir(), key=lambda item: item.name):
            if child.is_symlink():
                _fail("INVALID_ASAR_SOURCE", "test ASAR source may not contain symlinks")
            files[child.name] = directory(child) if child.is_dir() else {"size": child.stat().st_size, "offset": "0"}
        return {"files": files}

    pack_asar(tree, directory(tree), output)


def _load_spec(spec_path: Path) -> dict[str, Any]:
    try:
        spec = json.loads(spec_path.read_text())
    except (OSError, json.JSONDecodeError) as error:
        raise RuntimePatchError("INVALID_PATCH_SPEC", "unable to load patch spec") from error
    if spec.get("formatVersion") != 1 or spec.get("target", {}).get("build") != "9275":
        _fail("INVALID_PATCH_SPEC", "patch spec is not Build 9275")
    return spec


def _app_paths(app: Path, *, mutating: bool) -> tuple[Path, Path, Path, Path, Path]:
    candidate = Path(app)
    if not candidate.exists() or candidate.is_symlink() or not candidate.is_dir():
        _fail("INVALID_APP", "App must be an existing real bundle directory")
    resolved = candidate.resolve()
    if mutating and resolved == REAL_APP:
        _fail("REAL_APP_MUTATION_NOT_AUTHORIZED", "real ChatGPT.app mutation is disabled in Phase 7")
    resources = resolved / "Contents/Resources"
    plist = resolved / "Contents/Info.plist"
    archive = resources / "app.asar"
    for path_value in (resources, plist, archive):
        if path_value.is_symlink() or not path_value.exists():
            _fail("INVALID_APP", "App bundle layout is invalid")
    if not resources.is_dir() or not plist.is_file() or not archive.is_file():
        _fail("INVALID_APP", "App bundle layout is invalid")
    return resolved, resources, plist, archive, resources / BACKUP_NAME


def _version_build(plist: Path) -> tuple[str, str]:
    try:
        with plist.open("rb") as handle:
            value = plistlib.load(handle)
        return str(value["CFBundleShortVersionString"]), str(value["CFBundleVersion"])
    except (OSError, plistlib.InvalidFileException, KeyError) as error:
        raise RuntimePatchError("INVALID_APP", "Info.plist is invalid") from error


def _verify_original(app: Path, spec: dict[str, Any]) -> tuple[str, str, str]:
    _, _, plist, archive, _ = _app_paths(app, mutating=False)
    version, build = _version_build(plist)
    observed = sha256_file(archive)
    target = spec["target"]
    if version != target["version"] or build != target["build"] or observed != target["appAsarSha256"]:
        _fail("UNSUPPORTED_BUILD", f"unsupported version/build/app.asar: {version}/{build}/{observed}")
    for name, chunk in spec["chunks"].items():
        if hashlib.sha256(read_asar_file(archive, chunk["path"])).hexdigest() != chunk["sha256"]:
            _fail("UNSUPPORTED_BUILD", f"chunk fingerprint mismatch: {name}")
    return version, build, observed


def _atomic_json(path: Path, value: dict[str, Any]) -> None:
    descriptor, temporary_name = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w") as handle:
            json.dump(value, handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise


def _load_state(state_path: Path) -> dict[str, Any]:
    if state_path.is_symlink() or not state_path.is_file():
        _fail("INVALID_PATCH_STATE", "patch state is missing or unsafe")
    try:
        state = json.loads(state_path.read_text())
    except (OSError, json.JSONDecodeError) as error:
        raise RuntimePatchError("INVALID_PATCH_STATE", "patch state is invalid") from error
    expected = {"formatVersion", "originalVersion", "originalBuild", "originalAsarSha256", "patchedAsarSha256", "patchSpecVersion"}
    if set(state) != expected or state.get("formatVersion") != 1 or any(not isinstance(state.get(key), str) for key in expected - {"formatVersion"}):
        _fail("INVALID_PATCH_STATE", "patch state identity is invalid")
    return state


def _owned_patched_state(resources: Path, archive: Path, backup: Path) -> dict[str, Any] | None:
    state_path = resources / STATE_NAME
    if not state_path.exists():
        if backup.exists():
            _fail("UNKNOWN_BACKUP_REFUSED", "backup exists without installer ownership state")
        return None
    state = _load_state(state_path)
    if backup.is_symlink() or not backup.is_file() or sha256_file(backup) != state["originalAsarSha256"]:
        _fail("CORRUPTED_BACKUP", "owned backup hash mismatch")
    if sha256_file(archive) != state["patchedAsarSha256"]:
        _fail("PATCH_STATE_MISMATCH", "current app.asar does not match patch state")
    return state


def _run_recipe(input_dir: Path, output_dir: Path, spec_path: Path, node: str) -> dict[str, Any]:
    completed = subprocess.run(
        [node, str(PATCH_RECIPE), "--input-dir", str(input_dir), "--output-dir", str(output_dir), "--spec", str(spec_path)],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        raise RuntimePatchError("PATCH_RECIPE_FAILED", completed.stderr.strip() or "runtime patch recipe failed")
    try:
        report = json.loads((output_dir / REPORT_NAME).read_text())
    except (OSError, json.JSONDecodeError) as error:
        raise RuntimePatchError("PATCH_RECIPE_FAILED", "patch report is missing") from error
    if report.get("status") != "PASS":
        _fail("PATCH_RECIPE_FAILED", "patch report did not pass")
    return report


def _verify_patched_archive(archive: Path, spec: dict[str, Any], report: dict[str, Any]) -> None:
    for name, chunk in spec["chunks"].items():
        actual = hashlib.sha256(read_asar_file(archive, chunk["path"])).hexdigest()
        if actual != report["targetHashes"][name]:
            _fail("PATCH_VERIFY_FAILED", f"patched chunk mismatch: {name}")
    if not all(item.get("status") == "PATCHED" and item.get("matchCount") == 1 for item in report.get("operations", [])):
        _fail("PATCH_VERIFY_FAILED", "patch operations are incomplete")


def inspect(app: Path, *, spec_path: Path = DEFAULT_SPEC) -> PatchResult:
    _, resources, plist, archive, backup = _app_paths(app, mutating=False)
    version, build = _version_build(plist)
    state = _owned_patched_state(resources, archive, backup)
    current = sha256_file(archive)
    if state is not None:
        return PatchResult("PATCHED", version, build, state["originalAsarSha256"], current, state["patchedAsarSha256"], False)
    spec = _load_spec(spec_path)
    version, build, original = _verify_original(app, spec)
    return PatchResult("SUPPORTED", version, build, original, original, None, False)


def patch_app(
    app: Path,
    *,
    spec_path: Path = DEFAULT_SPEC,
    dry_run: bool = False,
    node: str | None = None,
    fault_hook: FaultHook | None = None,
) -> PatchResult:
    _, resources, plist, archive, backup = _app_paths(app, mutating=not dry_run)
    spec = _load_spec(spec_path)
    version, build = _version_build(plist)
    state = _owned_patched_state(resources, archive, backup)
    if state is not None:
        return PatchResult("ALREADY_PATCHED", version, build, state["originalAsarSha256"], state["patchedAsarSha256"], state["patchedAsarSha256"], False)
    version, build, original_hash = _verify_original(app, spec)
    if dry_run:
        return PatchResult("PATCH", version, build, original_hash, original_hash, None, False)

    stage = Path(tempfile.mkdtemp(dir=resources, prefix=".liang-runtime-patch-"))
    input_dir, output_dir = stage / "extracted", stage / "patched"
    patched_archive = stage / "app.asar.patched"
    backup_temp = resources / f".{BACKUP_NAME}.{os.getpid()}.tmp"
    state_path = resources / STATE_NAME
    replaced = False
    backup_created = False
    paths = {"stage": stage, "archive": archive, "backup": backup, "state": state_path, "patched": patched_archive}
    try:
        header = extract_asar(archive, input_dir)
        (input_dir / CONTEXT_NAME).write_text(json.dumps({"version": version, "build": build, "appAsarSha256": original_hash}) + "\n")
        if fault_hook:
            fault_hook("after-extract", paths)
        report = _run_recipe(input_dir, output_dir, spec_path, node or shutil.which("node") or "node")
        if fault_hook:
            fault_hook("after-patch", paths)
        pack_asar(output_dir, header, patched_archive)
        _verify_patched_archive(patched_archive, spec, report)
        patched_hash = sha256_file(patched_archive)
        if fault_hook:
            fault_hook("after-repack", paths)
        shutil.copy2(archive, backup_temp)
        if sha256_file(backup_temp) != original_hash:
            _fail("BACKUP_VERIFY_FAILED", "backup copy hash mismatch")
        if fault_hook:
            fault_hook("before-backup-rename", paths)
        try:
            os.link(backup_temp, backup)
            backup_created = True
        except FileExistsError as error:
            raise RuntimePatchError("UNKNOWN_BACKUP_REFUSED", "refusing to overwrite an unexpected backup") from error
        backup_temp.unlink()
        if fault_hook:
            fault_hook("before-atomic-replace", paths)
        os.replace(patched_archive, archive)
        replaced = True
        if sha256_file(archive) != patched_hash:
            _fail("INSTALL_VERIFY_FAILED", "installed patched ASAR hash mismatch")
        if fault_hook:
            fault_hook("before-state-write", paths)
        patch_state = {
            "formatVersion": 1,
            "originalVersion": version,
            "originalBuild": build,
            "originalAsarSha256": original_hash,
            "patchedAsarSha256": patched_hash,
            "patchSpecVersion": spec["patchSpecVersion"],
        }
        _atomic_json(state_path, patch_state)
        _owned_patched_state(resources, archive, backup)
        return PatchResult("PATCHED", version, build, original_hash, patched_hash, patched_hash, True)
    except Exception:
        if replaced and backup.exists():
            restore_temp = resources / f".app.asar.rollback-{os.getpid()}.tmp"
            shutil.copy2(backup, restore_temp)
            os.replace(restore_temp, archive)
        state_path.unlink(missing_ok=True)
        if backup_created:
            backup.unlink(missing_ok=True)
        backup_temp.unlink(missing_ok=True)
        raise
    finally:
        shutil.rmtree(stage, ignore_errors=True)


def restore_app(
    app: Path,
    *,
    dry_run: bool = False,
    fault_hook: FaultHook | None = None,
) -> PatchResult:
    _, resources, plist, archive, backup = _app_paths(app, mutating=not dry_run)
    version, build = _version_build(plist)
    state = _owned_patched_state(resources, archive, backup)
    if state is None:
        _fail("NOT_PATCHED", "App has no owned runtime patch")
    if dry_run:
        return PatchResult("RESTORE", version, build, state["originalAsarSha256"], state["patchedAsarSha256"], state["patchedAsarSha256"], False)
    state_path = resources / STATE_NAME
    restore_temp = resources / f".app.asar.restore-{os.getpid()}.tmp"
    rollback_temp = resources / f".app.asar.patched-{os.getpid()}.tmp"
    replaced = False
    try:
        shutil.copy2(archive, rollback_temp)
        shutil.copy2(backup, restore_temp)
        if sha256_file(restore_temp) != state["originalAsarSha256"]:
            _fail("CORRUPTED_BACKUP", "restore copy hash mismatch")
        if fault_hook:
            fault_hook("before-restore-replace", {"archive": archive, "backup": backup, "state": state_path})
        os.replace(restore_temp, archive)
        replaced = True
        if sha256_file(archive) != state["originalAsarSha256"]:
            _fail("RESTORE_VERIFY_FAILED", "restored ASAR hash mismatch")
        if fault_hook:
            fault_hook("before-restore-cleanup", {"archive": archive, "backup": backup, "state": state_path})
        state_path.unlink()
        backup.unlink()
        rollback_temp.unlink(missing_ok=True)
        return PatchResult("RESTORED", version, build, state["originalAsarSha256"], state["originalAsarSha256"], state["patchedAsarSha256"], True)
    except Exception:
        if replaced and rollback_temp.exists():
            os.replace(rollback_temp, archive)
        restore_temp.unlink(missing_ok=True)
        rollback_temp.unlink(missing_ok=True)
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--app", required=True, type=Path)
    parser.add_argument("--spec", type=Path, default=DEFAULT_SPEC)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--dry-run", action="store_true")
    modes.add_argument("--patch", action="store_true")
    modes.add_argument("--restore", action="store_true")
    modes.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    try:
        if args.restore:
            result = restore_app(args.app)
        elif args.verify:
            result = inspect(args.app, spec_path=args.spec)
        else:
            result = patch_app(args.app, spec_path=args.spec, dry_run=args.dry_run)
    except RuntimePatchError as error:
        print(json.dumps({"ok": False, "error": {"code": error.code, "message": str(error)}}))
        return 1
    print(json.dumps({"ok": True, "result": asdict(result)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
