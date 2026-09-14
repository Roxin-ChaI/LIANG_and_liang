#!/usr/bin/env python3
"""Assemble the approved feng-v2 rows without changing any frame pixels."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from PIL import Image


CELL_WIDTH = 192
CELL_HEIGHT = 208
COLUMNS = 8
ROWS = 11
ATLAS_SIZE = (COLUMNS * CELL_WIDTH, ROWS * CELL_HEIGHT)
ROW_SPECS = (
    ("idle", 6, "jobs/idle/decoded/idle.png"),
    ("running-right", 8, "jobs/running-right/decoded/running-right.png"),
    ("running-left", 8, "jobs/running-left/decoded/running-left.png"),
    ("waving", 4, "jobs/waving/decoded/waving.png"),
    ("jumping", 5, "jobs/jumping/decoded/jumping.png"),
    ("failed", 8, "jobs/failed/decoded/failed.png"),
    ("waiting", 6, "jobs/waiting/decoded/waiting.png"),
    ("running", 6, "jobs/running/decoded/running.png"),
    ("review", 6, "jobs/review/decoded/review.png"),
    ("look-row-9", 8, "jobs/look-row-9/decoded/look-row-9.png"),
    ("look-row-10", 8, "jobs/look-row-10/decoded/look-row-10.png"),
)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def is_clear(image: Image.Image) -> bool:
    return not any(image.tobytes())


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--png-output", required=True)
    parser.add_argument("--webp-output", required=True)
    parser.add_argument("--frames-root", required=True)
    parser.add_argument("--json-out", required=True)
    args = parser.parse_args()

    run_dir = Path(args.run_dir).expanduser().resolve()
    png_output = Path(args.png_output).expanduser().resolve()
    webp_output = Path(args.webp_output).expanduser().resolve()
    frames_root = Path(args.frames_root).expanduser().resolve()
    json_out = Path(args.json_out).expanduser().resolve()

    atlas = Image.new("RGBA", ATLAS_SIZE, (0, 0, 0, 0))
    cell_reports: list[dict[str, object]] = []
    source_reports: list[dict[str, object]] = []

    for row_index, (state, frame_count, relative_path) in enumerate(ROW_SPECS):
        source_path = run_dir / relative_path
        with Image.open(source_path) as opened:
            source_mode = opened.mode
            source_format = opened.format
            strip = opened.copy()
        expected_size = (frame_count * CELL_WIDTH, CELL_HEIGHT)
        if strip.size != expected_size:
            raise SystemExit(f"{state}: expected {expected_size}, got {strip.size}")
        if source_mode != "RGBA":
            raise SystemExit(f"{state}: expected RGBA source, got {source_mode}")

        source_reports.append(
            {
                "state": state,
                "row": row_index,
                "path": str(source_path),
                "sha256": sha256_file(source_path),
                "size": list(strip.size),
                "mode": source_mode,
                "format": source_format,
                "frame_count": frame_count,
            }
        )
        state_frames = frames_root / state
        state_frames.mkdir(parents=True, exist_ok=True)
        for column_index in range(frame_count):
            box = (
                column_index * CELL_WIDTH,
                0,
                (column_index + 1) * CELL_WIDTH,
                CELL_HEIGHT,
            )
            cell = strip.crop(box)
            if cell.getbbox() is None:
                raise SystemExit(f"{state} column {column_index} is empty")
            x = column_index * CELL_WIDTH
            y = row_index * CELL_HEIGHT
            atlas.paste(cell, (x, y))
            frame_path = state_frames / f"{column_index:02d}.png"
            cell.save(frame_path)
            cell_reports.append(
                {
                    "state": state,
                    "row": row_index,
                    "column": column_index,
                    "source_box": list(box),
                    "sha256_rgba": sha256_bytes(cell.tobytes()),
                    "output_frame": str(frame_path),
                }
            )

    idle_neutral = atlas.crop((0, 0, CELL_WIDTH, CELL_HEIGHT))
    neutral_x = 6 * CELL_WIDTH
    atlas.paste(idle_neutral, (neutral_x, 0))
    cell_reports.append(
        {
            "state": "neutral",
            "row": 0,
            "column": 6,
            "source": "idle row 0 column 0",
            "sha256_rgba": sha256_bytes(idle_neutral.tobytes()),
        }
    )

    png_output.parent.mkdir(parents=True, exist_ok=True)
    webp_output.parent.mkdir(parents=True, exist_ok=True)
    json_out.parent.mkdir(parents=True, exist_ok=True)
    atlas.save(png_output, format="PNG")
    atlas.save(
        webp_output,
        format="WEBP",
        lossless=True,
        quality=100,
        method=6,
        exact=True,
    )

    with Image.open(webp_output) as opened:
        webp_mode = opened.mode
        webp = opened.convert("RGBA")
    if webp.tobytes() != atlas.tobytes():
        raise SystemExit("lossless WebP pixels differ from the assembled RGBA atlas")

    unused_cells: list[dict[str, object]] = []
    used_by_row = [6, 8, 8, 4, 5, 8, 6, 6, 6, 8, 8]
    for row_index, used_count in enumerate(used_by_row):
        for column_index in range(COLUMNS):
            valid = column_index < used_count or (row_index == 0 and column_index == 6)
            if valid:
                continue
            cell = atlas.crop(
                (
                    column_index * CELL_WIDTH,
                    row_index * CELL_HEIGHT,
                    (column_index + 1) * CELL_WIDTH,
                    (row_index + 1) * CELL_HEIGHT,
                )
            )
            unused_cells.append(
                {
                    "row": row_index,
                    "column": column_index,
                    "fully_transparent_zero_rgba": is_clear(cell),
                }
            )

    report = {
        "ok": all(cell["fully_transparent_zero_rgba"] for cell in unused_cells),
        "assembly": "exact 192x208 cell copy; no scaling, resampling, or positional changes",
        "sprite_version_number": 2,
        "columns": COLUMNS,
        "rows": ROWS,
        "cell_size": [CELL_WIDTH, CELL_HEIGHT],
        "atlas_size": list(ATLAS_SIZE),
        "png_output": str(png_output),
        "png_sha256": sha256_file(png_output),
        "webp_output": str(webp_output),
        "webp_sha256": sha256_file(webp_output),
        "webp_mode": webp_mode,
        "webp_pixel_exact_to_png": True,
        "sources": source_reports,
        "cells": cell_reports,
        "unused_cells": unused_cells,
    }
    json_out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": report["ok"],
                "atlas_size": report["atlas_size"],
                "sprite_version_number": 2,
                "webp_pixel_exact_to_png": True,
                "webp_sha256": report["webp_sha256"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
