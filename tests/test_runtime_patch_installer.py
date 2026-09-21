from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import plistlib
import shutil
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "installer/runtime-patch-installer.py"
SPEC = importlib.util.spec_from_file_location("runtime_patch_installer", MODULE_PATH)
assert SPEC and SPEC.loader
runtime = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = runtime
SPEC.loader.exec_module(runtime)


SOURCES = {
    "main": 'const n={Mt(){return Promise.resolve({})}};const x={loadAvatar(e){return n.Mt({appServerClient:this.executionHostRegistry.get(),avatarId:e,preferWsl:!!process.env.WSL_DISTRO_NAME})}};H=new wle(V,d,S),ee=o4e;\n',
    "preload": 'e.contextBridge.exposeInMainWorld(`electronBridge`,R),typeof window<`u`;\n',
    "loader": "export const loader=true;\n",
    "core": "const Xlo={};function Ulo(e,t){let n=Xlo[e];return n}function q(){if(x){a=null;return}i=n,e.style.backgroundPosition=Glo(Wlo(r,i),d),o()}const native={loopStartIndex:r.length};\n",
    "overlay": "function kd(){return 1}function Nd(e){let t=(0,of.c)(43),{selectedAvatar:n,selectedAvatarId:r}=e;return t}const source={source:Kr(c)};function Nu(e){let _;_=(0,Lu.jsx)($l,{...n,layout:c}),t[10]=n,t[11]=c,t[12]=_;return _}const kr=Ai(`relative h-screen w-screen bg-transparent`,`overflow-hidden`);const task={state:vt.mascotState};const normal={style:{...Xa(rn.width),height:rn.height}};\n",
    "mascot": "export const mascot=true;\n",
    "settings": "export const settings=true;\n",
}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def snapshot(root: Path) -> dict[str, tuple[str, str]]:
    result = {}
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root).as_posix()
        if path.is_symlink():
            result[relative] = ("link", os.readlink(path))
        elif path.is_dir():
            result[relative] = ("dir", "")
        else:
            result[relative] = ("file", digest(path))
    return result


def make_app(tmp_path: Path, *, version: str = "26.908.70816", build: str = "9275") -> tuple[Path, Path]:
    app = tmp_path / "ChatGPT.app"
    resources = app / "Contents/Resources"
    source = tmp_path / "asar-source"
    resources.mkdir(parents=True)
    source.mkdir()
    production = json.loads(runtime.DEFAULT_SPEC.read_text())
    for name, chunk in production["chunks"].items():
        target = source / chunk["path"]
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(SOURCES[name])
        chunk["sha256"] = hashlib.sha256(SOURCES[name].encode()).hexdigest()
    runtime.create_asar_from_directory(source, resources / "app.asar")
    production["target"]["version"] = version
    production["target"]["build"] = build
    production["target"]["appAsarSha256"] = digest(resources / "app.asar")
    spec_path = tmp_path / "patch-spec.json"
    spec_path.write_text(json.dumps(production, indent=2) + "\n")
    with (app / "Contents/Info.plist").open("wb") as handle:
        plistlib.dump({"CFBundleShortVersionString": version, "CFBundleVersion": build, "CFBundleIdentifier": "com.openai.chat"}, handle)
    return app, spec_path


def code(callable_) -> str:
    with pytest.raises(runtime.RuntimePatchError) as caught:
        callable_()
    return caught.value.code


def test_supported_build_verifies(tmp_path: Path) -> None:
    app, spec = make_app(tmp_path)
    assert runtime.inspect(app, spec_path=spec).action == "SUPPORTED"


@pytest.mark.parametrize(
    ("version", "build"),
    [("26.908.70817", "9275"), ("26.908.70816", "9276")],
)
def test_unsupported_version_or_build_is_rejected(tmp_path: Path, version: str, build: str) -> None:
    app, spec = make_app(tmp_path)
    plist = app / "Contents/Info.plist"
    with plist.open("wb") as handle:
        plistlib.dump({"CFBundleShortVersionString": version, "CFBundleVersion": build}, handle)
    assert code(lambda: runtime.patch_app(app, spec_path=spec)) == "UNSUPPORTED_BUILD"


def test_wrong_asar_hash_is_rejected(tmp_path: Path) -> None:
    app, spec = make_app(tmp_path)
    with (app / "Contents/Resources/app.asar").open("ab") as handle:
        handle.write(b"tamper")
    assert code(lambda: runtime.patch_app(app, spec_path=spec)) == "UNSUPPORTED_BUILD"


def test_patch_success_and_installed_hash(tmp_path: Path) -> None:
    app, spec = make_app(tmp_path)
    result = runtime.patch_app(app, spec_path=spec)
    assert result.action == "PATCHED" and result.changed is True
    assert digest(app / "Contents/Resources/app.asar") == result.patched_asar_sha256
    assert runtime.inspect(app, spec_path=spec).action == "PATCHED"


def test_installed_archive_contains_every_reported_patched_chunk(tmp_path: Path) -> None:
    app, spec_path = make_app(tmp_path)
    runtime.patch_app(app, spec_path=spec_path)
    spec = json.loads(spec_path.read_text())
    archive = app / "Contents/Resources/app.asar"
    for chunk in spec["chunks"].values():
        assert runtime.read_asar_file(archive, chunk["path"])


def test_backup_file_is_created_with_original_bytes(tmp_path: Path) -> None:
    app, spec = make_app(tmp_path)
    archive = app / "Contents/Resources/app.asar"
    original = archive.read_bytes()
    runtime.patch_app(app, spec_path=spec)
    assert (app / f"Contents/Resources/{runtime.BACKUP_NAME}").read_bytes() == original


def test_backup_and_state_are_verified(tmp_path: Path) -> None:
    app, spec = make_app(tmp_path)
    original = digest(app / "Contents/Resources/app.asar")
    result = runtime.patch_app(app, spec_path=spec)
    resources = app / "Contents/Resources"
    state = json.loads((resources / runtime.STATE_NAME).read_text())
    assert digest(resources / runtime.BACKUP_NAME) == original
    assert state == {
        "formatVersion": 1,
        "originalVersion": "26.908.70816",
        "originalBuild": "9275",
        "originalAsarSha256": original,
        "patchedAsarSha256": result.patched_asar_sha256,
        "patchSpecVersion": "9275.1",
    }


def test_patch_state_contains_no_absolute_or_user_paths(tmp_path: Path) -> None:
    app, spec = make_app(tmp_path)
    runtime.patch_app(app, spec_path=spec)
    state_text = (app / f"Contents/Resources/{runtime.STATE_NAME}").read_text()
    assert str(tmp_path) not in state_text
    assert "/Users/" not in state_text


def test_idempotent_second_patch_is_noop(tmp_path: Path) -> None:
    app, spec = make_app(tmp_path)
    runtime.patch_app(app, spec_path=spec)
    before = snapshot(app)
    result = runtime.patch_app(app, spec_path=spec)
    assert result.action == "ALREADY_PATCHED" and result.changed is False
    assert snapshot(app) == before


def test_restore_returns_exact_original_hash(tmp_path: Path) -> None:
    app, spec = make_app(tmp_path)
    original = digest(app / "Contents/Resources/app.asar")
    runtime.patch_app(app, spec_path=spec)
    result = runtime.restore_app(app)
    resources = app / "Contents/Resources"
    assert result.action == "RESTORED"
    assert digest(resources / "app.asar") == original
    assert not (resources / runtime.BACKUP_NAME).exists()
    assert not (resources / runtime.STATE_NAME).exists()


def test_corrupted_backup_rejects_restore(tmp_path: Path) -> None:
    app, spec = make_app(tmp_path)
    runtime.patch_app(app, spec_path=spec)
    (app / f"Contents/Resources/{runtime.BACKUP_NAME}").write_bytes(b"bad")
    assert code(lambda: runtime.restore_app(app)) == "CORRUPTED_BACKUP"


def test_unknown_backup_is_refused(tmp_path: Path) -> None:
    app, spec = make_app(tmp_path)
    (app / f"Contents/Resources/{runtime.BACKUP_NAME}").write_bytes(b"unknown")
    before = snapshot(app)
    assert code(lambda: runtime.patch_app(app, spec_path=spec)) == "UNKNOWN_BACKUP_REFUSED"
    assert snapshot(app) == before


@pytest.mark.parametrize("failure_stage", ["after-extract", "after-patch", "after-repack"])
def test_extraction_patch_and_repack_failures_leave_original(tmp_path: Path, failure_stage: str) -> None:
    app, spec = make_app(tmp_path)
    before = snapshot(app)

    def fail(stage: str, paths: dict[str, Path]) -> None:
        if stage == failure_stage:
            raise OSError(f"injected {stage}")

    with pytest.raises(OSError, match="injected"):
        runtime.patch_app(app, spec_path=spec, fault_hook=fail)
    assert snapshot(app) == before


def test_atomic_replacement_failure_restores_original(tmp_path: Path) -> None:
    app, spec = make_app(tmp_path)
    before = snapshot(app)

    def fail(stage: str, paths: dict[str, Path]) -> None:
        if stage == "before-state-write":
            raise OSError("injected replacement failure")

    with pytest.raises(OSError, match="replacement failure"):
        runtime.patch_app(app, spec_path=spec, fault_hook=fail)
    assert snapshot(app) == before


def test_no_partial_state_after_failure(tmp_path: Path) -> None:
    app, spec = make_app(tmp_path)

    def fail(stage: str, paths: dict[str, Path]) -> None:
        if stage == "before-atomic-replace":
            raise OSError("stop")

    with pytest.raises(OSError):
        runtime.patch_app(app, spec_path=spec, fault_hook=fail)
    resources = app / "Contents/Resources"
    assert not (resources / runtime.STATE_NAME).exists()
    assert not (resources / runtime.BACKUP_NAME).exists()
    assert not list(resources.glob(".liang-runtime-patch-*"))


def test_real_app_patch_and_restore_are_refused(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    app, spec = make_app(tmp_path)
    monkeypatch.setattr(runtime, "REAL_APP", app.resolve())
    assert code(lambda: runtime.patch_app(app, spec_path=spec)) == "REAL_APP_MUTATION_NOT_AUTHORIZED"
    assert code(lambda: runtime.restore_app(app)) == "REAL_APP_MUTATION_NOT_AUTHORIZED"


def test_dry_run_has_zero_writes(tmp_path: Path) -> None:
    app, spec = make_app(tmp_path)
    before = snapshot(app)
    result = runtime.patch_app(app, spec_path=spec, dry_run=True)
    assert result.action == "PATCH" and result.changed is False
    assert snapshot(app) == before


def test_restore_failure_rolls_back_to_patched_state(tmp_path: Path) -> None:
    app, spec = make_app(tmp_path)
    patched = runtime.patch_app(app, spec_path=spec).patched_asar_sha256

    def fail(stage: str, paths: dict[str, Path]) -> None:
        if stage == "before-restore-cleanup":
            raise OSError("restore cleanup failure")

    with pytest.raises(OSError):
        runtime.restore_app(app, fault_hook=fail)
    resources = app / "Contents/Resources"
    assert digest(resources / "app.asar") == patched
    assert (resources / runtime.STATE_NAME).exists()
    assert (resources / runtime.BACKUP_NAME).exists()
