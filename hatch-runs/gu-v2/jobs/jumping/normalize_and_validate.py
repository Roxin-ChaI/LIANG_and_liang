#!/usr/bin/env python3
"""Normalize the approved Liang Wengu five-frame low-energy hover jump."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import deque
from pathlib import Path

from PIL import Image, ImageChops


LABELS = ("01-idle", "02-anticipation", "03-peak", "04-descent", "05-settle")
BASELINES = (203, 202, 199, 201, 203)
CELL_SIZE = (192, 208)
OUTPUT_SIZE = (960, 208)
TARGET_HEIGHT = 198
BODY_LOCK_Y = 96
BODY_START_FRACTION = 0.55
HEAD_END_FRACTION = 0.43
ALPHA_THRESHOLD = 64


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


def keep_largest(image: Image.Image) -> Image.Image:
    found = components(image)
    if not found:
        return image
    keep = set(found[0])
    source = image.load()
    cleaned = Image.new("RGBA", image.size, (0, 0, 0, 0))
    target = cleaned.load()
    for x, y in keep:
        target[x, y] = source[x, y]
    return cleaned


def hard_alpha(image: Image.Image) -> Image.Image:
    rgba = image.convert("RGBA")
    source = rgba.load()
    result = Image.new("RGBA", rgba.size, (0, 0, 0, 0))
    target = result.load()
    for y in range(rgba.height):
        for x in range(rgba.width):
            red, green, blue, alpha = source[x, y]
            if alpha >= ALPHA_THRESHOLD:
                target[x, y] = (red, green, blue, 255)
    return keep_largest(result)


def remove_checkerboard(slot: Image.Image) -> Image.Image:
    rgb = slot.convert("RGB")
    source = rgb.load()
    width, height = rgb.size

    def eligible(x: int, y: int) -> bool:
        red, green, blue = source[x, y]
        return min(red, green, blue) >= 90 and max(red, green, blue) - min(red, green, blue) <= 45

    queue: deque[tuple[int, int]] = deque()
    background: set[tuple[int, int]] = set()
    for x in range(width):
        for y in (0, height - 1):
            if eligible(x, y):
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

    result = Image.new("RGBA", slot.size, (0, 0, 0, 0))
    target = result.load()
    for y in range(height):
        for x in range(width):
            if (x, y) not in background:
                red, green, blue = source[x, y]
                target[x, y] = (red, green, blue, 255)
    return keep_largest(result)


def band_center(image: Image.Image, start_fraction: float, end_fraction: float) -> float:
    bbox = image.getbbox()
    if bbox is None:
        raise ValueError("empty frame")
    _left, top, _right, bottom = bbox
    band_top = top + int((bottom - top) * start_fraction)
    band_bottom = top + int((bottom - top) * end_fraction)
    band_bbox = image.getchannel("A").crop((0, band_top, image.width, band_bottom)).getbbox()
    if band_bbox is None:
        raise ValueError("empty anchor band")
    return (band_bbox[0] + band_bbox[2]) / 2


def normalize(sprite: Image.Image, scale: float, baseline: int = 203) -> Image.Image:
    crop = sprite.crop(sprite.getbbox())
    resized = crop.resize(
        (max(1, round(crop.width * scale)), max(1, round(crop.height * scale))),
        Image.Resampling.NEAREST,
    )
    paste_x = round(CELL_SIZE[0] / 2 - band_center(resized, BODY_START_FRACTION, 1.0))
    paste_y = baseline + 1 - resized.height
    cell = Image.new("RGBA", CELL_SIZE, (0, 0, 0, 0))
    cell.alpha_composite(resized, (paste_x, paste_y))
    return cell


def shift_vertical(image: Image.Image, amount: int) -> Image.Image:
    shifted = Image.new("RGBA", CELL_SIZE, (0, 0, 0, 0))
    shifted.alpha_composite(image, (0, amount))
    return shifted


def exact_equal(left: Image.Image, right: Image.Image) -> bool:
    return ImageChops.difference(left, right).getbbox() is None


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--generated-source", required=True)
    parser.add_argument("--approved-idle-row", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--frames-dir", required=True)
    parser.add_argument("--json-out", required=True)
    args = parser.parse_args()

    generated_path = Path(args.generated_source).resolve()
    idle_row_path = Path(args.approved_idle_row).resolve()
    output_path = Path(args.output).resolve()
    frames_dir = Path(args.frames_dir).resolve()
    json_path = Path(args.json_out).resolve()

    with Image.open(generated_path) as opened:
        generated = opened.convert("RGB")
    with Image.open(idle_row_path) as opened:
        idle_row = opened.convert("RGBA")
    approved_idle_source = idle_row.crop((0, 0, 192, 208))
    approved_sprite = approved_idle_source.crop(approved_idle_source.getbbox())
    approved_scale = TARGET_HEIGHT / approved_sprite.height
    approved_idle = normalize(approved_sprite, approved_scale)

    source_frames: list[Image.Image] = []
    for index in range(len(LABELS)):
        left = round(index * generated.width / len(LABELS))
        right = round((index + 1) * generated.width / len(LABELS))
        frame = remove_checkerboard(generated.crop((left, 0, right, generated.height)))
        if frame.getbbox() is None:
            raise ValueError(f"generated frame {index + 1} is empty")
        source_frames.append(frame)
    shared_scale = TARGET_HEIGHT / max(frame.getbbox()[3] - frame.getbbox()[1] for frame in source_frames)
    generated_frames = [normalize(frame, shared_scale) for frame in source_frames]

    source_indices: list[int | None] = [None, 1, 2, 3, None]
    frames = [
        generated_frames[source_index] if source_index is not None else approved_idle.copy()
        for source_index in source_indices
    ]
    approved_body = approved_idle.crop((0, BODY_LOCK_Y, CELL_SIZE[0], CELL_SIZE[1]))
    for index in range(len(frames)):
        locked = Image.new("RGBA", CELL_SIZE, (0, 0, 0, 0))
        locked.alpha_composite(frames[index].crop((0, 0, CELL_SIZE[0], BODY_LOCK_Y)), (0, 0))
        locked.alpha_composite(approved_body, (0, BODY_LOCK_Y))
        frames[index] = keep_largest(shift_vertical(locked, BASELINES[index] - 203))

    output = Image.new("RGBA", OUTPUT_SIZE, (0, 0, 0, 0))
    frames_dir.mkdir(parents=True, exist_ok=True)
    reports: list[dict[str, object]] = []
    for index, (label, frame) in enumerate(zip(LABELS, frames)):
        bbox = frame.getbbox()
        if bbox is None:
            raise ValueError(f"normalized {label} is empty")
        alpha_values = [value for value, count in enumerate(frame.getchannel("A").histogram()) if count]
        hidden_rgb_clear = all(pixel[:3] == (0, 0, 0) for pixel in frame.getdata() if pixel[3] == 0)
        frame_components = components(frame)
        frame_path = frames_dir / f"{index + 1:02d}-{label}.png"
        frame.save(frame_path)
        output.alpha_composite(frame, (index * CELL_SIZE[0], 0))
        reports.append(
            {
                "index": index,
                "label": label,
                "generated_source_index": source_indices[index],
                "path": str(frame_path),
                "bbox": list(bbox),
                "baseline_y": bbox[3] - 1,
                "body_center_x": band_center(frame, BODY_START_FRACTION, 1.0),
                "head_center_x": band_center(frame, 0.0, HEAD_END_FRACTION),
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
    body_centers = [float(frame["body_center_x"]) for frame in reports]
    observed_baselines = [int(frame["baseline_y"]) for frame in reports]
    checks = {
        "dimensions_960x208": output.size == OUTPUT_SIZE,
        "mode_rgba": output.mode == "RGBA",
        "five_nonempty_192x208_cells": all(frame["bbox"] for frame in reports),
        "frame_1_and_5_same_approved_idle": exact_equal(frames[0], frames[4]),
        "frame_1_and_5_baseline_y_203": observed_baselines[0] == observed_baselines[4] == 203,
        "body_center_stable_near_96": max(body_centers) - min(body_centers) <= 1.0
        and all(abs(center - 96.0) <= 1.5 for center in body_centers),
        "vertical_jump_trajectory_continuous": observed_baselines == list(BASELINES),
        "no_horizontal_drift": max(body_centers) - min(body_centers) <= 1.0,
        "peak_has_transparent_top_margin": reports[2]["margins"]["top"] >= 1,
        "no_clipping": all(min(frame["margins"].values()) >= 1 for frame in reports),
        "no_isolated_pixels": all(frame["component_count"] == 1 for frame in reports),
        "binary_alpha_no_antialias": all(frame["alpha_values"] == [0, 255] for frame in reports),
        "hidden_background_rgb_clear": all(frame["hidden_rgb_clear"] for frame in reports),
        "nearest_neighbor_only": True,
    }
    report = {
        "ok": all(checks.values()),
        "generated_source": str(generated_path),
        "generated_source_sha256": digest(generated_path),
        "approved_idle_row": str(idle_row_path),
        "approved_idle_row_sha256": digest(idle_row_path),
        "output": str(output_path),
        "output_sha256": digest(output_path),
        "output_size": list(output.size),
        "mode": output.mode,
        "frame_labels": list(LABELS),
        "target_baselines": list(BASELINES),
        "jump_height_pixels": 4,
        "body_lock_y_before_translation": BODY_LOCK_Y,
        "resampling": "nearest-neighbor",
        "checks": checks,
        "frames": reports,
        "manual_review": {
            "low_energy_hover_jump": "pending",
            "vertical_motion_continuity": "pending",
            "frame_5_return": "pending",
            "approved_identity_match": "pending",
        },
    }
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": report["ok"], "checks": checks}, indent=2))
    raise SystemExit(0 if report["ok"] else 1)


if __name__ == "__main__":
    main()
