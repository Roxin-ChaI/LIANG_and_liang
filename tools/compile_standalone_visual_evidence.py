#!/usr/bin/env python3
"""Curate actual QA2 window captures into reviewable, non-source QA evidence."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.audit_standalone_visual import ROWS


def selected(trace: dict, form: str) -> dict[str, dict[int, dict]]:
    result = {}
    for name, row, count, _ in ROWS:
        frames = {}
        for item in trace["captures"]:
            render = item.get("rendered") or {}
            if render.get("form") == form and render.get("row") == row and render.get("state") == name:
                index = render.get("frame")
                if isinstance(index, int) and 0 <= index < count and index not in frames:
                    frames[index] = item
        result[name] = frames
    return result


def alpha_metrics(frames: dict[int, dict], scale: int) -> dict:
    bounds = [item["geometry"]["bbox"] for item in frames.values()]
    baselines = [round((box[3] - 1) / scale, 2) for box in bounds if box]
    centers = [round((box[0] + box[2]) / (2 * scale), 2) for box in bounds if box]
    differences = []
    for a, b in zip(sorted(frames), sorted(frames)[1:]):
        with Image.open(frames[a]["file"]) as first, Image.open(frames[b]["file"]) as second:
            # RGBA getbbox() consults alpha and misses eye-color changes whose
            # alpha mask stays fixed. Compare RGB and alpha independently.
            rgb = ImageChops.difference(first.convert("RGB"), second.convert("RGB"))
            alpha = ImageChops.difference(first.getchannel("A"), second.getchannel("A"))
            differences.append({"from": a, "to": b,
                                "rgbBbox": rgb.getbbox(), "alphaBbox": alpha.getbbox()})
    return {"capturedFrames": sorted(frames), "baselinesCssPx": baselines,
            "overallAlphaCentersCssPx": centers, "adjacentDifference": differences}


def look_sheet(look: list[dict], destination: Path) -> None:
    sheet = Image.new("RGBA", (8 * 192, 2 * 236), (35, 35, 35, 255))
    draw = ImageDraw.Draw(sheet)
    for index, item in enumerate(look):
        x, y = (index % 8) * 192, (index // 8) * 236
        draw.text((x + 3, y + 3), f"{index * 22.5:05.1f}", fill="white")
        with Image.open(item["file"]) as image:
            rgba = image.convert("RGBA")
        if rgba.size == (512, 512):
            rgba = rgba.resize((256, 256), Image.Resampling.NEAREST)
        sheet.alpha_composite(rgba.crop((32, 24, 224, 232)), (x, y + 24))
    sheet.save(destination)


def comparison(first: Path, second: Path, destination: Path, labels: tuple[str, str]) -> None:
    canvas = Image.new("RGBA", (512, 280), (35, 35, 35, 255))
    draw = ImageDraw.Draw(canvas)
    for index, (path, label) in enumerate(((first, labels[0]), (second, labels[1]))):
        with Image.open(path) as source:
            image = source.convert("RGBA")
        if image.size == (512, 512):
            image = image.resize((256, 256), Image.Resampling.NEAREST)
        canvas.alpha_composite(image, (index * 256, 24))
        draw.text((index * 256 + 5, 3), label, fill="white")
    canvas.save(destination)


def compile_evidence(raw_2x: Path, raw_1x: Path, output: Path) -> dict:
    output.mkdir(parents=True, exist_ok=True)
    report = {"captureKind": "Electron webContents.capturePage of isolated QA2 window",
              "displayScaleNote": "1x and 2x forced device-scale-factor; external Retina monitor not proven",
              "forms": {}}
    selection = {}
    for form in ("gu", "feng"):
        source = raw_2x / form
        trace = json.loads((source / f"{form}-2x-trace.json").read_text())
        trace_1x = json.loads((raw_1x / form / f"{form}-1x-trace.json").read_text())
        frames = selected(trace, form)
        selection[form] = frames
        look_sheet(trace["lookCaptures"], output / f"{form}-look-directions.png")
        for suffix in ("contact-sheet.png", "window-recording.gif"):
            shutil.copy2(source / f"{form}-2x-{suffix}", output / f"{form}-{suffix}")
        report["forms"][form] = {
            "2xCaptureCount": len(trace["captures"]), "1xCaptureCount": len(trace_1x["captures"]),
            "2xMissingFrames": trace["missingFrames"], "1xMissingFrames": trace_1x["missingFrames"],
            "rows": {name: alpha_metrics(items, 2) for name, items in frames.items()},
            "lookCount": len(trace["lookCaptures"]),
        }
    comparison(Path(selection["gu"]["idle"][0]["file"]),
               Path(selection["gu"]["running"][0]["file"]),
               output / "gu-idle-vs-running-baseline.png", ("Gu Idle", "Gu Running"))
    comparison(Path(selection["feng"]["failed"][0]["file"]),
               Path(selection["feng"]["failed"][4]["file"]),
               output / "feng-failed-frame-0-vs-4.png", ("Feng Failed 0", "Feng Failed 4"))
    (output / "metrics.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-2x", type=Path, required=True)
    parser.add_argument("--raw-1x", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = compile_evidence(args.raw_2x, args.raw_1x, args.output)
    print(json.dumps({"output": str(args.output), "forms": list(report["forms"])}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
