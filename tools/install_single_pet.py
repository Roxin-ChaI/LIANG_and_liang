#!/usr/bin/env python3
"""Install the single selectable Pet: custom:liang-no-henshin.

Usage:
  install_single_pet.py --source /path/to/spritesheet.webp [--replace]

Writes pet.json with the fixed identity and atomically installs the active
spritesheet under ~/.codex/pets/liang-no-henshin/.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
from pathlib import Path

OUT_ROOT = Path.home() / ".codex" / "pets" / "liang-no-henshin"
MANIFEST = {
    "id": "liang-no-henshin",
    "displayName": "Liang no Henshin",
    "description": "Single selectable Pet with internal gu/feng forms.",
    "spriteVersionNumber": 2,
    "spritesheetPath": "spritesheet.webp",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def atomic_copy(source: Path, dest: Path) -> None:
    fd, tmp_name = tempfile.mkstemp(dir=str(dest.parent), prefix=".spritesheet.", suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(source.read_bytes())
        os.chmod(tmp_name, 0o644)
        os.replace(tmp_name, dest)
    except Exception:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True)
    parser.add_argument("--replace", action="store_true")
    args = parser.parse_args()

    source = Path(args.source).expanduser().resolve()
    if not source.is_file():
        raise SystemExit(f"source not found: {source}")

    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    dest = OUT_ROOT / "spritesheet.webp"
    if args.replace or not dest.exists():
        atomic_copy(source, dest)
    else:
        raise SystemExit("target already exists; pass --replace to overwrite")

    manifest_path = OUT_ROOT / "pet.json"
    manifest_path.write_text(
        json.dumps(MANIFEST, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    print(
        json.dumps(
            {
                "ok": True,
                "directory": str(OUT_ROOT),
                "pet_json": str(manifest_path),
                "spritesheet": str(dest),
                "spritesheet_sha256": sha256(dest),
            }
        )
    )


if __name__ == "__main__":
    main()
