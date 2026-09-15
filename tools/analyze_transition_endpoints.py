"""Read-only endpoint geometry and deterministic comparison sheets for Phase 3B.

The color mask is an extremal-body proxy: opaque dark hair, suit, and shoes.
Cyan energy pixels are excluded. It does not edit any approved or runtime art.
"""

from __future__ import annotations

import json
from pathlib import Path

from PIL import Image, ImageDraw

from normalize_transition_frames import BASELINE, CELL, ROOT, plan_sequence


QA_DIR = ROOT / "hatch-runs" / "transition-qa" / "endpoints"
BODY_HEIGHT_TARGET = 200
HEIGHT_TOLERANCE = 2


def dark_character_bbox(image: Image.Image) -> tuple[int, int, int, int]:
    """BBox of opaque near-neutral dark character extrema, excluding cyan aura.

    On these four approved endpoint frames, the extremal selected rows are
    visibly black hair and dark shoes, and selected lateral pixels are suit.
    This remains a deterministic proxy, not a cutout or recoloring operation.
    """
    rgba = image.convert("RGBA")
    width, _ = rgba.size
    left = top = 10**9
    right = bottom = -1
    for index, (red, green, blue, alpha) in enumerate(rgba.get_flattened_data()):
        if (alpha >= 128 and red < 100 and green < 100 and blue < 110
                and abs(red - green) < 35 and abs(green - blue) < 55):
            x, y = index % width, index // width
            left, top = min(left, x), min(top, y)
            right, bottom = max(right, x), max(bottom, y)
    if right < 0:
        raise ValueError("dark character proxy is empty")
    return left, top, right + 1, bottom + 1


def geometry(bbox: tuple[int, int, int, int]) -> dict[str, float | int | list[int]]:
    left, top, right, bottom = bbox
    return {
        "bbox": list(bbox), "width": right - left, "height": bottom - top,
        "center_x": (left + right) / 2, "baseline": bottom - 1,
        "top_y": top, "visible_character_width": right - left,
        "visible_character_height": bottom - top,
    }


def alpha_bbox(image: Image.Image) -> tuple[int, int, int, int]:
    bbox = image.convert("RGBA").getchannel("A").getbbox()
    if bbox is None:
        raise ValueError("empty alpha")
    return bbox


def idle_cell(form: str) -> Image.Image:
    with Image.open(ROOT / "assets" / "builds" / form / "spritesheet.webp") as atlas:
        if atlas.size != (1536, 2288):
            raise ValueError(f"{form}: not a formal v2 atlas")
        return atlas.convert("RGBA").crop((0, 0, *CELL))


def runtime_cell(direction: str, number: int) -> Image.Image:
    path = ROOT / "assets" / "transform-runtime" / direction / f"{direction}_{number:02d}.png"
    with Image.open(path) as image:
        if image.size != CELL or image.mode != "RGBA":
            raise ValueError(f"{path}: not 192x208 RGBA")
        return image.copy()


def source_endpoint(direction: str, number: int) -> dict[str, object]:
    path = ROOT / "assets" / "transform" / direction / f"{direction}_{number:02d}.png"
    with Image.open(path) as image:
        if image.size != (1254, 1254) or image.mode != "RGBA":
            raise ValueError(f"{path}: approved source format changed")
        return {
            "alpha": geometry(alpha_bbox(image)),
            "character_dark_proxy": geometry(dark_character_bbox(image)),
        }


def draw_tile(image: Image.Image, label: str, *, include_proxies: bool) -> Image.Image:
    base = Image.new("RGBA", CELL, (30, 32, 39, 255))
    base.alpha_composite(image)
    draw = ImageDraw.Draw(base)
    draw.line((96, 0, 96, CELL[1] - 1), fill=(0, 215, 245, 255), width=1)
    draw.line((0, BASELINE, CELL[0] - 1, BASELINE), fill=(80, 240, 100, 255), width=1)
    ab = alpha_bbox(image)
    draw.rectangle((ab[0], ab[1], ab[2] - 1, ab[3] - 1), outline=(235, 70, 75, 255), width=1)
    if include_proxies:
        db = dark_character_bbox(image)
        draw.rectangle((db[0], db[1], db[2] - 1, db[3] - 1), outline=(255, 185, 30, 255), width=1)
    enlarged = base.resize((CELL[0] * 2, CELL[1] * 2), Image.Resampling.NEAREST)
    tile = Image.new("RGBA", (CELL[0] * 2, CELL[1] * 2 + 28), (20, 21, 27, 255))
    tile.paste(enlarged, (0, 28))
    ImageDraw.Draw(tile).text((8, 7), label, fill=(255, 255, 255, 255))
    return tile


def comparison_sheet(direction: str, source_form: str, target_form: str, count: int) -> Path:
    frames = [
        (idle_cell(source_form), f"{source_form.upper()} IDLE", False),
        (runtime_cell(direction, 1), f"{direction} 01", True),
        (runtime_cell(direction, count), f"{direction} {count:02d}", True),
        (idle_cell(target_form), f"{target_form.upper()} IDLE", False),
    ]
    tiles = [draw_tile(image, label, include_proxies=proxy) for image, label, proxy in frames]
    sheet = Image.new("RGBA", (tiles[0].width * len(tiles), tiles[0].height), (20, 21, 27, 255))
    for index, tile in enumerate(tiles):
        sheet.paste(tile, (index * tile.width, 0))
    output = QA_DIR / ("gu-to-feng-endpoints.png" if direction == "gu_to_feng" else "feng-to-gu-endpoints.png")
    sheet.save(output)
    return output


def contact_sheet() -> Path:
    sequences = (
        ("gu_to_feng", "gu", "feng", 10),
        ("feng_to_gu", "feng", "gu", 8),
    )
    tile_w, tile_h = CELL[0], CELL[1] + 18
    sheet = Image.new("RGBA", (12 * tile_w, 2 * tile_h), (20, 21, 27, 255))
    for row, (direction, start, finish, count) in enumerate(sequences):
        entries = [(idle_cell(start), f"{start} idle")]
        entries.extend((runtime_cell(direction, i), f"{i:02d}") for i in range(1, count + 1))
        entries.append((idle_cell(finish), f"{finish} idle"))
        for col, (image, label) in enumerate(entries):
            x, y = col * tile_w, row * tile_h
            block = Image.new("RGBA", CELL, (30, 32, 39, 255))
            block.alpha_composite(image)
            sheet.paste(block, (x, y + 18))
            ImageDraw.Draw(sheet).text((x + 4, y + 2), label, fill=(255, 255, 255, 255))
    output = QA_DIR / "contact-sheet.png"
    sheet.save(output)
    return output


def analyze() -> dict[str, object]:
    gu_idle = idle_cell("gu")
    feng_idle = idle_cell("feng")
    endpoint_cells = {
        "gu_to_feng_first": runtime_cell("gu_to_feng", 1),
        "gu_to_feng_last": runtime_cell("gu_to_feng", 10),
        "feng_to_gu_first": runtime_cell("feng_to_gu", 1),
        "feng_to_gu_last": runtime_cell("feng_to_gu", 8),
    }
    runtime_geometry = {
        "gu_idle": {"alpha": geometry(alpha_bbox(gu_idle)), "body": geometry(alpha_bbox(gu_idle))},
        "feng_idle": {"alpha": geometry(alpha_bbox(feng_idle)), "body": geometry(alpha_bbox(feng_idle))},
    }
    for key, image in endpoint_cells.items():
        runtime_geometry[key] = {
            "alpha": geometry(alpha_bbox(image)),
            "body_dark_proxy": geometry(dark_character_bbox(image)),
        }
    sources = {
        "gu_to_feng_first": source_endpoint("gu_to_feng", 1),
        "gu_to_feng_last": source_endpoint("gu_to_feng", 10),
        "feng_to_gu_first": source_endpoint("feng_to_gu", 1),
        "feng_to_gu_last": source_endpoint("feng_to_gu", 8),
    }
    scales: dict[str, dict[str, object]] = {}
    for direction, names in (
        ("gu_to_feng", ("gu_to_feng_first", "gu_to_feng_last")),
        ("feng_to_gu", ("feng_to_gu_first", "feng_to_gu_last")),
    ):
        heights = [sources[name]["character_dark_proxy"]["height"] for name in names]
        intervals = [
            [(BODY_HEIGHT_TARGET - HEIGHT_TOLERANCE) / height,
             (BODY_HEIGHT_TARGET + HEIGHT_TOLERANCE) / height]
            for height in heights
        ]
        plan = plan_sequence(direction)
        union_width = plan.union_bbox[2] - plan.union_bbox[0]
        scales[direction] = {
            "endpoint_body_heights_source": heights,
            "endpoint_height_scale_intervals": intervals,
            "candidate_scales": [BODY_HEIGHT_TARGET / height for height in heights],
            "one_scale_height_feasible": max(a[0] for a in intervals) <= min(a[1] for a in intervals),
            "full_alpha_union_bbox": list(plan.union_bbox),
            "max_scale_without_clipping_any_nonzero_alpha": CELL[0] / union_width,
        }
    QA_DIR.mkdir(parents=True, exist_ok=True)
    qa = {
        "gu_to_feng": str(comparison_sheet("gu_to_feng", "gu", "feng", 10)),
        "feng_to_gu": str(comparison_sheet("feng_to_gu", "feng", "gu", 8)),
        "contact_sheet": str(contact_sheet()),
    }
    result = {
        "phase": "3B", "structural_endpoint_check": "BLOCKED",
        "reason": "endpoint body-height scale intervals are disjoint in both directions",
        "runtime_geometry": runtime_geometry, "source_endpoints": sources,
        "scale_analysis": scales, "qa": qa,
        "manual_body_bbox_required": False,
        "body_bbox_confidence": "LIKELY: opaque dark extremal proxy; cyan effects excluded; comparison sheets require user visual review",
        "visual_review_required": True,
    }
    (QA_DIR / "analysis.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return result


def main() -> None:
    result = analyze()
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
