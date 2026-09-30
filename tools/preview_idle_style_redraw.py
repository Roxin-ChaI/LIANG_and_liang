"""Render an honest QA preview with external Idle holds, not runtime artwork.

All candidate poses share one nearest-neighbor scale. Source PNGs and generated
alpha remain unchanged. Preview registration uses sole center/baseline only;
no per-frame fitting conceals source height or identity differences.
"""
from __future__ import annotations

import json

from PIL import Image, ImageDraw

from tools.package_idle_style_redraw import ROOT, OUT, sha

QA = OUT / "qa"
CANVAS = (256, 296)
ANCHOR_X = 128
BASELINE = 263
NORMAL_ORIGIN = (32, 60)


def visible_bounds(image: Image.Image) -> tuple[int, int, int, int]:
    bounds = image.getchannel("A").point(lambda a: 255 if a >= 128 else 0).getbbox()
    if bounds is None:
        raise ValueError("empty character")
    return bounds


def sole_center(image: Image.Image) -> float:
    _, _, _, bottom = visible_bounds(image)
    pixels = image.load()
    xs = [x for y in range(bottom - 12, bottom) for x in range(image.width)
          if pixels[x, y][3] >= 128 and max(pixels[x, y][:3]) < 110]
    if not xs:
        raise ValueError("no dark shoe pixels in sole band")
    return (min(xs) + max(xs)) / 2


def panel(sprite: Image.Image, position: tuple[int, int], label: str) -> Image.Image:
    result = Image.new("RGBA", CANVAS, (35, 35, 39, 255))
    result.alpha_composite(sprite, position)
    draw = ImageDraw.Draw(result)
    draw.text((8, 8), label, fill="white")
    draw.line((8, BASELINE + 1, CANVAS[0] - 8, BASELINE + 1), fill=(94, 94, 103, 255))
    return result


def main() -> None:
    if QA.exists():
        raise ValueError("refuse to overwrite QA")
    report = json.loads((OUT / "review.json").read_text())
    images = []
    for frame in report["frames"]:
        file = ROOT / frame["path"]
        if sha(file) != frame["sha256"]:
            raise ValueError("candidate hash changed")
        images.append(Image.open(file).convert("RGBA"))
    heights = [visible_bounds(im)[3] - visible_bounds(im)[1] for im in images]
    scale = 200 / max(heights)
    candidate_panels, geometry = [], []
    for index, image in enumerate(images):
        # ONE uniform scale is applied to every candidate, solely for display.
        scaled = image.resize((round(image.width * scale), round(image.height * scale)),
                              Image.Resampling.NEAREST)
        left, top, right, bottom = visible_bounds(scaled)
        x = round(ANCHOR_X - sole_center(scaled))
        y = BASELINE - (bottom - 1)
        if min(left + x, top + y) < 24 or right + x >= CANVAS[0] or bottom + y >= CANVAS[1]:
            raise ValueError("preview would clip visible artwork")
        candidate_panels.append(panel(scaled, (x, y), f"T{index + 1:02d} / 10 transition"))
        geometry.append({"frame": index + 1, "sourceHeightAlpha128": heights[index],
                         "displayHeightAlpha128": bottom - top,
                         "displayTopY": top + y, "displaySoleY": BASELINE,
                         "displayTranslation": [x, y]})
    anchors = ROOT / "assets/rework/v0.1.0/manual-transition-endpoints"
    gu_path = anchors / "A-gu-to-feng-entry.png"
    feng_path = anchors / "B-gu-to-feng-exit.png"
    gu = Image.open(gu_path).convert("RGBA")
    feng = Image.open(feng_path).convert("RGBA")
    gu_panel = panel(gu, NORMAL_ORIGIN, "Gu IDLE / outside transition")
    feng_panel = panel(feng, NORMAL_ORIGIN, "Feng IDLE / outside transition")
    all_panels = [gu_panel, *candidate_panels, feng_panel]
    QA.mkdir()
    grid = Image.new("RGBA", (CANVAS[0] * 6, CANVAS[1] * 2), (35, 35, 39, 255))
    for i, item in enumerate(all_panels):
        grid.paste(item, ((i % 6) * CANVAS[0], (i // 6) * CANVAS[1]))
    grid.save(QA / "idle-transition-idle-contact-sheet.png")
    # GIF is a flattened QA rendering; alpha remains intact in all source PNGs.
    gif = [item.convert("RGB").quantize(colors=256, dither=Image.Dither.NONE)
           for item in all_panels]
    gif[0].save(QA / "idle-transition-idle-preview.gif", save_all=True,
                append_images=gif[1:], duration=[900, *([180] * 10), 900],
                loop=0, disposal=2, optimize=False)
    candidates = [item.convert("RGB").quantize(colors=256, dither=Image.Dither.NONE)
                  for item in candidate_panels]
    candidates[0].save(QA / "transition-only-10-frames.gif", save_all=True,
                      append_images=candidates[1:], duration=180, loop=0,
                      disposal=2, optimize=False)
    with Image.open(QA / "transition-only-10-frames.gif") as saved:
        if saved.n_frames != 10:
            raise AssertionError("transition-only GIF must have exactly 10 frames")
    output = {
        "status": "VISUAL_QA_FAIL", "approval": "NOT_APPROVED",
        "purpose": "QA display only, not runtime normalization",
        "transitionFrameCount": 10, "externalIdleHolds": 2,
        "candidateCommonNearestScale": scale, "sourceHeightRange": [min(heights), max(heights)],
        "sourcePixelsModified": False, "geometry": geometry,
        "refs": {str(gu_path.relative_to(ROOT)): sha(gu_path), str(feng_path.relative_to(ROOT)): sha(feng_path)},
        "blockers": [
            "First generated pose is shorter than canonical Gu under a single common scale; entry head position jumps.",
            "The generated face/hair and suit rendition does not yet exactly match canonical Idle artwork.",
            "Original generated PNGs retain partial-alpha edge pixels; strict hard-edge pixel alpha not met.",
        ],
        "appIntegrated": False,
    }
    (QA / "preview-review.json").write_text(json.dumps(output, indent=2) + "\n")
    for record in report["frames"]:
        if sha(ROOT / record["path"]) != record["sha256"]:
            raise AssertionError("source PNG modified during preview")
    print(json.dumps({k: output[k] for k in ("status", "transitionFrameCount", "externalIdleHolds", "sourceHeightRange")}))


if __name__ == "__main__":
    main()
