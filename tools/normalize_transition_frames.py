"""Deterministically normalize approved transition PNGs.

The default historical Phase 3A mode fits 192x208 cells. Explicit
``--layout overlay`` uses the frozen Phase 3C per-frame nearest-neighbor scale
and Phase 3D fixed oversized canvas. Approved sources are never written.
"""

from __future__ import annotations

import argparse
import json
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


def overlay_plan(direction: str) -> tuple[dict[str, int], list[dict[str, object]]]:
    if direction not in DIRECTIONS:
        raise ValueError(f"unknown direction: {direction}")
    layout_path = ROOT / "runtime-patch" / "fixtures" / "transition-overlay-layout.json"
    schedule_path = ROOT / "runtime-patch" / "fixtures" / "transition-scale-schedule.json"
    layout = json.loads(layout_path.read_text())[direction]
    entries = json.loads(schedule_path.read_text())[direction]
    if len(entries) != DIRECTIONS[direction] or [e["frame"] for e in entries] != list(range(1, DIRECTIONS[direction] + 1)):
        raise ValueError(f"{direction}: malformed frozen schedule")
    if layout["petAnchorX"] != CELL[0] // 2 or layout["petBaselineY"] != BASELINE:
        raise ValueError(f"{direction}: normal Pet anchor changed")
    if layout["offsetLeft"] != CELL[0] // 2 - layout["anchorX"] or layout["offsetTop"] != BASELINE - layout["anchorY"]:
        raise ValueError(f"{direction}: overlay offsets disagree with anchors")
    return layout, entries


def render_overlay_frame(direction: str, entry: dict[str, object], layout: dict[str, int]) -> Image.Image:
    # Imported here to retain the legacy normalization path and avoid a
    # module-load cycle with Phase 3B's geometry helpers.
    from analyze_transition_endpoints import dark_character_bbox

    frame = int(entry["frame"])
    side = int(entry["resizedWidth"])
    if side != int(entry["resizedHeight"]) or side <= 0:
        raise ValueError(f"{direction} {frame}: schedule is not isotropic")
    path = ROOT / "assets" / "transform" / direction / f"{direction}_{frame:02d}.png"
    with Image.open(path) as source:
        if source.mode != "RGBA" or source.size != (1254, 1254):
            raise ValueError(f"{path}: approved source format changed")
        scaled = source.resize((side, side), Image.Resampling.NEAREST)
    body = dark_character_bbox(scaled)
    full = scaled.getchannel("A").getbbox()
    if full is None:
        raise ValueError(f"{path}: empty resized frame")
    dx = round(layout["anchorX"] - (body[0] + body[2]) / 2)
    dy = layout["anchorY"] - (body[3] - 1)
    moved = (full[0] + dx, full[1] + dy, full[2] + dx, full[3] + dy)
    size = (layout["canvasWidth"], layout["canvasHeight"])
    if moved[0] < 0 or moved[1] < 0 or moved[2] > size[0] or moved[3] > size[1]:
        raise ValueError(f"{path}: full alpha/effect would be cropped by overlay")
    canvas = Image.new("RGBA", size, (0, 0, 0, 0))
    canvas.paste(scaled.crop(full), moved[:2])
    return canvas


def normalize(direction: str, *, check: bool = False, layout: str = "cell") -> SequencePlan | dict[str, int]:
    if layout == "overlay":
        overlay, entries = overlay_plan(direction)
        output_dir = ROOT / "assets" / "transform-overlay" / direction
        if not check:
            output_dir.mkdir(parents=True, exist_ok=True)
        for entry in entries:
            frame = int(entry["frame"])
            output = output_dir / f"{direction}_{frame:02d}.png"
            expected = png_bytes(render_overlay_frame(direction, entry, overlay))
            if check:
                if not output.exists() or output.read_bytes() != expected:
                    raise ValueError(f"{output}: missing or not deterministic")
            else:
                output.write_bytes(expected)
        return overlay
    if layout != "cell":
        raise ValueError(f"unknown layout: {layout}")
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
    parser.add_argument("--layout", choices=("cell", "overlay"), default="cell",
                        help="default historical 192x208 cell or Phase 3D oversized overlay")
    parser.add_argument("--check", action="store_true", help="compare existing outputs without writing")
    args = parser.parse_args()
    plan = normalize(args.direction, check=args.check, layout=args.layout)
    mode = "PASS" if args.check else "WRITTEN"
    if args.layout == "overlay":
        print(f"{mode} layout=overlay direction={args.direction} frames={DIRECTIONS[args.direction]} "
              f"output={plan['canvasWidth']}x{plan['canvasHeight']} "
              f"anchor=({plan['anchorX']},{plan['anchorY']}) baseline={BASELINE}")
    else:
        print(
            f"{mode} direction={args.direction} frames={len(plan.source_paths)} "
            f"source={plan.source_size[0]}x{plan.source_size[1]} "
            f"output={CELL[0]}x{CELL[1]} scale={plan.scale:.9f} "
            f"union_bbox={plan.union_bbox} baseline={BASELINE}"
        )


if __name__ == "__main__":
    main()
