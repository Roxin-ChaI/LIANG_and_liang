"""Deterministically fit approved transition PNGs into 192x208 runtime cells.

Only alpha bounding boxes, one sequence-wide nearest-neighbor scale, and
integer positioning are used. The approved source files are never written.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
DIRECTIONS = {"gu_to_feng": 10, "feng_to_gu": 8}
CELL = (192, 208)
BASELINE = 203  # Both formal v2 atlas idle rows have alpha ending at y=203.
HORIZONTAL_MARGIN = 2


@dataclass(frozen=True)
class SequencePlan:
    direction: str
    source_paths: tuple[Path, ...]
    union_bbox: tuple[int, int, int, int]
    source_size: tuple[int, int]
    scaled_size: tuple[int, int]

    @property
    def scale(self) -> float:
        return self.scaled_size[0] / self.source_size[0]


def plan_sequence(direction: str) -> SequencePlan:
    if direction not in DIRECTIONS:
        raise ValueError(f"unknown direction: {direction}")
    source_paths = tuple(sorted((ROOT / "assets" / "transform" / direction).glob("*.png")))
    if len(source_paths) != DIRECTIONS[direction]:
        raise ValueError(f"{direction}: expected {DIRECTIONS[direction]} source frames, got {len(source_paths)}")
    bounds: list[tuple[int, int, int, int]] = []
    sizes: set[tuple[int, int]] = set()
    for path in source_paths:
        with Image.open(path) as image:
            if image.mode != "RGBA":
                raise ValueError(f"{path}: expected RGBA, got {image.mode}")
            sizes.add(image.size)
            bbox = image.getchannel("A").getbbox()
            if bbox is None:
                raise ValueError(f"{path}: empty alpha")
            bounds.append(bbox)
    if len(sizes) != 1:
        raise ValueError(f"{direction}: source dimensions differ: {sizes}")
    source_size = sizes.pop()
    union = (
        min(b[0] for b in bounds), min(b[1] for b in bounds),
        max(b[2] for b in bounds), max(b[3] for b in bounds),
    )
    max_width = union[2] - union[0]
    max_height = union[3] - union[1]
    # A conservative whole-square resize avoids per-frame rounding changes.
    # Both directions' union bounds nearly fill the source; 188 px leaves a
    # 2 px horizontal safety margin and ample space above the y=203 baseline.
    limit = min(CELL[0] - 2 * HORIZONTAL_MARGIN, BASELINE + 1 - 16)
    if max(max_width, max_height) > source_size[0]:
        raise ValueError("source content exceeds source canvas")
    if source_size[0] != source_size[1]:
        raise ValueError("uniform square source expected for exact isotropic scale")
    return SequencePlan(direction, source_paths, union, source_size, (limit, limit))


def render_frame(path: Path, plan: SequencePlan) -> Image.Image:
    with Image.open(path) as source:
        # This is the only resampling operation, and its scale is identical
        # for every frame. Source alpha/RGB contents are not edited.
        scaled = source.resize(plan.scaled_size, Image.Resampling.NEAREST)
    bbox = scaled.getchannel("A").getbbox()
    if bbox is None:
        raise ValueError(f"{path}: empty after nearest-neighbor resize")
    cropped = scaled.crop(bbox)
    x = round((CELL[0] - cropped.width) / 2)
    y = BASELINE + 1 - cropped.height
    if x < 0 or x + cropped.width > CELL[0] or y < 0 or y + cropped.height > CELL[1]:
        raise ValueError(f"{path}: content would be clipped")
    canvas = Image.new("RGBA", CELL, (0, 0, 0, 0))
    canvas.paste(cropped, (x, y))
    return canvas


def png_bytes(image: Image.Image) -> bytes:
    stream = BytesIO()
    image.save(stream, format="PNG", optimize=False)
    return stream.getvalue()


def normalize(direction: str, *, check: bool = False) -> SequencePlan:
    plan = plan_sequence(direction)
    output_dir = ROOT / "assets" / "transform-runtime" / direction
    if not check:
        output_dir.mkdir(parents=True, exist_ok=True)
    for path in plan.source_paths:
        expected = png_bytes(render_frame(path, plan))
        output = output_dir / path.name
        if check:
            if not output.exists() or output.read_bytes() != expected:
                raise ValueError(f"{output}: missing or not deterministic")
        else:
            output.write_bytes(expected)
    return plan


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--direction", choices=tuple(DIRECTIONS), required=True)
    parser.add_argument("--check", action="store_true", help="compare existing outputs without writing")
    args = parser.parse_args()
    plan = normalize(args.direction, check=args.check)
    mode = "PASS" if args.check else "WRITTEN"
    print(
        f"{mode} direction={args.direction} frames={len(plan.source_paths)} "
        f"source={plan.source_size[0]}x{plan.source_size[1]} "
        f"output={CELL[0]}x{CELL[1]} scale={plan.scale:.9f} "
        f"union_bbox={plan.union_bbox} baseline={BASELINE}"
    )


if __name__ == "__main__":
    main()
