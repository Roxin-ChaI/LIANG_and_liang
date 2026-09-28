#!/usr/bin/env python3
"""Derive a lossless candidate: only translate five approved Gu rows down 5 px."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
ROWS = {"waving": (3, 4), "failed": (5, 8), "waiting": (6, 6),
        "running": (7, 6), "review": (8, 6)}


def translate_cell(cell: Image.Image, dy: int) -> Image.Image:
    box = cell.getchannel("A").getbbox()
    if box is None or box[1] + dy < 0 or box[3] + dy > cell.height:
        raise ValueError("translation would clip visible sprite")
    # Reject hidden RGB too: no bytes may be silently cropped.
    if any(any(pixel) for pixel in cell.crop((0, cell.height - dy, cell.width, cell.height)).get_flattened_data()):
        raise ValueError("translation would discard RGBA bytes")
    result = Image.new("RGBA", cell.size)
    result.paste(cell.crop((0, 0, cell.width, cell.height - dy)), (0, dy))
    return result


def derive(source: Path, output: Path) -> dict:
    with Image.open(source) as image:
        if image.size != (1536, 2288) or image.mode != "RGBA":
            raise ValueError("source is not v2 RGBA")
        original = image.copy()
    corrected = original.copy()
    baseline = original.crop((0, 0, 192, 208)).getchannel("A").getbbox()[3] - 1
    changes = []
    for name, (row, count) in ROWS.items():
        for index in range(count):
            position = (index * 192, row * 208)
            cell = original.crop((*position, position[0] + 192, position[1] + 208))
            before = cell.getchannel("A").getbbox()[3] - 1
            dy = baseline - before
            if dy != 5:
                raise ValueError("source no longer matches audited 5 px error")
            translated = translate_cell(cell, dy)
            corrected.paste(translated, position)
            changes.append({"state": name, "frame": index, "dy": dy,
                            "beforeBaseline": before, "afterBaseline": baseline})
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        raise ValueError("candidate already exists")
    corrected.save(output, lossless=True, exact=True, quality=100, method=6)
    with Image.open(output) as image:
        if image.convert("RGBA").tobytes() != corrected.tobytes():
            raise ValueError("candidate RGBA roundtrip changed pixels")
    sheet = Image.new("RGBA", (384, 236 * len(ROWS)), (35, 35, 35, 255))
    draw = ImageDraw.Draw(sheet)
    for line, (name, (row, _)) in enumerate(ROWS.items()):
        draw.text((4, line * 236 + 2), name + " before / after", fill="white")
        for column, atlas in enumerate((original, corrected)):
            sheet.alpha_composite(atlas.crop((0, row * 208, 192, (row + 1) * 208)),
                                  (column * 192, line * 236 + 24))
    sheet.save(output.parent / "baseline-before-after.png")
    report = {"source": str(source.relative_to(ROOT)) if source.is_relative_to(ROOT) else str(source),
              "output": str(output.relative_to(ROOT)) if output.is_relative_to(ROOT) else str(output),
              "sourceSha256": hashlib.sha256(source.read_bytes()).hexdigest(),
              "candidateSha256": hashlib.sha256(output.read_bytes()).hexdigest(),
              "operation": "integer translation; no scaling, interpolation, palette edits or reorder",
              "baseline": baseline, "changes": changes}
    (output.parent / "derivation.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=ROOT / "assets/builds/gu/spritesheet.webp")
    parser.add_argument("--output", type=Path, default=ROOT / "assets/rework/v0.1.0/gu/spritesheet.webp")
    args = parser.parse_args()
    report = derive(args.source, args.output)
    print(json.dumps({key: value for key, value in report.items() if key != "changes"}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
