#!/usr/bin/env python3
"""Read-only source attribution and state-pair evidence for the visual audit."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from pathlib import Path

from PIL import Image, ImageChops

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.audit_standalone_visual import ROWS
from tools.run_standalone_app_qa import ROOT


def dark_proxy(image: Image.Image) -> tuple[int, int, int, int]:
    points = []
    rgba = image.convert("RGBA")
    for index, (r, g, b, a) in enumerate(rgba.get_flattened_data()):
        if a >= 128 and r < 100 and g < 100 and b < 110 and abs(r - g) < 35 and abs(g - b) < 55:
            points.append((index % image.width, index // image.width))
    if not points:
        raise ValueError("no dark body proxy")
    return (min(x for x, _ in points), min(y for _, y in points),
            max(x for x, _ in points) + 1, max(y for _, y in points) + 1)


def source_measurements() -> dict:
    result = {"forms": {}, "endpoints": {}}
    for form in ("gu", "feng"):
        path = ROOT / "assets/builds" / form / "spritesheet.webp"
        with Image.open(path) as source:
            atlas = source.convert("RGBA")
        rows = {}
        for name, row, count, _ in ROWS:
            frames = [atlas.crop((index * 192, row * 208, (index + 1) * 192, (row + 1) * 208))
                      for index in range(count)]
            boxes = [image.getchannel("A").getbbox() for image in frames]
            feet = [image.crop((0, 170, 192, 208)).getchannel("A").getbbox() for image in frames]
            rows[name] = {"bounds": boxes, "baselines": [box[3] - 1 for box in boxes],
                          "lowerBodyHullCentersX": [(box[0] + box[2]) / 2 for box in feet],
                          "identicalAdjacentFrames": [index for index in range(count - 1)
                           if ImageChops.difference(frames[index].convert("RGB"),
                                                    frames[index + 1].convert("RGB")).getbbox() is None]}
        result["forms"][form] = {"sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "rows": rows}
    layouts = json.loads((ROOT / "runtime-patch/fixtures/transition-overlay-layout.json").read_text())
    for direction, count in (("gu_to_feng", 10), ("feng_to_gu", 8)):
        layout = layouts[direction]
        for number in (1, count):
            path = ROOT / "assets/transform-overlay" / direction / f"{direction}_{number:02d}.png"
            with Image.open(path) as image:
                box = dark_proxy(image)
            registered = [box[0] + layout["offsetLeft"], box[1] + layout["offsetTop"],
                          box[2] + layout["offsetLeft"], box[3] + layout["offsetTop"]]
            result["endpoints"][f"{direction}-{number:02d}"] = {
                "darkBodyProxyRegisteredBox": registered,
                "centerX": (registered[0] + registered[2]) / 2,
                "baseline": registered[3] - 1,
                "note": "dark-color extrema exclude aura; not an anatomical head/shoulder segmentation",
            }
    return result


def compile_pairs(raw: Path, output: Path) -> dict:
    output.mkdir(parents=True, exist_ok=True)
    result = {}
    for form in ("gu", "feng"):
        report = json.loads((raw / form / f"{form}-state-pairs.json").read_text())
        shutil.copy2(raw / form / f"{form}-state-pairs.png", output / f"{form}-state-pairs.png")
        result[form] = {"pairs": [
            {"from": item["from"], "to": item["to"], "row": item["renderer"]["row"],
             "empty": item["empty"], "touchesWindowEdge": item["touchesWindowEdge"]}
            for item in report["pairs"]],
            "finiteHandoffs": [{"from": item["from"], "row": item["renderer"]["row"],
                                 "frame": item["renderer"]["frame"]} for item in report["finiteHandoffs"]],
            "coverageNote": report["coverageNote"]}
    (output / "state-pair-coverage.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state-pairs", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    compile_pairs(args.state_pairs, args.output)
    sources = source_measurements()
    (args.output / "source-attribution.json").write_text(json.dumps(sources, indent=2) + "\n")
    print(json.dumps({"output": str(args.output), "guBaseline": {
        name: row["baselines"] for name, row in sources["forms"]["gu"]["rows"].items()}}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
