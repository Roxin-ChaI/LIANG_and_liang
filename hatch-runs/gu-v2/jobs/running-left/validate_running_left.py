#!/usr/bin/env python3
"""Validate Liang Wengu's deterministic eight-frame running-left row."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import deque
from pathlib import Path

from PIL import Image, ImageChops, ImageOps


CELL_WIDTH = 192
CELL_HEIGHT = 208
FRAME_COUNT = 8
OUTPUT_SIZE = (CELL_WIDTH * FRAME_COUNT, CELL_HEIGHT)
TARGET_BASELINE = 203
TORSO_START_FRACTION = 0.28
TORSO_END_FRACTION = 0.68
LABELS = (
    "01-enter-left",
    "02-left-lean",
    "03-left-foot-forward",
    "04-weight-transfer",
    "05-right-foot-follow",
    "06-tired-sway",
    "07-return-near-start",
    "08-loop-transition",
)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def connected_component_count(image: Image.Image) -> int:
    alpha = image.getchannel("A")
    pixels = alpha.load()
    seen: set[tuple[int, int]] = set()
    count = 0
    for y in range(alpha.height):
        for x in range(alpha.width):
            if not pixels[x, y] or (x, y) in seen:
                continue
            count += 1
            queue = deque([(x, y)])
            seen.add((x, y))
            while queue:
                px, py = queue.popleft()
                for ny in range(max(0, py - 1), min(alpha.height, py + 2)):
                    for nx in range(max(0, px - 1), min(alpha.width, px + 2)):
                        point = (nx, ny)
                        if pixels[nx, ny] and point not in seen:
                            seen.add(point)
                            queue.append(point)
    return count


def torso_center(image: Image.Image) -> float:
    bbox = image.getbbox()
    if bbox is None:
        raise ValueError("empty frame")
    _, top, _, bottom = bbox
    band_top = top + int((bottom - top) * TORSO_START_FRACTION)
    band_bottom = top + int((bottom - top) * TORSO_END_FRACTION)
    band_bbox = image.getchannel("A").crop((0, band_top, image.width, band_bottom)).getbbox()
    if band_bbox is None:
        raise ValueError("empty torso band")
    return (band_bbox[0] + band_bbox[2]) / 2


def hidden_rgb_clear(image: Image.Image) -> bool:
    data = image.tobytes()
    for index in range(0, len(data), 4):
        if data[index + 3] == 0 and data[index : index + 3] != b"\x00\x00\x00":
            return False
    return True


def changed_pixels(left: Image.Image, right: Image.Image) -> int:
    data = ImageChops.difference(left, right).tobytes()
    return sum(
        data[index : index + 4] != b"\x00\x00\x00\x00"
        for index in range(0, len(data), 4)
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--running-right", required=True)
    parser.add_argument("--running-left", required=True)
    parser.add_argument("--approved-drag", required=True)
    parser.add_argument("--frames-dir", required=True)
    parser.add_argument("--preview", required=True)
    parser.add_argument("--json-out", required=True)
    args = parser.parse_args()

    right_path = Path(args.running_right).resolve()
    left_path = Path(args.running_left).resolve()
    drag_path = Path(args.approved_drag).resolve()
    frames_dir = Path(args.frames_dir).resolve()
    preview_path = Path(args.preview).resolve()
    json_path = Path(args.json_out).resolve()

    with Image.open(right_path) as opened:
        right_strip = opened.convert("RGBA")
    with Image.open(left_path) as opened:
        left_mode = opened.mode
        left_strip = opened.convert("RGBA")

    frames_dir.mkdir(parents=True, exist_ok=True)
    preview_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.parent.mkdir(parents=True, exist_ok=True)

    frame_reports: list[dict[str, object]] = []
    frames: list[Image.Image] = []
    mirror_matches: list[bool] = []
    for index, label in enumerate(LABELS):
        box = (index * CELL_WIDTH, 0, (index + 1) * CELL_WIDTH, CELL_HEIGHT)
        right_frame = right_strip.crop(box)
        left_frame = left_strip.crop(box)
        expected = ImageOps.mirror(right_frame)
        mirror_match = left_frame.tobytes() == expected.tobytes()
        mirror_matches.append(mirror_match)
        frames.append(left_frame)

        bbox = left_frame.getbbox()
        if bbox is None:
            frame_reports.append({"index": index, "label": label, "empty": True})
            continue

        alpha_values = [
            value
            for value, count in enumerate(left_frame.getchannel("A").histogram())
            if count
        ]
        frame_path = frames_dir / f"{index + 1:02d}-{label}.png"
        left_frame.save(frame_path)
        frame_reports.append(
            {
                "index": index,
                "label": label,
                "path": str(frame_path),
                "bbox": list(bbox),
                "baseline_y": bbox[3] - 1,
                "torso_center_x": torso_center(left_frame),
                "height": bbox[3] - bbox[1],
                "margins": {
                    "left": bbox[0],
                    "top": bbox[1],
                    "right": CELL_WIDTH - bbox[2],
                    "bottom": CELL_HEIGHT - bbox[3],
                },
                "component_count": connected_component_count(left_frame),
                "alpha_values": alpha_values,
                "hidden_rgb_clear": hidden_rgb_clear(left_frame),
                "exact_mirror_of_same_index_right_frame": mirror_match,
            }
        )

    enlarged = [
        frame.resize((CELL_WIDTH * 2, CELL_HEIGHT * 2), Image.Resampling.NEAREST)
        for frame in frames
    ]
    enlarged[0].save(
        preview_path,
        save_all=True,
        append_images=enlarged[1:],
        duration=180,
        loop=0,
        disposal=2,
    )

    adjacent_diffs = [changed_pixels(frames[i], frames[i + 1]) for i in range(7)]
    wrap_diff = changed_pixels(frames[-1], frames[0])
    nonempty_reports = [report for report in frame_reports if not report.get("empty")]
    centers = [float(report["torso_center_x"]) for report in nonempty_reports]
    heights = [int(report["height"]) for report in nonempty_reports]
    checks = {
        "dimensions_1536x208": left_strip.size == OUTPUT_SIZE,
        "mode_rgba": left_mode == "RGBA",
        "eight_nonempty_192x208_cells": len(nonempty_reports) == FRAME_COUNT,
        "exact_framewise_horizontal_mirror_preserving_order": all(mirror_matches),
        "baseline_y_203": all(report["baseline_y"] == TARGET_BASELINE for report in nonempty_reports),
        "torso_center_stable_95_5_to_96_5": centers
        and min(centers) >= 95.5
        and max(centers) <= 96.5,
        "height_199_to_200": heights and min(heights) >= 199 and max(heights) <= 200,
        "safe_margin_at_least_4px": all(
            min(report["margins"].values()) >= 4 for report in nonempty_reports
        ),
        "single_connected_sprite_no_isolated_pixels": all(
            report["component_count"] == 1 for report in nonempty_reports
        ),
        "binary_alpha_no_antialias": all(
            report["alpha_values"] == [0, 255] for report in nonempty_reports
        ),
        "hidden_background_rgb_clear": all(
            report["hidden_rgb_clear"] for report in nonempty_reports
        ),
        "loop_diff_within_adjacent_range": adjacent_diffs
        and min(adjacent_diffs) <= wrap_diff <= max(adjacent_diffs),
        "no_scaling_or_resampling": all(mirror_matches),
    }
    report = {
        "ok": all(checks.values()),
        "derivation": "framewise-horizontal-mirror-preserving-order",
        "imagegen_used": False,
        "running_right": str(right_path),
        "running_right_sha256": digest(right_path),
        "approved_drag": str(drag_path),
        "approved_drag_sha256": digest(drag_path),
        "output": str(left_path),
        "output_sha256": digest(left_path),
        "output_size": list(left_strip.size),
        "mode": left_mode,
        "frame_labels": list(LABELS),
        "adjacent_changed_pixels": adjacent_diffs,
        "wrap_8_to_1_changed_pixels": wrap_diff,
        "checks": checks,
        "frames": frame_reports,
        "manual_review": {
            "screen_left_drag_semantics": "pending",
            "alternating_gait_continuity": "pending",
            "loop_8_to_1": "pending",
            "approved_liang_wengu_identity_match": "pending",
            "mirror_feature_safety": "pending",
        },
    }
    json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"ok": report["ok"], "checks": checks}, indent=2))
    raise SystemExit(0 if report["ok"] else 1)


if __name__ == "__main__":
    main()
