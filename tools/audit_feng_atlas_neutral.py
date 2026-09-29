"""Read-only inventory of every formal Feng v2 atlas slot for F0 reuse."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from PIL import Image, ImageDraw

from tools.f0_transition_endpoint_spec import OUT, specification
from tools.prepare_transition_animation_candidate import digest
from tools.audit_b_endpoint_compatibility import FENG_ATLAS, FENG_ATLAS_SHA, KB2

ROW_NAMES = (
    "idle", "running-right", "running-left", "waving", "jumping",
    "failed", "waiting", "running", "review", "look-row-9", "look-row-10",
)
QA = OUT / "atlas-neutral-audit"
CELL = (192, 208)


def rgba_hash(image: Image.Image) -> str:
    return hashlib.sha256(image.tobytes()).hexdigest()


def geometry(image: Image.Image) -> dict:
    alpha = image.getchannel("A")
    bbox = alpha.getbbox()
    if bbox is None:
        return {"alphaBbox": None, "baselineY": None, "bodyBbox": None,
                "bodyBandCenterX": None, "upperRegionBboxApprox": None,
                "registrationX": 96, "rgbaSha256": rgba_hash(image)}
    body = alpha.crop((0, 70, 192, 208)).getbbox()
    upper = alpha.crop((0, 0, 192, 70)).getbbox()
    return {"alphaBbox": list(bbox), "baselineY": bbox[3] - 1,
            "bodyBbox": [body[0], body[1] + 70, body[2], body[3] + 70] if body else None,
            "bodyBandCenterX": (body[0] + body[2]) / 2 if body else None,
            "upperRegionBboxApprox": list(upper) if upper else None,
            "registrationX": 96, "rgbaSha256": rgba_hash(image)}


def scan() -> tuple[dict, list[Image.Image]]:
    specification()  # Recheck frozen A/K1/K2/K3/B, KB2 and formal atlas hashes.
    if digest(FENG_ATLAS) != FENG_ATLAS_SHA:
        raise ValueError("formal Feng atlas changed")
    with Image.open(FENG_ATLAS) as source:
        if source.mode != "RGBA" or source.size != (1536, 2288):
            raise ValueError("formal v2 atlas must be 1536x2288 RGBA")
        atlas = source.copy()
    with Image.open(KB2) as source:
        kb2 = source.copy()
    b = atlas.crop((0, 0, *CELL))
    records, frames = [], []
    for row, state in enumerate(ROW_NAMES):
        for col in range(8):
            frame = atlas.crop((col * 192, row * 208, (col + 1) * 192, (row + 1) * 208))
            info = geometry(frame)
            records.append({"state": state, "row": row, "frame": col,
                            "nonempty": info["alphaBbox"] is not None, **info})
            frames.append(frame)
    used = [r for r in records if r["nonempty"]]
    duplicates = {}
    for record in used:
        duplicates.setdefault(record["rgbaSha256"], []).append(f'{record["state"]}:{record["frame"]}')
    return {"status": "ATLAS_SCAN_COMPLETE_VISUAL_RANKING_PENDING", "atlasSha256": digest(FENG_ATLAS),
            "atlasSize": [1536, 2288], "cellSize": list(CELL), "slotsScanned": len(records),
            "nonemptyFrames": len(used), "emptySlots": len(records) - len(used),
            "rowNames": list(ROW_NAMES), "KB2RgbaSha256": rgba_hash(kb2),
            "formalIdle0RgbaSha256": rgba_hash(b),
            "headGuideWarning": "upperRegionBboxApprox is alpha in y0:70; arms/shoulders can contaminate it. It is NOT a segmented anatomical head; shortlisted candidates require manual head guides and independent visual review.",
            "registrationWarning": "registrationX=96 is the atlas cell anchor, not a proof that each asymmetric silhouette's center is exactly 96.",
            "duplicatePixelFamilies": [names for names in duplicates.values() if len(names) > 1],
            "records": records, "sourcePixelsModified": False, "F0Selected": False}, frames


def prepare(output: Path = QA) -> dict:
    if output.exists():
        raise ValueError("refuse to overwrite existing Feng atlas inventory")
    report, frames = scan()
    output.mkdir(parents=True)
    sheet = Image.new("RGBA", (1536, 11 * 230), (32, 32, 32, 255))
    draw = ImageDraw.Draw(sheet)
    for index, frame in enumerate(frames):
        row, col = divmod(index, 8)
        x, y = col * 192, row * 230
        sheet.alpha_composite(frame, (x, y + 20))
        draw.text((x + 3, y + 2), f"{row:02d}/{col:02d} {ROW_NAMES[row]}", fill=(255, 255, 255, 255))
    sheet.save(output / "all-88-slots-contact.png")
    (output / "inventory.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=QA)
    args = parser.parse_args()
    result = prepare(args.output)
    print(f'{result["status"]} slots={result["slotsScanned"]} nonempty={result["nonemptyFrames"]}')
