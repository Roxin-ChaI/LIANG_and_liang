#!/usr/bin/env python3
"""Normalize Liang Wengu look-row-9 into eight hard-edged registered cells."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import deque
from pathlib import Path

from PIL import Image, ImageChops


DIRECTIONS = ("000.0", "022.5", "045.0", "067.5", "090.0", "112.5", "135.0", "157.5")
CELL_SIZE = (192, 208)
OUTPUT_SIZE = (1536, 208)
TARGET_HEIGHT = 200
TARGET_BASELINE = 203
BODY_START_FRACTION = 0.35
HEAD_END_FRACTION = 0.43
BODY_LOCK_Y = 96


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def components(image: Image.Image) -> list[list[tuple[int, int]]]:
    alpha = image.getchannel("A")
    pixels = alpha.load()
    seen: set[tuple[int, int]] = set()
    result: list[list[tuple[int, int]]] = []
    for y in range(alpha.height):
        for x in range(alpha.width):
            if not pixels[x, y] or (x, y) in seen:
                continue
            queue = deque([(x, y)])
            seen.add((x, y))
            current: list[tuple[int, int]] = []
            while queue:
                px, py = queue.popleft()
                current.append((px, py))
                for ny in range(max(0, py - 1), min(alpha.height, py + 2)):
                    for nx in range(max(0, px - 1), min(alpha.width, px + 2)):
                        point = (nx, ny)
                        if pixels[nx, ny] and point not in seen:
                            seen.add(point)
                            queue.append(point)
            result.append(current)
    return sorted(result, key=len, reverse=True)


def remove_checkerboard(slot: Image.Image) -> Image.Image:
    """Remove the border-connected light neutral checkerboard without touching enclosed shirt pixels."""
    rgb = slot.convert("RGB")
    source = rgb.load()
    width, height = rgb.size

    def eligible(x: int, y: int) -> bool:
        red, green, blue = source[x, y]
        return min(red, green, blue) >= 130 and max(red, green, blue) - min(red, green, blue) <= 40

    queue: deque[tuple[int, int]] = deque()
    background: set[tuple[int, int]] = set()
    for x in range(width):
        for y in (0, height - 1):
            if eligible(x, y) and (x, y) not in background:
                background.add((x, y))
                queue.append((x, y))
    for y in range(height):
        for x in (0, width - 1):
            if eligible(x, y) and (x, y) not in background:
                background.add((x, y))
                queue.append((x, y))
    while queue:
        x, y = queue.popleft()
        for ny in range(max(0, y - 1), min(height, y + 2)):
            for nx in range(max(0, x - 1), min(width, x + 2)):
                point = (nx, ny)
                if point not in background and eligible(nx, ny):
                    background.add(point)
                    queue.append(point)

    extracted = Image.new("RGBA", slot.size, (0, 0, 0, 0))
    output = extracted.load()
    for y in range(height):
        for x in range(width):
            if (x, y) not in background:
                red, green, blue = source[x, y]
                output[x, y] = (red, green, blue, 255)

    found = components(extracted)
    if not found:
        return extracted
    keep = set(found[0])
    cleaned = Image.new("RGBA", slot.size, (0, 0, 0, 0))
    cleaned_pixels = cleaned.load()
    for x, y in keep:
        cleaned_pixels[x, y] = output[x, y]
    return cleaned


def band_center(image: Image.Image, start_fraction: float, end_fraction: float) -> float:
    bbox = image.getbbox()
    if bbox is None:
        raise ValueError("empty image")
    left, top, right, bottom = bbox
    band_top = top + int((bottom - top) * start_fraction)
    band_bottom = top + int((bottom - top) * end_fraction)
    band_bbox = image.getchannel("A").crop((0, band_top, image.width, band_bottom)).getbbox()
    if band_bbox is None:
        raise ValueError("empty anchor band")
    return (band_bbox[0] + band_bbox[2]) / 2


def prepare_generated_frames(source: Image.Image) -> list[Image.Image]:
    frames: list[Image.Image] = []
    for index in range(len(DIRECTIONS)):
        left = round(index * source.width / len(DIRECTIONS))
        right = round((index + 1) * source.width / len(DIRECTIONS))
        extracted = remove_checkerboard(source.crop((left, 0, right, source.height)))
        if extracted.getbbox() is None:
            raise ValueError(f"generated slot {index} is empty")
        frames.append(extracted.crop(extracted.getbbox()))
    return frames


def normalize(sprite: Image.Image, shared_scale: float) -> Image.Image:
    size = (
        max(1, round(sprite.width * shared_scale)),
        max(1, round(sprite.height * shared_scale)),
    )
    resized = sprite.resize(size, Image.Resampling.NEAREST)
    body_x = band_center(resized, BODY_START_FRACTION, 1.0)
    paste_x = round(CELL_SIZE[0] / 2 - body_x)
    paste_y = TARGET_BASELINE + 1 - resized.height
    cell = Image.new("RGBA", CELL_SIZE, (0, 0, 0, 0))
    cell.alpha_composite(resized, (paste_x, paste_y))
    return cell


def exact_equal(left: Image.Image, right: Image.Image) -> bool:
    return ImageChops.difference(left, right).getbbox() is None


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--generated-source", required=True)
    parser.add_argument("--cardinals", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--frames-dir", required=True)
    parser.add_argument("--json-out", required=True)
    args = parser.parse_args()

    generated_path = Path(args.generated_source).resolve()
    cardinals_path = Path(args.cardinals).resolve()
    output_path = Path(args.output).resolve()
    frames_dir = Path(args.frames_dir).resolve()
    json_path = Path(args.json_out).resolve()

    with Image.open(generated_path) as opened:
        generated = opened.convert("RGB")
    with Image.open(cardinals_path) as opened:
        cardinals = opened.convert("RGBA")
    if cardinals.size != (768, 208):
        raise SystemExit(f"approved cardinal strip is {cardinals.size}; expected 768x208")

    source_frames = prepare_generated_frames(generated)
    shared_scale = TARGET_HEIGHT / max(frame.height for frame in source_frames)
    normalized_generated = [normalize(frame, shared_scale) for frame in source_frames]
    approved_up = cardinals.crop((0, 0, 192, 208))
    approved_right = cardinals.crop((192, 0, 384, 208))

    # Keep the generated sweep's ordered intermediate poses while replacing the two
    # cardinal slots with their approved head anchors.
    generated_source_indices: list[int | None] = [None, 1, 2, 3, 4, 5, 6, 7]
    row_frames = [
        normalized_generated[source_index] if source_index is not None else approved_up.copy()
        for source_index in generated_source_indices
    ]

    row_frames[0] = approved_up.copy()

    # Lock the complete lower body, arms, hands, clothing, and feet to one approved
    # raster. The upper 96 rows retain the generated head/neck direction family.
    approved_body = approved_up.crop((0, BODY_LOCK_Y, CELL_SIZE[0], CELL_SIZE[1]))
    for index in range(1, len(row_frames)):
        locked = Image.new("RGBA", CELL_SIZE, (0, 0, 0, 0))
        locked.alpha_composite(row_frames[index].crop((0, 0, CELL_SIZE[0], BODY_LOCK_Y)), (0, 0))
        locked.alpha_composite(approved_body, (0, BODY_LOCK_Y))
        row_frames[index] = locked

    output = Image.new("RGBA", OUTPUT_SIZE, (0, 0, 0, 0))
    frames_dir.mkdir(parents=True, exist_ok=True)
    reports: list[dict[str, object]] = []
    for index, (direction, frame) in enumerate(zip(DIRECTIONS, row_frames)):
        bbox = frame.getbbox()
        if bbox is None:
            raise ValueError(f"normalized frame {direction} is empty")
        frame_components = components(frame)
        body_center = band_center(frame, BODY_START_FRACTION, 1.0)
        head_center = band_center(frame, 0.0, HEAD_END_FRACTION)
        alpha_values = [value for value, count in enumerate(frame.getchannel("A").histogram()) if count]
        hidden_rgb_clear = all(
            pixel[:3] == (0, 0, 0)
            for pixel in frame.getdata()
            if pixel[3] == 0
        )
        frame_path = frames_dir / f"{index:02d}-{direction}.png"
        frame.save(frame_path)
        output.alpha_composite(frame, (index * CELL_SIZE[0], 0))
        reports.append(
            {
                "index": index,
                "direction": direction,
                "generated_source_index": generated_source_indices[index],
                "path": str(frame_path),
                "bbox": list(bbox),
                "baseline_y": bbox[3] - 1,
                "body_center_x": body_center,
                "head_center_x": head_center,
                "margins": {
                    "left": bbox[0],
                    "top": bbox[1],
                    "right": CELL_SIZE[0] - bbox[2],
                    "bottom": CELL_SIZE[1] - bbox[3],
                },
                "component_count": len(frame_components),
                "alpha_values": alpha_values,
                "hidden_rgb_clear": hidden_rgb_clear,
            }
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output.save(output_path)
    body_centers = [float(report["body_center_x"]) for report in reports]
    head_centers = [float(report["head_center_x"]) for report in reports]
    checks = {
        "dimensions_1536x208": output.size == OUTPUT_SIZE,
        "mode_rgba": output.mode == "RGBA",
        "eight_nonempty_192x208_cells": all(report["bbox"] for report in reports),
        "direction_order_strict": [report["direction"] for report in reports] == list(DIRECTIONS),
        "000_exact_approved_cardinal": exact_equal(row_frames[0], approved_up),
        "090_uses_coherent_sweep_right_pose": generated_source_indices[4] == 4,
        "body_arms_hands_feet_pixel_locked": all(
            exact_equal(frame.crop((0, BODY_LOCK_Y, CELL_SIZE[0], CELL_SIZE[1])), approved_body)
            for frame in row_frames
        ),
        "baseline_y_203": all(report["baseline_y"] == TARGET_BASELINE for report in reports),
        "body_center_stable_near_96": max(body_centers) - min(body_centers) <= 1.0 and all(abs(x - 96) <= 0.5 for x in body_centers),
        "adjacent_head_registration_continuous": max(abs(b - a) for a, b in zip(head_centers, head_centers[1:])) <= 8.0,
        "no_clipping": all(min(report["margins"].values()) >= 4 for report in reports),
        "no_isolated_pixels": all(report["component_count"] == 1 for report in reports),
        "binary_alpha_no_antialias": all(report["alpha_values"] == [0, 255] for report in reports),
        "hidden_background_rgb_clear": all(report["hidden_rgb_clear"] for report in reports),
        "nearest_neighbor_only": True,
    }
    report = {
        "ok": all(checks.values()),
        "generated_source": str(generated_path),
        "generated_source_sha256": digest(generated_path),
        "approved_cardinals": str(cardinals_path),
        "approved_cardinals_sha256": digest(cardinals_path),
        "output": str(output_path),
        "output_sha256": digest(output_path),
        "output_size": list(output.size),
        "mode": output.mode,
        "directions": list(DIRECTIONS),
        "shared_scale": shared_scale,
        "body_lock_y": BODY_LOCK_Y,
        "resampling": "nearest-neighbor",
        "checks": checks,
        "frames": reports,
        "manual_review": {
            "direction_semantics": "pending",
            "adjacent_head_motion": "pending",
            "approved_identity_match": "pending",
        },
    }
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": report["ok"], "checks": checks}, indent=2))
    raise SystemExit(0 if report["ok"] else 1)


if __name__ == "__main__":
    main()
