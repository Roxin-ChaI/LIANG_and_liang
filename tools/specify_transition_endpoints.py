#!/usr/bin/env python3
"""Extract QA references only: canonical endpoint pixels never invent new poses."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
GU = ROOT / "assets/rework/v0.1.0/gu/spritesheet.webp"
FENG = ROOT / "assets/builds/feng/spritesheet.webp"


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def reference(image: Image.Image) -> dict:
    def region(box):
        bbox = image.crop(box).getchannel("A").getbbox()
        return [bbox[0] + box[0], bbox[1] + box[1], bbox[2] + box[0], bbox[3] + box[1]] if bbox else None
    return {"alphaBbox": image.getchannel("A").getbbox(),
            "headReferenceBbox": region((0, 0, 192, 70)),
            "bodyReferenceBbox": region((0, 70, 192, 208)),
            "shoeReferenceBbox": region((0, 190, 192, 208)),
            "pixelSha256": sha(image.tobytes()),
            "referenceNote": "fixed pixel bands are QA reference regions, not anatomical segmentation"}


def build(output: Path) -> dict:
    output.mkdir(parents=True, exist_ok=True)
    poses = []
    sheet = Image.new("RGBA", (7 * 192, 2 * 252), (35, 35, 35, 255))
    draw = ImageDraw.Draw(sheet)
    for line, (form, source) in enumerate((("gu", GU), ("feng", FENG))):
        with Image.open(source) as opened:
            atlas = opened.convert("RGBA")
        for column, (state, frame) in enumerate([("idle", 0)] + [("running", i) for i in range(6)]):
            row = 0 if state == "idle" else 7
            cell = atlas.crop((frame * 192, row * 208, (frame + 1) * 192, (row + 1) * 208))
            filename = f"{form}-{state}-{frame:02d}.png"
            cell.save(output / filename)
            item = {"form": form, "state": state, "row": row, "frame": frame,
                    "referenceFile": filename, "atlas": source.relative_to(ROOT).as_posix(),
                    "atlasSha256": sha(source.read_bytes()), **reference(cell)}
            if item["alphaBbox"][3] - 1 != 203:
                raise ValueError(f"noncanonical grounded baseline: {filename}")
            poses.append(item)
            x, y = column * 192, line * 252
            sheet.alpha_composite(cell, (x, y + 26))
            draw.text((x + 3, y + 3), f"{form} {state} {frame}", fill="white")
            draw.line((x, y + 229, x + 191, y + 229), fill=(220, 110, 80, 255))
            draw.line((x + 96, y + 26, x + 96, y + 233), fill=(80, 110, 160, 180))
    sheet.save(output / "canonical-reference-sheet.png")
    layouts = json.loads((ROOT / "runtime-patch/fixtures/transition-overlay-layout.json").read_text())
    result = {"schemaVersion": 1, "status": "SPECIFICATION_ONLY",
              "normalCell": [192, 208], "logicalAnchor": {"x": 96, "baselineY": 203},
              "bboxConvention": "half-open [left,top,right,bottom], normal-cell coordinates",
              "canonicalGu": "gu-idle-00.png", "canonicalFeng": "feng-idle-00.png",
              "stateMatchedReferences": poses,
              "handoffRule": "Idle uses canonical frame0; Running uses the actual displayed row7 frame, not forced Idle",
              "endpointRule": "subject RGBA equals the matching canonical reference at entry0/exitLast; no boundary-only recolor/translate/scale",
              "subjectMasks": "manual subject/effect masks required for any reauthored effect-bearing frame; blue-color threshold is not a subject mask",
              "directions": {name: {"frameCount": count, "layout": layouts[name],
                    "effectRegionInNormalCoordinates": [layouts[name]["offsetLeft"], layouts[name]["offsetTop"],
                        layouts[name]["offsetLeft"] + layouts[name]["canvasWidth"],
                        layouts[name]["offsetTop"] + layouts[name]["canvasHeight"]],
                    "endpointEffects": "none at start0 and final endpoint; no foreground effect occlusion of face/torso",
                    "interiorEffects": "secondary, hard-edge, attached/peripheral; retain 4px canvas safety margin"}
                  for name, count in (("gu_to_feng", 10), ("feng_to_gu", 8))},
              "approval": "new artwork needs independent visual approval; geometry is necessary, not sufficient",
              "animationFilesGenerated": False}
    (output / "endpoint-specification.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = build(args.output)
    print(json.dumps({"status": result["status"], "referenceCount": len(result["stateMatchedReferences"])}))


if __name__ == "__main__":
    main()
