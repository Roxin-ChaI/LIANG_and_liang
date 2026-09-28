#!/usr/bin/env python3
"""Read-only whole-pose reuse/rigid feasibility; never emits substitute animation frames."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from PIL import Image, ImageChops, ImageDraw
from tools.specify_transition_endpoints import ROOT, GU, sha


def different_pixels(first, second):
    channels = ImageChops.difference(first, second).split()
    union = channels[0]
    for channel in channels[1:]:
        union = ImageChops.lighter(union, channel)
    return first.width * first.height - union.histogram()[0]


def assess(output: Path) -> dict:
    output.mkdir(parents=True, exist_ok=True)
    layouts = json.loads((ROOT / "runtime-patch/fixtures/transition-overlay-layout.json").read_text())
    frames, input_hashes = {}, {}
    sheet = Image.new("RGBA", (10 * 240, 2 * 274), (35, 35, 35, 255))
    draw = ImageDraw.Draw(sheet)
    for line, (direction, count) in enumerate((("gu_to_feng", 10), ("feng_to_gu", 8))):
        frames[direction] = []
        for index in range(count):
            path = ROOT / "assets/transform-overlay" / direction / f"{direction}_{index + 1:02d}.png"
            with Image.open(path) as opened:
                image = opened.convert("RGBA")
            input_hashes[path.relative_to(ROOT).as_posix()] = sha(path.read_bytes())
            projected = Image.new("RGBA", (192, 208))
            layout = layouts[direction]
            projected.paste(image, (layout["offsetLeft"], layout["offsetTop"]))
            frames[direction].append(projected)
            sheet.alpha_composite(image, (index * 240, line * 274 + 26))
            draw.text((index * 240 + 2, line * 274 + 2), f"{direction} {index}", fill="white")
    sheet.save(output / "unchanged-source-stages.png")
    with Image.open(GU) as opened:
        atlas = opened.convert("RGBA")
    compare = Image.new("RGBA", (5 * 192, 4 * 236), (35, 35, 35, 255))
    label = ImageDraw.Draw(compare)
    cases = []
    for line, (state, row) in enumerate((("idle", 0), ("running", 7))):
        canonical = atlas.crop((0, row * 208, 192, (row + 1) * 208))
        candidates = []
        for direction, source in frames.items():
            for index, image in enumerate(source):
                for dx in range(-16, 17):
                    adjusted = Image.new("RGBA", (192, 208))
                    adjusted.paste(image, (dx, 0))
                    candidates.append((different_pixels(canonical, adjusted), abs(dx), direction, index, dx))
        best = min(candidates)
        cases.append({"state": state, "canonicalFrame": 0, "testedTranslations": [-16, 16],
                      "verticalTranslation": 0, "sourceFrameCount": 18,
                      "bestWholePoseReuse": {"differentPixels": best[0], "direction": best[2], "frame": best[3], "dx": best[4]},
                      "exactWholePoseMatch": best[0] == 0,
                      "boundaryOnlyForwardNextFrameDifferentPixels": different_pixels(canonical, frames["gu_to_feng"][1]),
                      "boundaryOnlyReversePreviousFrameDifferentPixels": different_pixels(canonical, frames["feng_to_gu"][6])})
        for direction_index, (direction, images, names) in enumerate((
            ("forward", [canonical, frames["gu_to_feng"][0], canonical, frames["gu_to_feng"][1], frames["gu_to_feng"][2]],
             ["current canonical", "old frame0", "boundary-only idea", "unchanged frame1", "unchanged frame2"]),
            ("reverse", [frames["feng_to_gu"][5], frames["feng_to_gu"][6], frames["feng_to_gu"][7], canonical, canonical],
             ["unchanged frame5", "unchanged frame6", "old final frame7", "boundary-only idea", "normal canonical"]),
        )):
            y = (line * 2 + direction_index) * 236
            for column, (image, name) in enumerate(zip(images, names)):
                compare.alpha_composite(image, (column * 192, y + 26))
                label.text((column * 192 + 2, y + 2), f"{state} {direction} {name}", fill="white")
    compare.save(output / "boundary-only-diagnostic.png")
    report = {"status": "NEEDS_MANUAL_ART_REDESIGN", "packagingEligible": False,
              "animationFramesGenerated": False, "sourceFramesModified": False,
              "inputHashes": input_hashes, "cases": cases,
              "scope": "18 frozen whole-pose frames and baseline-preserving integer translations; not proof about every possible hand edit",
              "metricLimit": "pixel differences alone do not establish visual failure; independent pose/neighbor review is mandatory",
              "diagnosticOnly": "projected 192x208 images on comparison sheet may crop aura; full original oversized stages are shown separately",
              "missingWork": "state-matched Gu entrance and late Gu convergence intermediate artwork; no head/body splice or pixel dissolve accepted"}
    (output / "reuse-feasibility.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = assess(args.output)
    print(json.dumps({"status": result["status"], "cases": result["cases"]}, indent=2))
