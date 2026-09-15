"""Derive fixed, anchored overlay canvases from the frozen Phase 3C schedule.

Every nonzero-alpha pixel of the nearest-neighbor resized approved source is
included. The dark-character bbox is only an anchor proxy; it is not the
renderer Pet anchor, which remains (96, 203).
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image

from analyze_transition_endpoints import dark_character_bbox
from derive_transition_scale_schedule import FIXTURE, source_path
from normalize_transition_frames import BASELINE, CELL, DIRECTIONS, ROOT


LAYOUT = ROOT / "runtime-patch" / "fixtures" / "transition-overlay-layout.json"
QA = ROOT / "hatch-runs" / "transition-qa" / "overlay" / "preflight.json"
MAX_CANVAS = 384


def round16(value: int) -> int:
    return (value + 15) // 16 * 16


def shift_bbox(box: tuple[int, int, int, int], dx: int, dy: int) -> list[int]:
    return [box[0] + dx, box[1] + dy, box[2] + dx, box[3] + dy]


def read_schedule() -> dict[str, list[dict[str, object]]]:
    schedule = json.loads(FIXTURE.read_text())
    if set(schedule) != set(DIRECTIONS):
        raise ValueError("Phase 3C schedule direction set changed")
    for direction, count in DIRECTIONS.items():
        entries = schedule[direction]
        if len(entries) != count or [e["frame"] for e in entries] != list(range(1, count + 1)):
            raise ValueError(f"{direction}: malformed frozen frame schedule")
    return schedule


def scaled_geometry(direction: str, entry: dict[str, object]) -> dict[str, object]:
    frame = int(entry["frame"])
    side = int(entry["resizedWidth"])
    if side != int(entry["resizedHeight"]) or side <= 0:
        raise ValueError(f"{direction} {frame}: non-isotropic resize")
    with Image.open(source_path(direction, frame)) as image:
        if image.mode != "RGBA" or image.size != (1254, 1254):
            raise ValueError(f"{direction} {frame}: approved source format changed")
        scaled = image.resize((side, side), Image.Resampling.NEAREST)
    body = dark_character_bbox(scaled)
    full = scaled.getchannel("A").getbbox()
    important = scaled.getchannel("A").point(lambda a: 255 if a >= 128 else 0).getbbox()
    if full is None or important is None:
        raise ValueError(f"{direction} {frame}: empty effect/alpha")
    center = (body[0] + body[2]) / 2
    dx = round(CELL[0] / 2 - center)
    dy = BASELINE - (body[3] - 1)
    moved_body = shift_bbox(body, dx, dy)
    moved_full = shift_bbox(full, dx, dy)
    moved_important = shift_bbox(important, dx, dy)
    return {
        "frame": frame, "resizedSide": side, "translationInPetCoordinates": [dx, dy],
        "bodyBBoxPet": moved_body, "fullAlphaBBoxPet": moved_full,
        "importantAlphaBBoxPet": moved_important,
        "bodyCenterXPet": (moved_body[0] + moved_body[2]) / 2,
        "bodyBaselineYPet": moved_body[3] - 1,
        "effectExtentFromPetBox": {
            "left": max(0, -moved_full[0]), "right": max(0, moved_full[2] - CELL[0]),
            "top": max(0, -moved_full[1]), "bottom": max(0, moved_full[3] - CELL[1]),
        },
    }


def derive() -> tuple[dict[str, dict[str, object]], dict[str, object]]:
    schedule = read_schedule()
    layout: dict[str, dict[str, object]] = {}
    rows: dict[str, list[dict[str, object]]] = {}
    violations: list[str] = []
    for direction, entries in schedule.items():
        frames = [scaled_geometry(direction, entry) for entry in entries]
        rows[direction] = frames
        # Include the normal Pet box so the metadata preserves its reference
        # coordinate system even if every frame's content is narrower.
        left = min(0, *(f["fullAlphaBBoxPet"][0] for f in frames))
        top = min(0, *(f["fullAlphaBBoxPet"][1] for f in frames))
        right = max(CELL[0], *(f["fullAlphaBBoxPet"][2] for f in frames))
        bottom = max(CELL[1], *(f["fullAlphaBBoxPet"][3] for f in frames))
        width, height = round16(right - left), round16(bottom - top)
        if width > MAX_CANVAS or height > MAX_CANVAS:
            violations.append(f"{direction}: OVERLAY_GEOMETRY_BLOCKED {width}x{height}")
        anchor_x, anchor_y = CELL[0] // 2 - left, BASELINE - top
        item = {
            "canvasWidth": width, "canvasHeight": height,
            "anchorX": anchor_x, "anchorY": anchor_y,
            "petAnchorX": CELL[0] // 2, "petBaselineY": BASELINE,
            "offsetLeft": CELL[0] // 2 - anchor_x,
            "offsetTop": BASELINE - anchor_y,
        }
        layout[direction] = item
        for f in frames:
            box = f["fullAlphaBBoxPet"]
            overlay_box = shift_bbox(tuple(box), -left, -top)
            f["fullAlphaBBoxOverlay"] = overlay_box
            f["bodyBBoxOverlay"] = shift_bbox(tuple(f["bodyBBoxPet"]), -left, -top)
            if any((overlay_box[0] < 0, overlay_box[1] < 0,
                    overlay_box[2] > width, overlay_box[3] > height)):
                violations.append(f"{direction} {f['frame']:02d}: full alpha clipped")
            if abs(f["bodyCenterXPet"] - CELL[0] / 2) > 1:
                violations.append(f"{direction} {f['frame']:02d}: body center drift")
            if f["bodyBaselineYPet"] != BASELINE:
                violations.append(f"{direction} {f['frame']:02d}: body baseline drift")
    report = {
        "result": "OVERLAY_GEOMETRY_BLOCKED" if violations else "PASS",
        "method": "frozen Phase 3C nearest-neighbor scale; dark-body integer anchor; full alpha union; 16px canvas rounding",
        "normalPetBox": list(CELL), "petAnchor": [CELL[0] // 2, BASELINE],
        "layout": layout, "rows": rows, "effectCropCount": 0 if not violations else len(violations),
        "maxEffectExtentFromPetBox": {
            edge: max(f["effectExtentFromPetBox"][edge] for fs in rows.values() for f in fs)
            for edge in ("left", "right", "top", "bottom")
        },
        "violations": violations,
    }
    return layout, report


def canonical(data: object) -> bytes:
    return (json.dumps(data, indent=2, sort_keys=True) + "\n").encode()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="compare fixture/QA without writing")
    args = parser.parse_args()
    layout, report = derive()
    if report["result"] != "PASS":
        raise ValueError("; ".join(report["violations"]))
    for path, payload in ((LAYOUT, layout), (QA, report)):
        expected = canonical(payload)
        if args.check:
            if not path.exists() or path.read_bytes() != expected:
                raise ValueError(f"{path}: missing or not deterministic")
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(expected)
    print(f"OVERLAY_GEOMETRY_PASS gu_to_feng={layout['gu_to_feng']['canvasWidth']}x{layout['gu_to_feng']['canvasHeight']} feng_to_gu={layout['feng_to_gu']['canvasWidth']}x{layout['feng_to_gu']['canvasHeight']} effects_cropped=0 frames=18")


if __name__ == "__main__":
    main()
