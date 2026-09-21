from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import plistlib
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
MODULE_SPEC = importlib.util.spec_from_file_location("runtime_patch_installer_e2e_module", ROOT / "installer/runtime-patch-installer.py")
assert MODULE_SPEC and MODULE_SPEC.loader
runtime = importlib.util.module_from_spec(MODULE_SPEC)
sys.modules[MODULE_SPEC.name] = runtime
MODULE_SPEC.loader.exec_module(runtime)


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


def make_app(root: Path) -> tuple[Path, Path]:
    app = root / "ChatGPT.app"
    resources = app / "Contents/Resources"
    source = root / "source"
    resources.mkdir(parents=True)
    source.mkdir()
    spec = json.loads(runtime.DEFAULT_SPEC.read_text())
    for name, chunk in spec["chunks"].items():
        file = source / chunk["path"]
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text(SOURCES[name])
        chunk["sha256"] = hashlib.sha256(SOURCES[name].encode()).hexdigest()
    runtime.create_asar_from_directory(source, resources / "app.asar")
    spec["target"]["appAsarSha256"] = digest(resources / "app.asar")
    spec_path = root / "patch-spec.json"
    spec_path.write_text(json.dumps(spec, indent=2) + "\n")
    with (app / "Contents/Info.plist").open("wb") as handle:
        plistlib.dump({"CFBundleShortVersionString": "26.908.70816", "CFBundleVersion": "9275", "CFBundleIdentifier": "com.openai.codex"}, handle)
    (app / "Contents/MacOS").mkdir()
    (app / "Contents/MacOS/ChatGPT").write_bytes(b"unchanged executable")
    (app / "Contents/Frameworks").mkdir()
    (app / "Contents/Frameworks/keep").write_text("unchanged")
    return app, spec_path


def error_code(callable_) -> str:
    with pytest.raises(runtime.RuntimePatchError) as caught:
        callable_()
    return caught.value.code


def test_case_a_supported_build_patches_and_contains_all_runtime_branches(tmp_path: Path) -> None:
    app, spec_path = make_app(tmp_path)
    result = runtime.patch_app(app, spec_path=spec_path)
    spec = json.loads(spec_path.read_text())
    archive = app / "Contents/Resources/app.asar"
    main = runtime.read_asar_file(archive, spec["chunks"]["main"]["path"]).decode()
    preload = runtime.read_asar_file(archive, spec["chunks"]["preload"]["path"]).decode()
    core = runtime.read_asar_file(archive, spec["chunks"]["core"]["path"]).decode()
    overlay = runtime.read_asar_file(archive, spec["chunks"]["overlay"]["path"]).decode()
    assert result.action == "PATCHED"
    assert "__liang9275LoadDualForm" in main
    assert "__liang9275InstallBridge" in main
    assert "liangNoHenshin" in preload
    assert "__liang9275TransitionDescriptor" in core
    assert "__liang9275Runtime?.complete" in core
    assert "__liang9275Runtime.hotSource" in overlay
    assert "__liang9275Runtime.sibling" in overlay
    assert "token!==s.operationToken" in overlay
    assert "__liang9275BindControl" in overlay
    assert "catch(_error){return result}" in main


def test_case_b_second_patch_is_already_patched(tmp_path: Path) -> None:
    app, spec = make_app(tmp_path)
    runtime.patch_app(app, spec_path=spec)
    before = snapshot(app)
    assert runtime.patch_app(app, spec_path=spec).action == "ALREADY_PATCHED"
    assert snapshot(app) == before


def test_case_c_restore_is_byte_exact_and_leaves_other_bundle_files(tmp_path: Path) -> None:
    app, spec = make_app(tmp_path)
    original = digest(app / "Contents/Resources/app.asar")
    executable = digest(app / "Contents/MacOS/ChatGPT")
    framework = digest(app / "Contents/Frameworks/keep")
    runtime.patch_app(app, spec_path=spec)
    runtime.restore_app(app)
    assert digest(app / "Contents/Resources/app.asar") == original
    assert digest(app / "Contents/MacOS/ChatGPT") == executable
    assert digest(app / "Contents/Frameworks/keep") == framework


def test_case_d_tampered_original_is_unsupported_with_zero_writes(tmp_path: Path) -> None:
    app, spec = make_app(tmp_path)
    archive = app / "Contents/Resources/app.asar"
    with archive.open("ab") as handle:
        handle.write(b"tampered")
    before = snapshot(app)
    assert error_code(lambda: runtime.patch_app(app, spec_path=spec)) == "UNSUPPORTED_BUILD"
    assert snapshot(app) == before


def test_case_e_tampered_patch_state_refuses_unsafe_restore(tmp_path: Path) -> None:
    app, spec = make_app(tmp_path)
    runtime.patch_app(app, spec_path=spec)
    state_path = app / f"Contents/Resources/{runtime.STATE_NAME}"
    state = json.loads(state_path.read_text())
    state["patchedAsarSha256"] = "0" * 64
    state_path.write_text(json.dumps(state))
    before = snapshot(app)
    assert error_code(lambda: runtime.restore_app(app)) == "PATCH_STATE_MISMATCH"
    assert snapshot(app) == before


def test_case_f_app_update_refuses_old_recipe(tmp_path: Path) -> None:
    app, spec = make_app(tmp_path)
    with (app / "Contents/Info.plist").open("wb") as handle:
        plistlib.dump({"CFBundleShortVersionString": "26.915.31945", "CFBundleVersion": "9922", "CFBundleIdentifier": "com.openai.codex"}, handle)
    before = snapshot(app)
    assert error_code(lambda: runtime.patch_app(app, spec_path=spec)) == "UNSUPPORTED_BUILD"
    assert snapshot(app) == before


def test_case_g_interruption_keeps_original_recoverable(tmp_path: Path) -> None:
    app, spec = make_app(tmp_path)
    original = digest(app / "Contents/Resources/app.asar")

    def interrupt(stage: str, paths: dict[str, Path]) -> None:
        if stage == "before-state-write":
            raise OSError("simulated interruption")

    with pytest.raises(OSError, match="interruption"):
        runtime.patch_app(app, spec_path=spec, fault_hook=interrupt)
    assert digest(app / "Contents/Resources/app.asar") == original
    assert runtime.inspect(app, spec_path=spec).action == "SUPPORTED"


def test_patched_asar_is_deterministic_for_identical_input(tmp_path: Path) -> None:
    first, first_spec = make_app(tmp_path / "one")
    second, second_spec = make_app(tmp_path / "two")
    one = runtime.patch_app(first, spec_path=first_spec)
    two = runtime.patch_app(second, spec_path=second_spec)
    assert one.patched_asar_sha256 == two.patched_asar_sha256


def test_repository_contains_no_proprietary_runtime_artifacts() -> None:
    tracked = os.popen(f"git -C {ROOT} ls-files").read().splitlines()
    forbidden_names = {"app.asar", "main-DaMR-wdT.js", "preload.js", "app-initial-4d7ea7f81c2d.js", "avatar-overlay-native-page-efa96d74af15.js"}
    assert not any(Path(relative).name in forbidden_names for relative in tracked)
    assert not any("extracted-app-asar" in relative or "/extracted/" in relative for relative in tracked)
