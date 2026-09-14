#!/usr/bin/env python3
"""Normalize the approved Liang Wengu six-frame idle loop."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import deque
from pathlib import Path

from PIL import Image, ImageChops


FRAME_LABELS = ("01-idle", "02-breathe-down", "03-blink", "04-eyes-closed", "05-reopen", "06-loop-return")
CELL_SIZE = (192, 208)
OUTPUT_SIZE = (1152, 208)
TARGET_HEIGHT = 200
TARGET_BASELINE = 203
BODY_LOCK_Y = 96
BODY_START_FRACTION = 0.35
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


def hard_alpha_largest_component(image: Image.Image) -> Image.Image:
    rgba = image.convert("RGBA")
    source = rgba.load()
    thresholded = Image.new("RGBA", rgba.size, (0, 0, 0, 0))
    target = thresholded.load()
    for y in range(rgba.height):
        for x in range(rgba.width):
            red, green, blue, alpha = source[x, y]
            if alpha >= ALPHA_THRESHOLD:
                target[x, y] = (red, green, blue, 255)
    found = components(thresholded)
    if not found:
        return thresholded
    keep = set(found[0])
    cleaned = Image.new("RGBA", rgba.size, (0, 0, 0, 0))
    cleaned_pixels = cleaned.load()
    for x, y in keep:
        cleaned_pixels[x, y] = target[x, y]
    return cleaned


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


def normalize(sprite: Image.Image, shared_scale: float) -> Image.Image:
    crop = sprite.crop(sprite.getbbox())
    size = (
        max(1, round(crop.width * shared_scale)),
        max(1, round(crop.height * shared_scale)),
    )
    resized = crop.resize(size, Image.Resampling.NEAREST)
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
    parser.add_argument("--approved-idle", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--frames-dir", required=True)
    parser.add_argument("--json-out", required=True)
    args = parser.parse_args()

    generated_path = Path(args.generated_source).resolve()
    approved_path = Path(args.approved_idle).resolve()
    output_path = Path(args.output).resolve()
    frames_dir = Path(args.frames_dir).resolve()
    json_path = Path(args.json_out).resolve()

    with Image.open(generated_path) as opened:
        generated = opened.convert("RGBA")
    with Image.open(approved_path) as opened:
        approved_source = hard_alpha_largest_component(opened)

    source_frames: list[Image.Image] = []
    for index in range(len(FRAME_LABELS)):
        left = round(index * generated.width / len(FRAME_LABELS))
        right = round((index + 1) * generated.width / len(FRAME_LABELS))
        frame = hard_alpha_largest_component(generated.crop((left, 0, right, generated.height)))
        if frame.getbbox() is None:
            raise ValueError(f"generated frame {index + 1} is empty")
        source_frames.append(frame)

    shared_scale = TARGET_HEIGHT / max(frame.getbbox()[3] - frame.getbbox()[1] for frame in source_frames)
    normalized_generated = [normalize(frame, shared_scale) for frame in source_frames]
    approved_scale = TARGET_HEIGHT / (approved_source.getbbox()[3] - approved_source.getbbox()[1])
    approved_idle = normalize(approved_source, approved_scale)

    source_indices: list[int | None] = [None, 1, 2, 3, 4, None]
    frames = [
        normalized_generated[source_index] if source_index is not None else approved_idle.copy()
        for source_index in source_indices
    ]

    approved_body = approved_idle.crop((0, BODY_LOCK_Y, CELL_SIZE[0], CELL_SIZE[1]))
    for index in range(len(frames)):
        locked = Image.new("RGBA", CELL_SIZE, (0, 0, 0, 0))
        locked.alpha_composite(frames[index].crop((0, 0, CELL_SIZE[0], BODY_LOCK_Y)), (0, 0))
        locked.alpha_composite(approved_body, (0, BODY_LOCK_Y))
        frames[index] = locked

    output = Image.new("RGBA", OUTPUT_SIZE, (0, 0, 0, 0))
    frames_dir.mkdir(parents=True, exist_ok=True)
    reports: list[dict[str, object]] = []
    for index, (label, frame) in enumerate(zip(FRAME_LABELS, frames)):
        bbox = frame.getbbox()
        if bbox is None:
            raise ValueError(f"normalized {label} is empty")
        frame_components = components(frame)
        alpha_values = [value for value, count in enumerate(frame.getchannel("A").histogram()) if count]
        hidden_rgb_clear = all(pixel[:3] == (0, 0, 0) for pixel in frame.getdata() if pixel[3] == 0)
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
    head_centers = [float(frame["head_center_x"]) for frame in reports]
    checks = {
        "dimensions_1152x208": output.size == OUTPUT_SIZE,
        "mode_rgba": output.mode == "RGBA",
        "six_nonempty_192x208_cells": all(frame["bbox"] for frame in reports),
        "frame_1_exact_approved_idle": exact_equal(frames[0], approved_idle),
        "frame_6_exact_loop_return": exact_equal(frames[5], frames[0]),
        "baseline_y_203": all(frame["baseline_y"] == TARGET_BASELINE for frame in reports),
        "body_center_stable_near_96": max(body_centers) - min(body_centers) <= 1.0
        and all(abs(center - 96.0) <= 1.5 for center in body_centers),
        "body_arms_hands_legs_feet_pixel_locked": all(
            exact_equal(frame.crop((0, BODY_LOCK_Y, CELL_SIZE[0], CELL_SIZE[1])), approved_body)
            for frame in frames
        ),
        "adjacent_head_registration_continuous": max(
            abs(right - left) for left, right in zip(head_centers, head_centers[1:] + head_centers[:1])
        ) <= 8.0,
        "no_clipping": all(min(frame["margins"].values()) >= 4 for frame in reports),
        "no_isolated_pixels": all(frame["component_count"] == 1 for frame in reports),
        "binary_alpha_no_antialias": all(frame["alpha_values"] == [0, 255] for frame in reports),
        "hidden_background_rgb_clear": all(frame["hidden_rgb_clear"] for frame in reports),
        "nearest_neighbor_only": True,
    }
    report = {
        "ok": all(checks.values()),
        "generated_source": str(generated_path),
        "generated_source_sha256": digest(generated_path),
        "approved_idle": str(approved_path),
        "approved_idle_sha256": digest(approved_path),
        "output": str(output_path),
        "output_sha256": digest(output_path),
        "output_size": list(output.size),
        "mode": output.mode,
        "frame_labels": list(FRAME_LABELS),
        "body_lock_y": BODY_LOCK_Y,
        "resampling": "nearest-neighbor",
        "checks": checks,
        "frames": reports,
        "manual_review": {
            "idle_action_sequence": "pending",
            "loop_6_to_1": "pending",
            "approved_identity_match": "pending",
        },
    }
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": report["ok"], "checks": checks}, indent=2))
    raise SystemExit(0 if report["ok"] else 1)


if __name__ == "__main__":
    main()
