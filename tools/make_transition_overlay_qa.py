"""Render Phase 3F oversized-transition review sheets from frozen assets only."""

from __future__ import annotations

import json
from pathlib import Path

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[1]
LAYOUT = json.loads((ROOT / "runtime-patch/fixtures/transition-overlay-layout.json").read_text())
OUTPUT = ROOT / "hatch-runs/transition-qa/overlay"
PANEL = (300, 300)
ORIGIN = (50, 50)
SCALE = 2
NORMAL = (192, 208)
BLUE = (31, 94, 220, 255)
RED = (220, 65, 55, 255)
GREEN = (39, 155, 77, 255)
PURPLE = (137, 67, 170, 255)


def checkerboard() -> Image.Image:
    panel = Image.new("RGBA", PANEL, (248, 248, 248, 255))
    draw = ImageDraw.Draw(panel)
    for y in range(0, PANEL[1], 16):
        for x in range(0, PANEL[0], 16):
            if (x // 16 + y // 16) % 2:
                draw.rectangle((x, y, x + 15, y + 15), fill=(226, 226, 226, 255))
    return panel


def idle_cell(form: str) -> Image.Image:
    with Image.open(ROOT / f"assets/builds/{form}/spritesheet.webp") as atlas:
        if atlas.size != (1536, 2288):
            raise ValueError(f"{form}: formal atlas changed dimensions")
        return atlas.convert("RGBA").crop((0, 0, *NORMAL))


def panel_for(sprite: Image.Image, label: str, layout: dict | None = None) -> Image.Image:
    panel = checkerboard()
    if layout is None:
        position = ORIGIN
    else:
        if sprite.size != (layout["canvasWidth"], layout["canvasHeight"]):
            raise ValueError(f"{label}: frame canvas differs from frozen layout")
        position = (ORIGIN[0] + layout["offsetLeft"], ORIGIN[1] + layout["offsetTop"])
    panel.alpha_composite(sprite, position)
    draw = ImageDraw.Draw(panel)
    x, y = ORIGIN
    draw.rectangle((x, y, x + NORMAL[0] - 1, y + NORMAL[1] - 1), outline=BLUE, width=1)
    if layout is not None:
        left, top = position
        draw.rectangle((left, top, left + sprite.width - 1, top + sprite.height - 1), outline=RED, width=1)
    draw.line((x + 96, 12, x + 96, 274), fill=GREEN, width=1)
    draw.line((12, y + 203, 288, y + 203), fill=PURPLE, width=1)
    draw.ellipse((x + 94, y + 201, x + 98, y + 205), fill=(255, 255, 255, 255), outline=(0, 0, 0, 255))
    draw.text((10, 278), label, fill=(20, 20, 20, 255))
    return panel.resize((PANEL[0] * SCALE, PANEL[1] * SCALE), resample=Image.Resampling.NEAREST)


def make_sequence(direction: str, initial: str, target: str, frame_count: int, filename: str) -> Path:
    layout = LAYOUT[direction]
    panels = [panel_for(idle_cell(initial), f"{initial.upper()} idle")]
    for index in range(1, frame_count + 1):
        source = ROOT / f"assets/transform-overlay/{direction}/{direction}_{index:02d}.png"
        with Image.open(source) as original:
            if original.mode != "RGBA":
                raise ValueError(f"{source}: must be RGBA")
            panels.append(panel_for(original.copy(), f"{direction.upper()} {index:02d}", layout))
    panels.append(panel_for(idle_cell(target), f"{target.upper()} idle"))
    sheet = Image.new("RGBA", (len(panels) * PANEL[0] * SCALE, PANEL[1] * SCALE), (255, 255, 255, 255))
    for index, item in enumerate(panels):
        sheet.alpha_composite(item, (index * PANEL[0] * SCALE, 0))
    OUTPUT.mkdir(parents=True, exist_ok=True)
    destination = OUTPUT / filename
    sheet.save(destination)
    return destination


def main() -> None:
    results = (
        make_sequence("gu_to_feng", "gu", "feng", 10, "gu-to-feng-overlay-sequence.png"),
        make_sequence("feng_to_gu", "feng", "gu", 8, "feng-to-gu-overlay-sequence.png"),
    )
    for destination in results:
        print(f"OVERLAY_QA_CREATED {destination}")
    print("guides=normal_192x208_blue,oversized_canvas_red,anchor_x96_green,baseline_y203_purple scale=2 nearest=true")


if __name__ == "__main__":
    main()
