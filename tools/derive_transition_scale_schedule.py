"""Derive smoothstep transition scales from formal idle and approved endpoints.

The schedule is deterministic but not an asset approval. Use --preflight to
test whether nearest-neighbor scaled body and high-alpha effects fit a cell.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image

from analyze_transition_endpoints import dark_character_bbox, idle_cell
from normalize_transition_frames import BASELINE, CELL, DIRECTIONS, ROOT


FIXTURE = ROOT / "runtime-patch" / "fixtures" / "transition-scale-schedule.json"
QA_PREFLIGHT = ROOT / "hatch-runs" / "transition-qa" / "schedule" / "preflight.json"
SOURCE_SIDE = 1254


def source_path(direction: str, frame: int) -> Path:
    return ROOT / "assets" / "transform" / direction / f"{direction}_{frame:02d}.png"


def source_body_height(direction: str, frame: int) -> int:
    with Image.open(source_path(direction, frame)) as image:
        if image.size != (SOURCE_SIDE, SOURCE_SIDE) or image.mode != "RGBA":
            raise ValueError(f"{direction} {frame}: approved source format changed")
        box = dark_character_bbox(image)
    return box[3] - box[1]


def idle_body_height(form: str) -> int:
    box = idle_cell(form).getchannel("A").getbbox()
    if box is None:
        raise ValueError(f"{form}: empty formal idle")
    return box[3] - box[1]


def smoothstep(t: float) -> float:
    return 3 * t * t - 2 * t * t * t


def derive() -> dict[str, list[dict[str, float | int]]]:
    result: dict[str, list[dict[str, float | int]]] = {}
    for direction, count in DIRECTIONS.items():
        start_form, end_form = direction.split("_to_")
        start = idle_body_height(start_form) / source_body_height(direction, 1)
        end = idle_body_height(end_form) / source_body_height(direction, count)
        entries: list[dict[str, float | int]] = []
        for frame in range(1, count + 1):
            t = (frame - 1) / (count - 1)
            scale = start + (end - start) * smoothstep(t)
            side = round(SOURCE_SIDE * scale)
            entries.append({
                "frame": frame, "normalizedT": t, "scale": scale,
                "resizedWidth": side, "resizedHeight": side,
                "effectiveScale": side / SOURCE_SIDE,
                "targetCenterX": 96, "baselineY": BASELINE,
            })
        if len(entries) != count or any(e["resizedWidth"] != e["resizedHeight"] for e in entries):
            raise ValueError(f"{direction}: malformed schedule")
        values = [float(e["scale"]) for e in entries]
        if end < start and any(b > a for a, b in zip(values, values[1:])):
            raise ValueError(f"{direction}: non-monotonic decreasing schedule")
        if end > start and any(b < a for a, b in zip(values, values[1:])):
            raise ValueError(f"{direction}: non-monotonic increasing schedule")
        result[direction] = entries
    return result


def canonical_bytes(schedule: dict[str, list[dict[str, float | int]]]) -> bytes:
    return (json.dumps(schedule, indent=2, ensure_ascii=False) + "\n").encode()


def opaque_content_bbox(image: Image.Image) -> tuple[int, int, int, int]:
    bbox = image.getchannel("A").point(lambda value: 255 if value >= 128 else 0).getbbox()
    if bbox is None:
        raise ValueError("empty high-alpha content")
    return bbox


def preflight(schedule: dict[str, list[dict[str, float | int]]]) -> dict[str, object]:
    rows: dict[str, list[dict[str, object]]] = {}
    violations: list[dict[str, object]] = []
    for direction, entries in schedule.items():
        direction_rows: list[dict[str, object]] = []
        previous_scale: float | None = None
        previous_height: int | None = None
        for entry in entries:
            frame = int(entry["frame"])
            side = int(entry["resizedWidth"])
            with Image.open(source_path(direction, frame)) as source:
                scaled = source.resize((side, side), Image.Resampling.NEAREST)
            body = dark_character_bbox(scaled)
            important = opaque_content_bbox(scaled)
            body_center = (body[0] + body[2]) / 2
            dx = round(96 - body_center)
            dy = BASELINE - (body[3] - 1)
            moved_body = [body[0] + dx, body[1] + dy, body[2] + dx, body[3] + dy]
            moved_important = [important[0] + dx, important[1] + dy,
                               important[2] + dx, important[3] + dy]
            body_height = body[3] - body[1]
            scale = float(entry["effectiveScale"])
            scale_delta = None if previous_scale is None else abs(scale / previous_scale - 1)
            height_delta = None if previous_height is None else abs(body_height - previous_height)
            reasons: list[str] = []
            if (moved_body[0] < 0 or moved_body[1] < 0
                    or moved_body[2] > CELL[0] or moved_body[3] > CELL[1]):
                reasons.append("CHARACTER_CLIPPED")
            if (moved_important[0] < 0 or moved_important[1] < 0
                    or moved_important[2] > CELL[0] or moved_important[3] > CELL[1]):
                reasons.append("IMPORTANT_ALPHA_CLIPPED")
            if scale_delta is not None and scale_delta > 0.10:
                reasons.append("SCALE_JUMP_GT_10_PERCENT")
            row = {
                "frame": frame, "scheduledScale": entry["scale"],
                "effectiveScale": scale, "resizedSide": side,
                "integerTranslation": [dx, dy], "bodyBBox": moved_body,
                "importantAlphaBBox": moved_important,
                "bodyHeight": body_height, "bodyCenterX": (moved_body[0] + moved_body[2]) / 2,
                "bodyBaselineY": moved_body[3] - 1,
                "adjacentScaleDelta": scale_delta,
                "adjacentBodyHeightDelta": height_delta,
                "poseDrivenDelta": height_delta is not None and height_delta > 8,
                "violations": reasons,
            }
            direction_rows.append(row)
            if reasons:
                violations.append({"direction": direction, "frame": frame,
                                   "reasons": reasons, "bodyBBox": moved_body,
                                   "importantAlphaBBox": moved_important})
            previous_scale, previous_height = scale, body_height
        rows[direction] = direction_rows
    return {
        "result": "BLOCKED" if violations else "PASS",
        "method": "nearest-neighbor full-source resize, dark-character integer anchor, alpha>=128 important-content fit",
        "rows": rows, "violations": violations,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="compare fixture without writing")
    parser.add_argument("--preflight", action="store_true", help="check all scheduled frames for clipping")
    args = parser.parse_args()
    schedule = derive()
    expected = canonical_bytes(schedule)
    if args.check:
        if not FIXTURE.exists() or FIXTURE.read_bytes() != expected:
            raise ValueError(f"{FIXTURE}: missing or nondeterministic schedule")
    else:
        FIXTURE.parent.mkdir(parents=True, exist_ok=True)
        FIXTURE.write_bytes(expected)
    print(f"SCHEDULE_PASS gu_to_feng={len(schedule['gu_to_feng'])} "
          f"feng_to_gu={len(schedule['feng_to_gu'])} "
          f"algorithm=smoothstep fixture={FIXTURE}")
    if args.preflight:
        report = preflight(schedule)
        QA_PREFLIGHT.parent.mkdir(parents=True, exist_ok=True)
        QA_PREFLIGHT.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
        print(f"PREFLIGHT_{report['result']} violations={len(report['violations'])} "
              f"report={QA_PREFLIGHT}")
        for item in report["violations"]:
            print(f"  {item['direction']} {item['frame']:02d}: "
                  f"{','.join(item['reasons'])} important={item['importantAlphaBBox']}")


if __name__ == "__main__":
    main()
