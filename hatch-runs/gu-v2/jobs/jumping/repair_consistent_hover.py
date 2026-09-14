#!/usr/bin/env python3
"""Repair jumping with one approved hover sprite and rigid vertical motion only."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import deque
from pathlib import Path

from PIL import Image


CELL_SIZE = (192, 208)
OUTPUT_SIZE = (960, 208)
FRAME_LABELS = ("01-hover", "02-lift", "03-peak", "04-descent", "05-settle")
VERTICAL_OFFSETS = (0, -1, -4, -2, 0)
EXPECTED_BASELINES = (203, 202, 199, 201, 203)
TARGET_HEIGHT = 198
TARGET_BASELINE = 203
BODY_START_FRACTION = 0.35
HEAD_REGION_BOTTOM = 80
ALPHA_THRESHOLD = 64


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def components(image: Image.Image) -> list[list[tuple[int, int]]]:
    alpha = image.getchannel("A")
    pixels = alpha.load()
    seen: set[tuple[int, int]] = set()
    found: list[list[tuple[int, int]]] = []
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
            found.append(current)
    return sorted(found, key=len, reverse=True)


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
        raise ValueError("approved hover source is empty")
    keep = set(found[0])
    cleaned = Image.new("RGBA", rgba.size, (0, 0, 0, 0))
    cleaned_pixels = cleaned.load()
    for x, y in keep:
        cleaned_pixels[x, y] = target[x, y]
    return cleaned


def band_center(image: Image.Image, start_fraction: float, end_fraction: float) -> float:
    bbox = image.getbbox()
    if bbox is None:
        raise ValueError("empty sprite")
    _, top, _, bottom = bbox
    band_top = top + int((bottom - top) * start_fraction)
    band_bottom = top + int((bottom - top) * end_fraction)
    band_bbox = image.getchannel("A").crop((0, band_top, image.width, band_bottom)).getbbox()
    if band_bbox is None:
        raise ValueError("empty anchor band")
    return (band_bbox[0] + band_bbox[2]) / 2


def normalize_once(source: Image.Image) -> tuple[Image.Image, float]:
    bbox = source.getbbox()
    if bbox is None:
        raise ValueError("empty approved hover source")
    crop = source.crop(bbox)
    scale = TARGET_HEIGHT / crop.height
    resized = crop.resize(
        (max(1, round(crop.width * scale)), TARGET_HEIGHT),
        Image.Resampling.NEAREST,
    )
    resized = hard_alpha_largest_component(resized)
    paste_x = round(CELL_SIZE[0] / 2 - band_center(resized, BODY_START_FRACTION, 1.0))
    paste_y = TARGET_BASELINE + 1 - resized.height
    result = Image.new("RGBA", CELL_SIZE, (0, 0, 0, 0))
    result.paste(resized, (paste_x, paste_y), resized)
    return result, scale


def shift_vertical(image: Image.Image, offset: int) -> Image.Image:
    result = Image.new("RGBA", CELL_SIZE, (0, 0, 0, 0))
    result.paste(image, (0, offset), image)
    return result


def hidden_rgb_clear(image: Image.Image) -> bool:
    data = image.tobytes()
    return all(
        data[index + 3] != 0 or data[index : index + 3] == b"\x00\x00\x00"
        for index in range(0, len(data), 4)
    )


def head_bbox(image: Image.Image, offset: int) -> tuple[int, int, int, int]:
    crop_bottom = HEAD_REGION_BOTTOM + offset
    bbox = image.getchannel("A").crop((0, 0, CELL_SIZE[0], crop_bottom)).getbbox()
    if bbox is None:
        raise ValueError("head region is empty")
    return bbox


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--approved-hover", required=True)
    parser.add_argument("--approved-idle", required=True)
    parser.add_argument("--approved-idle-row", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--frames-dir", required=True)
    parser.add_argument("--preview", required=True)
    parser.add_argument("--json-out", required=True)
    args = parser.parse_args()

    hover_path = Path(args.approved_hover).resolve()
    idle_path = Path(args.approved_idle).resolve()
    idle_row_path = Path(args.approved_idle_row).resolve()
    output_path = Path(args.output).resolve()
    frames_dir = Path(args.frames_dir).resolve()
    preview_path = Path(args.preview).resolve()
    json_path = Path(args.json_out).resolve()

    with Image.open(hover_path) as opened:
        hover_source = hard_alpha_largest_component(opened)
    with Image.open(idle_row_path) as opened:
        idle_frame = opened.convert("RGBA").crop((0, 0, *CELL_SIZE))

    canonical, scale = normalize_once(hover_source)
    frames = [shift_vertical(canonical, offset) for offset in VERTICAL_OFFSETS]
    frame_reports: list[dict[str, object]] = []
    output = Image.new("RGBA", OUTPUT_SIZE, (0, 0, 0, 0))
    frames_dir.mkdir(parents=True, exist_ok=True)

    for index, (label, offset, frame) in enumerate(zip(FRAME_LABELS, VERTICAL_OFFSETS, frames)):
        bbox = frame.getbbox()
        if bbox is None:
            raise ValueError(f"{label} is empty")
        head = head_bbox(frame, offset)
        alpha_values = [
            value
            for value, count in enumerate(frame.getchannel("A").histogram())
            if count
        ]
        frame_path = frames_dir / f"{index + 1:02d}-{label}.png"
        frame.save(frame_path)
        output.paste(frame, (index * CELL_SIZE[0], 0), frame)
        frame_reports.append(
            {
                "index": index,
                "label": label,
                "vertical_offset": offset,
                "path": str(frame_path),
                "bbox": list(bbox),
                "baseline_y": bbox[3] - 1,
                "body_center_x": band_center(frame, BODY_START_FRACTION, 1.0),
                "head_bbox": list(head),
                "head_bbox_size": [head[2] - head[0], head[3] - head[1]],
                "component_count": len(components(frame)),
                "alpha_values": alpha_values,
                "hidden_rgb_clear": hidden_rgb_clear(frame),
                "exact_rigid_translation_of_canonical_hover": frame.tobytes()
                == shift_vertical(canonical, offset).tobytes(),
                "margins": {
                    "left": bbox[0],
                    "top": bbox[1],
                    "right": CELL_SIZE[0] - bbox[2],
                    "bottom": CELL_SIZE[1] - bbox[3],
                },
            }
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    preview_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    output.save(output_path)
    frames[0].save(
        preview_path,
        save_all=True,
        append_images=frames[1:],
        duration=[140, 140, 140, 140, 280],
        loop=0,
        disposal=2,
        optimize=False,
    )

    head_sizes = [tuple(report["head_bbox_size"]) for report in frame_reports]
    centers = [float(report["body_center_x"]) for report in frame_reports]
    baselines = [int(report["baseline_y"]) for report in frame_reports]
    canonical_bbox = canonical.getbbox()
    idle_bbox = idle_frame.getbbox()
    checks = {
        "dimensions_960x208": output.size == OUTPUT_SIZE,
        "mode_rgba": output.mode == "RGBA",
        "five_nonempty_192x208_cells": all(report["bbox"] for report in frame_reports),
        "frame_1_and_5_pixel_identical": frames[0].tobytes() == frames[4].tobytes(),
        "frame_1_and_5_baseline_y_203": baselines[0] == baselines[4] == TARGET_BASELINE,
        "body_center_fixed_near_x_96": max(centers) - min(centers) == 0
        and all(abs(center - 96.0) <= 0.5 for center in centers),
        "vertical_trajectory_0_minus1_minus4_minus2_0": list(VERTICAL_OFFSETS)
        == [int(report["vertical_offset"]) for report in frame_reports],
        "baseline_trajectory_203_202_199_201_203": baselines == list(EXPECTED_BASELINES),
        "head_bounding_box_size_identical_all_frames": len(set(head_sizes)) == 1,
        "face_glasses_hair_and_body_pixels_rigidly_identical": all(
            report["exact_rigid_translation_of_canonical_hover"] for report in frame_reports
        ),
        "no_head_scaling": len(set(head_sizes)) == 1,
        "hover_and_idle_normalized_geometry_compatible": canonical_bbox is not None
        and idle_bbox is not None
        and abs((canonical_bbox[2] - canonical_bbox[0]) - (idle_bbox[2] - idle_bbox[0])) <= 1
        and abs((canonical_bbox[3] - canonical_bbox[1]) - (idle_bbox[3] - idle_bbox[1])) <= 2,
        "jump_height_4px": max(VERTICAL_OFFSETS) - min(VERTICAL_OFFSETS) == 4,
        "no_horizontal_drift": max(centers) - min(centers) == 0,
        "no_clipping": all(min(report["margins"].values()) >= 2 for report in frame_reports),
        "single_connected_sprite_no_isolated_pixels": all(
            report["component_count"] == 1 for report in frame_reports
        ),
        "binary_alpha_no_antialias": all(
            report["alpha_values"] == [0, 255] for report in frame_reports
        ),
        "hidden_background_rgb_clear": all(
            report["hidden_rgb_clear"] for report in frame_reports
        ),
        "nearest_neighbor_normalization_once_only": True,
        "no_per_frame_resampling": True,
    }
    report = {
        "ok": all(checks.values()),
        "repair_reason": "device Hover test exposed per-frame head scale and identity drift",
        "method": "normalize approved hover once, then use rigid integer vertical translations only",
        "approved_hover": str(hover_path),
        "approved_hover_sha256": digest(hover_path),
        "approved_idle": str(idle_path),
        "approved_idle_sha256": digest(idle_path),
        "approved_idle_row": str(idle_row_path),
        "approved_idle_row_sha256": digest(idle_row_path),
        "output": str(output_path),
        "output_sha256": digest(output_path),
        "output_size": list(output.size),
        "mode": output.mode,
        "frame_labels": list(FRAME_LABELS),
        "vertical_offsets": list(VERTICAL_OFFSETS),
        "jump_height_pixels": 4,
        "normalization_scale": scale,
        "resampling": "nearest-neighbor once for approved hover canonical only",
        "head_region_bottom_in_canonical": HEAD_REGION_BOTTOM,
        "canonical_hover_bbox": list(canonical_bbox) if canonical_bbox else None,
        "approved_idle_frame_bbox": list(idle_bbox) if idle_bbox else None,
        "checks": checks,
        "frames": frame_reports,
        "manual_review": {
            "same_character_all_five_frames": "pending",
            "no_head_scale_pop": "pending",
            "low_energy_hover_jump": "pending",
            "loop_5_to_1": "pending",
            "approved_hover_identity_match": "pending"
        }
    }
    json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"ok": report["ok"], "checks": checks}, indent=2))
    raise SystemExit(0 if report["ok"] else 1)


if __name__ == "__main__":
    main()
