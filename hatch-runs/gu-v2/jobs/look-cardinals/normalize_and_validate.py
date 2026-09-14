#!/usr/bin/env python3
"""Normalize an approved four-cardinal RGBA strip without redrawing pixels."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import deque
from pathlib import Path

from PIL import Image


DIRECTIONS = ("000", "090", "180", "270")
CELL_SIZE = (192, 208)
OUTPUT_SIZE = (CELL_SIZE[0] * len(DIRECTIONS), CELL_SIZE[1])
ALPHA_THRESHOLD = 64
TARGET_HEIGHT = 200
TARGET_BASELINE = 203
BODY_START_FRACTION = 0.35


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def alpha_count(image: Image.Image) -> int:
    return sum(image.getchannel("A").histogram()[1:])


def binary_foreground(image: Image.Image) -> Image.Image:
    rgba = image.convert("RGBA")
    source = rgba.load()
    cleaned = Image.new("RGBA", rgba.size, (0, 0, 0, 0))
    target = cleaned.load()
    for y in range(rgba.height):
        for x in range(rgba.width):
            red, green, blue, alpha = source[x, y]
            if alpha >= ALPHA_THRESHOLD:
                target[x, y] = (red, green, blue, 255)
    return cleaned


def connected_components(image: Image.Image) -> list[list[tuple[int, int]]]:
    alpha = image.getchannel("A")
    pixels = alpha.load()
    visited: set[tuple[int, int]] = set()
    components: list[list[tuple[int, int]]] = []
    for y in range(alpha.height):
        for x in range(alpha.width):
            if pixels[x, y] == 0 or (x, y) in visited:
                continue
            queue = deque([(x, y)])
            visited.add((x, y))
            component: list[tuple[int, int]] = []
            while queue:
                current_x, current_y = queue.popleft()
                component.append((current_x, current_y))
                for neighbor_y in range(max(0, current_y - 1), min(alpha.height, current_y + 2)):
                    for neighbor_x in range(max(0, current_x - 1), min(alpha.width, current_x + 2)):
                        point = (neighbor_x, neighbor_y)
                        if pixels[neighbor_x, neighbor_y] and point not in visited:
                            visited.add(point)
                            queue.append(point)
            components.append(component)
    return components


def keep_largest_component(image: Image.Image) -> tuple[Image.Image, dict[str, int]]:
    components = connected_components(image)
    if not components:
        return image, {"component_count_before": 0, "removed_pixels": 0}
    components.sort(key=len, reverse=True)
    keep = set(components[0])
    cleaned = Image.new("RGBA", image.size, (0, 0, 0, 0))
    source = image.load()
    target = cleaned.load()
    for x, y in keep:
        target[x, y] = source[x, y]
    return cleaned, {
        "component_count_before": len(components),
        "removed_pixels": sum(len(component) for component in components[1:]),
    }


def body_center(image: Image.Image) -> float:
    bbox = image.getbbox()
    if bbox is None:
        raise ValueError("cannot calculate body center for an empty image")
    left, top, right, bottom = bbox
    body_top = top + int((bottom - top) * BODY_START_FRACTION)
    body_bbox = image.getchannel("A").crop((0, body_top, image.width, bottom)).getbbox()
    if body_bbox is None:
        raise ValueError("body anchor region is empty")
    return (body_bbox[0] + body_bbox[2]) / 2


def normalize_frame(frame: Image.Image) -> tuple[Image.Image, dict[str, object]]:
    thresholded = binary_foreground(frame)
    isolated_cleaned, component_report = keep_largest_component(thresholded)
    source_bbox = isolated_cleaned.getbbox()
    if source_bbox is None:
        raise ValueError("source frame is empty after alpha cleanup")
    sprite = isolated_cleaned.crop(source_bbox)
    shared_scale = TARGET_HEIGHT / max(source_bbox[3] - source_bbox[1], 1)
    resized_size = (
        max(1, round(sprite.width * shared_scale)),
        max(1, round(sprite.height * shared_scale)),
    )
    sprite = sprite.resize(resized_size, Image.Resampling.NEAREST)
    sprite, post_resize_components = keep_largest_component(sprite)

    anchor_x = body_center(sprite)
    paste_x = round(CELL_SIZE[0] / 2 - anchor_x)
    paste_y = TARGET_BASELINE + 1 - sprite.height
    cell = Image.new("RGBA", CELL_SIZE, (0, 0, 0, 0))
    cell.alpha_composite(sprite, (paste_x, paste_y))

    final_bbox = cell.getbbox()
    if final_bbox is None:
        raise ValueError("normalized frame is empty")
    final_components = connected_components(cell)
    final_body_center = body_center(cell)
    margins = {
        "left": final_bbox[0],
        "top": final_bbox[1],
        "right": CELL_SIZE[0] - final_bbox[2],
        "bottom": CELL_SIZE[1] - final_bbox[3],
    }
    report: dict[str, object] = {
        "source_bbox": list(source_bbox),
        "source_used_pixels_after_threshold": alpha_count(isolated_cleaned),
        "alpha_threshold": ALPHA_THRESHOLD,
        "source_cleanup": component_report,
        "scale": shared_scale,
        "resampling": "nearest-neighbor",
        "resized_size": list(resized_size),
        "post_resize_removed_pixels": post_resize_components["removed_pixels"],
        "paste_xy": [paste_x, paste_y],
        "final_bbox": list(final_bbox),
        "baseline_y": final_bbox[3] - 1,
        "body_center_x": final_body_center,
        "margins": margins,
        "used_pixels": alpha_count(cell),
        "component_count": len(final_components),
        "alpha_values": [index for index, count in enumerate(cell.getchannel("A").histogram()) if count],
    }
    return cell, report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--anchors-dir", required=True)
    parser.add_argument("--approved-strip", required=True)
    parser.add_argument("--json-out", required=True)
    args = parser.parse_args()

    source_path = Path(args.source).expanduser().resolve()
    output_path = Path(args.output).expanduser().resolve()
    anchors_dir = Path(args.anchors_dir).expanduser().resolve()
    approved_strip_path = Path(args.approved_strip).expanduser().resolve()
    json_path = Path(args.json_out).expanduser().resolve()

    with Image.open(source_path) as opened:
        source = opened.convert("RGBA")
    if source.width % len(DIRECTIONS):
        raise SystemExit(f"source width {source.width} is not divisible by four")

    source_cell_width = source.width // len(DIRECTIONS)
    output = Image.new("RGBA", OUTPUT_SIZE, (0, 0, 0, 0))
    anchors_dir.mkdir(parents=True, exist_ok=True)
    frame_reports: list[dict[str, object]] = []
    for index, direction in enumerate(DIRECTIONS):
        source_cell = source.crop(
            (index * source_cell_width, 0, (index + 1) * source_cell_width, source.height)
        )
        normalized, frame_report = normalize_frame(source_cell)
        output.alpha_composite(normalized, (index * CELL_SIZE[0], 0))
        anchor_path = anchors_dir / f"{direction}.png"
        normalized.save(anchor_path)
        frame_report["direction"] = direction
        frame_report["source_slot"] = index
        frame_report["anchor_path"] = str(anchor_path)
        frame_reports.append(frame_report)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    approved_strip_path.parent.mkdir(parents=True, exist_ok=True)
    output.save(output_path)
    output.save(approved_strip_path)

    baselines = [int(frame["baseline_y"]) for frame in frame_reports]
    body_centers = [float(frame["body_center_x"]) for frame in frame_reports]
    checks = {
        "dimensions_768x208": output.size == OUTPUT_SIZE,
        "mode_rgba": output.mode == "RGBA",
        "four_nonempty_cells": all(int(frame["used_pixels"]) > 0 for frame in frame_reports),
        "baseline_consistent": len(set(baselines)) == 1,
        "body_center_stable": max(body_centers) - min(body_centers) <= 1.0,
        "no_clipping": all(min(dict(frame["margins"]).values()) >= 4 for frame in frame_reports),
        "no_unexpected_isolated_pixels": all(int(frame["component_count"]) == 1 for frame in frame_reports),
        "direction_order_000_090_180_270": tuple(
            str(frame["direction"]) for frame in frame_reports
        ) == DIRECTIONS,
        "binary_alpha_no_antialias": all(
            list(frame["alpha_values"]) == [0, 255] for frame in frame_reports
        ),
        "nearest_neighbor_only": all(
            frame["resampling"] == "nearest-neighbor" for frame in frame_reports
        ),
    }
    report = {
        "ok": all(checks.values()),
        "source": str(source_path),
        "source_sha256": sha256(source_path),
        "output": str(output_path),
        "output_sha256": sha256(output_path),
        "approved_strip": str(approved_strip_path),
        "source_size": list(source.size),
        "output_size": list(output.size),
        "mode": output.mode,
        "directions": list(DIRECTIONS),
        "method": "alpha threshold + largest connected component + shared-height nearest-neighbor resize + common body center and feet baseline",
        "checks": checks,
        "frames": frame_reports,
        "manual_review": {
            "direction_semantics": "pending",
            "approved_identity_match": "pending",
        },
    }
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": report["ok"], "checks": checks}, indent=2))
    raise SystemExit(0 if report["ok"] else 1)


if __name__ == "__main__":
    main()
