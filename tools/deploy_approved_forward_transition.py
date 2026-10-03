#!/usr/bin/env python3
"""Deploy only approved forward PNGs into the existing project-owned App."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "dist/Liang no Henshin.app"
SOURCE = ROOT / "assets/rework/v0.1.0/action-repair-2026-10-02"
BACKUP = ROOT / "backups/standalone-gu-to-feng-2026-10-03"
FRAMES = [f"assets/transform-overlay/gu_to_feng/gu_to_feng_{n:02d}.png" for n in range(1,11)]
ALLOWED = set(FRAMES + ["assets/transform-overlay.sha256"])


def run(*args):
    return subprocess.run(args, check=True, capture_output=True).stdout


def hashes(folder):
    return {p.relative_to(folder).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in folder.rglob("*") if p.is_file()}


def deploy():
    if not TARGET.is_dir() or TARGET.is_symlink() or BACKUP.exists():
        raise RuntimeError("missing/unsafe target or backup already exists; refusing overwrite")
    commands = run("ps", "-axo", "command=").decode()
    if str(TARGET / "Contents/MacOS/Electron") in commands:
        raise RuntimeError("formal App is running; refusing replacement")
    original = TARGET / "Contents/Resources/app"
    before = hashes(original)
    entitlements = run("codesign", "-d", "--entitlements", ":-", str(TARGET))
    with tempfile.TemporaryDirectory(prefix="approved-forward-", dir=ROOT/"dist") as temporary:
        staging = Path(temporary)/"Liang no Henshin.app"
        run("ditto", str(TARGET), str(staging))
        payload = staging / "Contents/Resources/app"
        for relative in FRAMES:
            shutil.copy2(SOURCE / "gu_to_feng" / Path(relative).name, payload / relative)
        # Keep reverse manifest entries exact; reject a source manifest mismatch.
        old_lines = (original/"assets/transform-overlay.sha256").read_text().splitlines()
        new_lines = (SOURCE/"transform-overlay.sha256").read_text().splitlines()
        if len(old_lines)!=18 or len(new_lines)!=18 or old_lines[10:]!=new_lines[10:]:
            raise RuntimeError("reverse checksum rows must stay exact")
        shutil.copy2(SOURCE/"transform-overlay.sha256", payload/"assets/transform-overlay.sha256")
        after = hashes(payload)
        changed = {key for key in before.keys() | after.keys() if before.get(key)!=after.get(key)}
        if changed != ALLOWED:
            raise RuntimeError(f"unexpected payload changes: {sorted(changed)}")
        # Validate with this bundle's actual original loader, not a substitute.
        loader = (payload/"runtime-patch/prototype/transition-assets.mjs").as_uri()
        js = "import {loadTransitionAssets} from " + json.dumps(loader) + "; await loadTransitionAssets(" + json.dumps({"projectRoot": str(payload)}) + ");"
        run("node", "--input-type=module", "-e", js)
        plist = Path(temporary)/"entitlements.plist"
        plist.write_bytes(entitlements)
        run("codesign", "--force", "--sign", "-", "--options", "runtime", "--entitlements", str(plist), str(staging))
        run("codesign", "--verify", "--deep", "--strict", str(staging))
        if hashes(payload) != after:
            raise RuntimeError("payload changed during signing")
        if run("codesign", "-d", "--entitlements", ":-", str(staging)) != entitlements:
            raise RuntimeError("entitlements changed")
        BACKUP.mkdir(parents=True)
        backup_app = BACKUP / TARGET.name
        os.replace(TARGET, backup_app)
        try:
            os.replace(staging, TARGET)
        except BaseException:
            os.replace(backup_app, TARGET)
            raise
        report = {"status":"DEPLOYED", "target":str(TARGET), "backup":str(backup_app),
                  "changedPayloadFiles":sorted(changed), "before":before, "after":after,
                  "signature":"STRICT_PASS", "transitionLoader":"PASS",
                  "otherPayloadFilesUnchanged":True, "runningAppReplaced":False}
        (BACKUP/"deployment.json").write_text(json.dumps(report,indent=2)+"\n")
        print(json.dumps({k:v for k,v in report.items() if k not in ("before","after")},indent=2))


if __name__=="__main__": deploy()
