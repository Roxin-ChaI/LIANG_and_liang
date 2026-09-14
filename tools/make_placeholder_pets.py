#!/usr/bin/env python3
"""Build two minimal placeholder Codex v2 pets from approved idle art.

This is a temporary verification helper only. It does not call image
generation and does not modify the approved source assets.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
OUT_ROOT = Path.home() / ".codex" / "pets"

CELL_W, CELL_H = 192, 208
COLS, ROWS = 8, 11

# Standard row 0-10 used-column layout from the installed hatch-pet skill.
USED = [
    (0, 7),   # idle: 0..5 + v2 neutral at col 6
    (1, 8),   # running-right
    (2, 8),   # running-left
    (3, 4),   # waving
    (4, 5),   # jumping / hover
    (5, 8),   # failed
    (6, 6),   # waiting
    (7, 6),   # running
    (8, 6),   # review
    (9, 8),   # look directions A
    (10, 8),  # look directions B
]

PETS = [
    {
        "dir": "liang-gu",
        "source": ASSETS / "gu" / "idle.png",
        "pet_json": {
            "id": "liang-gu",
            "displayName": "Liang Wengu",
            "description": "Temporary minimal test pet for switch verification.",
            "spriteVersionNumber": 2,
            "spritesheetPath": "spritesheet.webp",
        },
    },
    {
        "dir": "liang-feng",
        "source": ASSETS / "feng" / "idle.png",
        "pet_json": {
            "id": "liang-feng",
            "displayName": "Liang Wenfeng",
            "description": "Temporary minimal test pet for switch verification.",
            "spriteVersionNumber": 2,
            "spritesheetPath": "spritesheet.webp",
        },
    },
]


def clear_rgb_under_transparency(image: Image.Image) -> Image.Image:
    rgba = image.convert("RGBA")
    alpha = rgba.getchannel("A")
    rgba.putalpha(alpha)
    # Zero hidden RGB under fully transparent pixels.
    data = bytearray(rgba.tobytes())
    for idx in range(0, len(data), 4):
        if data[idx + 3] == 0:
            data[idx] = 0
            data[idx + 1] = 0
            data[idx + 2] = 0
    result = Image.frombytes("RGBA", rgba.size, bytes(data))
    return result


def content_crop(image: Image.Image) -> Image.Image:
    alpha = image.getchannel("A")
    bbox = alpha.point(lambda v: 255 if v > 8 else 0).getbbox()
    if bbox is None:
        raise RuntimeError("source image has no visible content")
    left, top, right, bottom = bbox
    # Small margin so soft edges are not clipped by the crop itself.
    m = 2
    left = max(0, left - m)
    top = max(0, top - m)
    right = min(image.width, right + m)
    bottom = min(image.height, bottom + m)
    return clear_rgb_under_transparency(image.crop((left, top, right, bottom)))


def make_cell(source_path: Path) -> Image.Image:
    source = clear_rgb_under_transparency(Image.open(source_path))
    cropped = content_crop(source)
    scale = min(
        (CELL_W - 12) / cropped.width,
        (CELL_H - 12) / cropped.height,
    )
    resized = cropped.resize(
        (max(1, round(cropped.width * scale)), max(1, round(cropped.height * scale))),
        Image.LANCZOS,
    )
    cell = Image.new("RGBA", (CELL_W, CELL_H), (0, 0, 0, 0))
    x = (CELL_W - resized.width) // 2
    y = CELL_H - 6 - resized.height
    cell.alpha_composite(resized, (x, y))
    return clear_rgb_under_transparency(cell)


def build_sheet(cell: Image.Image) -> Image.Image:
    sheet = Image.new("RGBA", (CELL_W * COLS, CELL_H * ROWS), (0, 0, 0, 0))
    for row, used in USED:
        for col in range(COLS):
            if col < used:
                sheet.paste(cell, (col * CELL_W, row * CELL_H))
    return clear_rgb_under_transparency(sheet)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    for pet in PETS:
        package = OUT_ROOT / pet["dir"]
        package.mkdir(parents=True, exist_ok=True)
        cell = make_cell(pet["source"])
        sheet = build_sheet(cell)
        sheet_path = package / "spritesheet.webp"
        sheet.save(sheet_path, "WEBP", lossless=True, quality=100, method=6)
        manifest_path = package / "pet.json"
        manifest_path.write_text(
            json.dumps(pet["pet_json"], indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        print(
            json.dumps(
                {
                    "dir": pet["dir"],
                    "spritesheet": str(sheet_path),
                    "spritesheet_bytes": sheet_path.stat().st_size,
                    "spritesheet_sha256": sha256(sheet_path),
                    "pet_json_sha256": sha256(manifest_path),
                }
            )
        )


if __name__ == "__main__":
    main()
