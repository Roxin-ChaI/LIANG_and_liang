#!/usr/bin/env python3
"""Build a read-only visual QA sheet from actual standalone window captures."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image, ImageDraw


def build(input_dir: Path, output: Path) -> dict:
    sequences = (("gu_to_feng", 10), ("feng_to_gu", 8))
    sheet = Image.new("RGBA", (10 * 256, 2 * 288), (32, 32, 32, 255))
    draw = ImageDraw.Draw(sheet)
    bounds = {}
    for row, (name, count) in enumerate(sequences):
        bounds[name] = []
        for index in range(count):
            path = input_dir / f"{name}-{index:02d}.png"
            with Image.open(path) as source:
                frame = source.convert("RGBA")
            if frame.size not in ((256, 256), (512, 512)):
                raise ValueError(f"unexpected capture geometry: {path}: {frame.size}")
            bbox = frame.getchannel("A").getbbox()
            if bbox is None:
                raise ValueError(f"empty transition capture: {path}")
            bounds[name].append(bbox)
            if frame.size == (512, 512):
                frame = frame.resize((256, 256), Image.Resampling.NEAREST)
            sheet.alpha_composite(frame, (index * 256, row * 288 + 32))
            draw.text((index * 256 + 4, row * 288 + 5), f"{name} {index:02d}", fill="white")
    output.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output)
    return {"sheet": str(output), "frameCounts": {name: count for name, count in sequences},
            "alphaBounds": bounds}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_dir", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(build(args.input_dir, args.output), indent=2))


if __name__ == "__main__":
    main()
