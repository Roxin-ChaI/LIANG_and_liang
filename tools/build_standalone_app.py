#!/usr/bin/env python3
"""Build a new project-owned macOS Electron App; never copy or patch Codex."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import plistlib
import shutil
import subprocess
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ELECTRON_APP = ROOT / "runtime-patch/electron-harness/node_modules/electron/dist/Electron.app"
DIST = ROOT / "dist/Liang no Henshin.app"
BUNDLE_ID = "com.liang-no-henshin.standalone"
APP_FILES = (
    "standalone-app/main.mjs", "standalone-app/preload.cjs",
    "standalone-app/renderer.mjs", "standalone-app/animation.mjs",
    "standalone-app/events.mjs", "standalone-app/codex-events.mjs",
    "standalone-app/pipeline-diagnostic.mjs",
    "standalone-app/schedule.mjs",
    "standalone-app/index.html", "standalone-app/style.css",
    "tools/codex_hook_receiver.py", "tools/codex_hook_probe.py",
    "runtime-patch/prototype/dual-form-source.mjs",
    "runtime-patch/prototype/transition-assets.mjs",
    "runtime-patch/prototype/transition-player.mjs",
    "runtime-patch/reference/runtime-state.mjs",
    "runtime-patch/fixtures/transition-overlay-layout.json",
    "assets/builds/gu/spritesheet.webp", "assets/builds/feng/spritesheet.webp",
    "assets/transform-overlay.sha256",
    *(f"assets/transform-overlay/gu_to_feng/gu_to_feng_{index:02d}.png" for index in range(1, 11)),
    *(f"assets/transform-overlay/feng_to_gu/feng_to_gu_{index:02d}.png" for index in range(1, 9)),
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def command(*args: str) -> None:
    result = subprocess.run(args, capture_output=True, check=False)
    if result.returncode:
        raise RuntimeError(f"command failed: {args[0]} ({result.returncode}): {result.stderr.decode('utf-8', 'replace')[:250]}")


def source_files() -> list[tuple[Path, Path]]:
    files = []
    for relative in APP_FILES:
        source = ROOT / relative
        if not source.is_file() or source.is_symlink():
            raise RuntimeError(f"missing or unsafe source file: {relative}")
        files.append((source, Path(relative)))
    if len(files) != len(set(relative for _, relative in files)):
        raise RuntimeError("duplicate bundle source path")
    return files


def build(destination: Path = DIST) -> dict[str, object]:
    if destination.exists() or destination.is_symlink():
        raise RuntimeError("destination already exists; refusing to overwrite")
    if not ELECTRON_APP.is_dir():
        raise RuntimeError("project Electron runtime is not installed")
    files = source_files()
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="liang-app-build-", dir=destination.parent) as temporary:
        temporary_root = Path(temporary)
        app = temporary_root / "Liang no Henshin.app"
        command("ditto", str(ELECTRON_APP), str(app))
        plist_path = app / "Contents/Info.plist"
        with plist_path.open("rb") as handle:
            info = plistlib.load(handle)
        info["CFBundleIdentifier"] = BUNDLE_ID
        info["CFBundleName"] = "Liang no Henshin"
        info["CFBundleDisplayName"] = "Liang no Henshin"
        with plist_path.open("wb") as handle:
            plistlib.dump(info, handle)
        payload = app / "Contents/Resources/app"
        payload.mkdir()
        (payload / "package.json").write_text(json.dumps({
            "name": "liang-no-henshin-standalone", "version": "0.1.0",
            "private": True, "type": "module", "main": "standalone-app/main.mjs",
        }, sort_keys=True) + "\n")
        hashes = {}
        for source, relative in files:
            target = payload / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
            original = sha256(source)
            if sha256(target) != original:
                raise RuntimeError(f"bundled asset changed: {relative}")
            hashes[relative.as_posix()] = original
        entitlements = temporary_root / "standalone-entitlements.plist"
        entitlements.write_bytes(plistlib.dumps({
            "com.apple.security.cs.allow-jit": True,
            "com.apple.security.cs.allow-unsigned-executable-memory": True,
            "com.apple.security.cs.disable-library-validation": True,
        }))
        # This signs only a newly created project-owned App, never Codex.
        command("codesign", "--force", "--deep", "--sign", "-", "--options", "runtime",
                "--entitlements", str(entitlements), str(app))
        command("codesign", "--verify", "--deep", "--strict", str(app))
        if not (app / "Contents/MacOS/Electron").is_file():
            raise RuntimeError("bundled Electron executable is missing")
        os.replace(app, destination)
    return {"status": "BUILT", "path": str(destination), "bundleId": BUNDLE_ID,
            "files": len(files), "signed": "PROJECT_OWNED_AD_HOC", "assetHashes": hashes}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DIST)
    args = parser.parse_args()
    try:
        result = build(args.output)
    except (OSError, RuntimeError) as error:
        print(json.dumps({"status": "BUILD_FAILED", "reason": str(error)}))
        return 2
    print(json.dumps({key: value for key, value in result.items() if key != "assetHashes"}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
