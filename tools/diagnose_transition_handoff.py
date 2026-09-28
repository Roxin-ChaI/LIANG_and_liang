#!/usr/bin/env python3
"""Read-only rigid-registration feasibility, using existing canonical/overlay pixels."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

ROOT = Path(__file__).resolve().parents[1]
BANDS = {"head": (0, 70), "shoulders": (80, 120), "shoes": (190, 208)}


def anchors(image: Image.Image) -> dict:
    result = {}
    for name, (top, bottom) in BANDS.items():
        points = []
        rgba = image.convert("RGBA")
        for y in range(top, bottom):
            for x in range(rgba.width):
                r, g, b, a = rgba.getpixel((x, y))
                if a >= 128 and r < 100 and g < 100 and b < 110 and abs(r - g) < 35 and abs(g - b) < 55:
                    points.append((x, y))
        if not points:
            raise ValueError(f"empty {name} dark-body anchor")
        left, right = min(x for x, _ in points), max(x for x, _ in points) + 1
        result[name] = {"centerX": (left + right) / 2, "width": right - left,
                        "top": min(y for _, y in points), "bottom": max(y for _, y in points)}
    return result


def rigid_alignment(canonical: dict, endpoint: dict) -> dict:
    candidates = []
    for dx in range(-16, 17):
        residuals = {name: endpoint[name]["centerX"] + dx - canonical[name]["centerX"] for name in BANDS}
        candidates.append((sum(abs(value) for value in residuals.values()), abs(dx), dx, residuals))
    _, _, dx, residuals = min(candidates, key=lambda item: item[:3])
    return {"bestIntegerDx": dx, "centerResiduals": residuals,
            "maximumResidual": max(abs(value) for value in residuals.values()),
            "rigidAnchorPass": max(abs(value) for value in residuals.values()) <= 2,
            "note": "proxy geometry only; a pass cannot certify facial/pose identity"}


def analyze(direction: str, gu_atlas: Path, output: Path) -> dict:
    output.mkdir(parents=True, exist_ok=True)
    layouts = json.loads((ROOT / "runtime-patch/fixtures/transition-overlay-layout.json").read_text())
    number = 1 if direction == "gu_to_feng" else 8
    path = ROOT / "assets/transform-overlay" / direction / f"{direction}_{number:02d}.png"
    layout = layouts[direction]
    with Image.open(path) as image:
        projected = Image.new("RGBA", (192, 208))
        projected.paste(image.convert("RGBA"), (layout["offsetLeft"], layout["offsetTop"]))
    with Image.open(gu_atlas) as image:
        atlas = image.convert("RGBA")
    results = []
    sheet = Image.new("RGBA", (3 * 192, 2 * 236), (35, 35, 35, 255))
    draw = ImageDraw.Draw(sheet)
    for line, (mode, row) in enumerate((("idle", 0), ("running", 7))):
        normal = atlas.crop((0, row * 208, 192, (row + 1) * 208))
        reference, observed = anchors(normal), anchors(projected)
        plan = rigid_alignment(reference, observed)
        adjusted = Image.new("RGBA", normal.size)
        adjusted.paste(projected, (plan["bestIntegerDx"], 0))
        for column, (label, value) in enumerate((("canonical", normal), ("endpoint", projected),
                                                ("best rigid dx (diagnostic)", adjusted))):
            x, y = column * 192, line * 236
            draw.text((x + 2, y + 2), f"{mode} {label}", fill="white")
            sheet.alpha_composite(value, (x, y + 24))
        results.append({"mode": mode, "canonicalAnchors": reference, "endpointAnchors": observed,
                        "alignment": plan,
                        "status": "MANUAL_VISUAL_QA" if plan["rigidAnchorPass"] else "RIGID_ALIGNMENT_INSUFFICIENT",
                        "reason": "proxy geometry does not certify facial/arm/torso pose continuity"})
    sheet.save(output / f"{direction}-rigid-candidates.png")
    report = {"direction": direction, "endpointFrame": number - 1, "guAtlas": str(gu_atlas),
              "projectionNote": "diagnostic crop of normal pet area excludes oversized aura; actual App uses full overlay",
              "cases": results, "appliedToRuntime": False}
    (output / f"{direction}-feasibility.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--direction", choices=("gu_to_feng", "feng_to_gu"), required=True)
    parser.add_argument("--gu-atlas", type=Path, default=ROOT / "assets/rework/v0.1.0/gu/spritesheet.webp")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = analyze(args.direction, args.gu_atlas, args.output)
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
