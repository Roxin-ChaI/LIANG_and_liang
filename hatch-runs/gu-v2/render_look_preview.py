#!/usr/bin/env python3
"""Render the approved 16-direction loop for final motion QA."""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--frames-root", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    frames_root = Path(args.frames_root).expanduser().resolve()
    paths = sorted((frames_root / "look-row-9").glob("*.png"))
    paths += sorted((frames_root / "look-row-10").glob("*.png"))
    if len(paths) != 16:
        raise SystemExit(f"expected 16 look frames, found {len(paths)}")

    frames: list[Image.Image] = []
    for path in paths:
        with Image.open(path) as opened:
            frames.append(opened.convert("RGBA"))
    output = Path(args.output).expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    frames[0].save(
        output,
        save_all=True,
        append_images=frames[1:],
        duration=140,
        loop=0,
        disposal=2,
        optimize=False,
    )
    print(f"wrote {output}")


if __name__ == "__main__":
    main()
