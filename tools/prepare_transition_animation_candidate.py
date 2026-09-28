"""Extract generated transition artwork; never synthesize intermediate poses.

All cells share ONE nearest-neighbor grid normalization. Only integer registration
and alpha hardening follow. Exact approved endpoints replace the two boundary
cells. Outputs remain candidates until an independent visual gate passes.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil

from PIL import Image, ImageDraw

from tools.prepare_manual_transition_endpoints import component_sizes, pixel_overlay

ROOT = Path(__file__).resolve().parents[1]
ENDPOINT_ROOT = ROOT / "assets/rework/v0.1.0/manual-transition-endpoints"
SPECS = {
    "gu_to_feng": (10, 5, "A-gu-to-feng-entry.png", "B-gu-to-feng-exit.png"),
    "feng_to_gu": (8, 4, "C-feng-to-gu-entry.png", "D-feng-to-gu-exit.png"),
}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def metrics(image: Image.Image) -> dict:
    alpha = image.getchannel("A")
    bbox = alpha.getbbox()
    body = alpha.crop((0, 70, 192, 208)).getbbox()
    head = alpha.crop((0, 0, 192, 70)).getbbox()
    values = list(image.get_flattened_data())
    components = component_sizes(image)
    return {
        "alphaBbox": list(bbox) if bbox else None,
        "baselineY": bbox[3] - 1 if bbox else None,
        "headReferenceBbox": list(head) if head else None,
        "bodyReferenceBbox": [body[0], body[1] + 70, body[2], body[3] + 70] if body else None,
        "bodyBandCenterX": (body[0] + body[2]) / 2 if body else None,
        "alphaValues": sorted({p[3] for p in values}),
        "hiddenRgbPixels": sum(any(p[:3]) for p in values if not p[3]),
        "connectedComponentSizes8": components,
        "isolatedSinglePixels": components.count(1),
        "touchesCellEdge": bool(bbox and (bbox[0] == 0 or bbox[1] == 0 or bbox[2] == 192 or bbox[3] == 208)),
    }


def harden_alpha(image: Image.Image) -> tuple[Image.Image, int]:
    values = list(image.get_flattened_data())
    count = sum(0 < p[3] < 255 for p in values)
    hardened = Image.new("RGBA", image.size)
    hardened.putdata([(*p[:3], 255) if p[3] >= 128 else (0, 0, 0, 0) for p in values])
    return hardened, count


def register(image: Image.Image) -> tuple[Image.Image, list[int]]:
    info = metrics(image)
    if info["baselineY"] is None or info["bodyBandCenterX"] is None:
        raise ValueError("empty generated character cell")
    dx = round(96 - info["bodyBandCenterX"])
    dy = 203 - info["baselineY"]
    # No fitting/scaling individual poses and no silently cropped translations.
    left, top, right, bottom = info["alphaBbox"]
    if min(left + dx, top + dy) < 1 or right + dx > 191 or bottom + dy > 207:
        raise ValueError("integer registration would crop generated artwork")
    result = Image.new("RGBA", (192, 208))
    result.paste(image, (dx, dy))
    return result, [dx, dy]


def diagnose_grid(source: Path, direction: str, output: Path) -> dict:
    """Retain rejected-layout evidence WITHOUT emitting playable frames."""
    if output.exists():
        raise ValueError("refuse to overwrite an existing grid diagnosis")
    count, columns, _, _ = SPECS[direction]
    with Image.open(source) as original:
        if original.mode != "RGBA":
            raise ValueError("source must be RGBA")
        size = original.size
        grid = original.resize((columns * 192, 416), Image.Resampling.NEAREST)
    sheet = Image.new("RGBA", (columns * 192, 480), (32, 32, 32, 255))
    draw, records = ImageDraw.Draw(sheet), []
    for index in range(count):
        x, y = (index % columns) * 192, (index // columns) * 208
        cell, partial = harden_alpha(grid.crop((x, y, x + 192, y + 208)))
        info = metrics(cell)
        try:
            _, shift = register(cell)
            error = None
        except ValueError as exc:
            shift, error = None, str(exc)
        records.append({"index": index, "partialAlphaPixels": partial,
                        "proposedIntegerShift": shift, "registrationError": error, **info})
        yy = (index // columns) * 240
        sheet.alpha_composite(cell, (x, yy + 24))
        draw.text((x + 3, yy + 2), f"RAW GRID {index:02d} / REJECTED", fill="white")
        draw.rectangle((x, yy + 24, x + 191, yy + 231), outline=(255, 100, 100, 255))
    output.mkdir(parents=True)
    sheet.save(output / "rejected-grid-contact-sheet.png")
    report = {"status": "REJECTED_GRID_DIAGNOSTIC_ONLY", "runtimeEligible": False,
              "playableFramesEmitted": 0, "direction": direction, "sourceSize": list(size),
              "sourceSha256": digest(source), "cells": records,
              "warning": "QA-only grid division may cut artwork; no production frames or corrective per-pose scaling emitted"}
    (output / "grid-diagnosis.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


def prepare(source: Path, direction: str, output: Path) -> dict:
    if output.exists():
        raise ValueError("refuse to overwrite an existing animation candidate")
    count, columns, entry, exit = SPECS[direction]
    approval = json.loads((ENDPOINT_ROOT / "approval.json").read_text())
    if approval["status"] != "ENDPOINT_ART_APPROVED":
        raise ValueError("endpoints not user approved")
    for name in (entry, exit):
        if digest(ENDPOINT_ROOT / name) != approval["approvedFiles"][name]:
            raise ValueError("approved endpoint hash changed")
    with Image.open(source) as original:
        if original.mode != "RGBA":
            raise ValueError("generated sheet must have genuine RGBA transparency")
        source_size = original.size
        if 0 not in original.getchannel("A").getextrema():
            raise ValueError("generated sheet has no transparent background")
        grid = original.resize((columns * 192, 416), Image.Resampling.NEAREST)
    cells, records = [], []
    for index in range(count):
        col, row = index % columns, index // columns
        raw = grid.crop((col * 192, row * 208, (col + 1) * 192, (row + 1) * 208))
        if index in (0, count - 1):
            name = entry if index == 0 else exit
            with Image.open(ENDPOINT_ROOT / name) as image:
                cell = image.copy()
            alpha_changes, shift, origin = 0, [0, 0], f"approved/{name}"
        else:
            cell, alpha_changes = harden_alpha(raw)
            cell, shift = register(cell)
            origin = "generated grid cell; no character synthesis in extraction"
        cells.append(cell)
        records.append({"index": index, "origin": origin, "integerShift": shift,
                        "hardenedPartialAlphaPixels": alpha_changes, "registrationAnchorX": 96,
                        **metrics(cell)})
    frames, qa = output / "frames", output / "qa"
    frames.mkdir(parents=True)
    qa.mkdir()
    for index, cell in enumerate(cells):
        file = frames / f"{direction}_{index:02d}.png"
        if index in (0, count - 1):
            shutil.copyfile(ENDPOINT_ROOT / (entry if index == 0 else exit), file)
        else:
            cell.save(file)
        records[index]["file"] = str(file.relative_to(output))
        records[index]["pngSha256"] = digest(file)
    sheet = Image.new("RGBA", (columns * 192, 480), (32, 32, 32, 255))
    draw = ImageDraw.Draw(sheet)
    for index, cell in enumerate(cells):
        x, y = (index % columns) * 192, (index // columns) * 240
        draw.text((x + 4, y + 3), f"{index:02d} candidate / NOT APPROVED", fill="white")
        sheet.alpha_composite(cell, (x, y + 24))
    sheet.save(qa / "contact-sheet.png")
    pairs = []
    for index, (left, right) in enumerate(zip(cells, cells[1:])):
        panel = Image.new("RGBA", (576, 244), (32, 32, 32, 255))
        pd = ImageDraw.Draw(panel)
        for col, (label, image) in enumerate(((f"{index:02d}", left), (f"{index + 1:02d}", right),
                                              ("pixel diff overlay", pixel_overlay(left, right)))):
            x = col * 192
            pd.text((x + 3, 3), label, fill="white")
            panel.alpha_composite(image, (x, 28))
            pd.line((x, 231, x + 191, 231), fill=(255, 170, 40, 255))
            pd.line((x + 96, 28, x + 96, 235), fill=(255, 90, 90, 255))
        a, b = records[index], records[index + 1]
        pairs.append({"from": index, "to": index + 1,
                      "baselineDelta": b["baselineY"] - a["baselineY"],
                      "headBandBboxDelta": [v - u for u, v in zip(a["headReferenceBbox"], b["headReferenceBbox"])],
                      "bodyBandBboxDelta": [v - u for u, v in zip(a["bodyReferenceBbox"], b["bodyReferenceBbox"])],
                      "rgbaChangedPixels": sum(a != b for a, b in zip(left.get_flattened_data(), right.get_flattened_data()))})
        panel.save(qa / f"adjacent-{index:02d}-{index + 1:02d}.png")
    report = {
        "direction": direction, "frameCount": count, "frameSize": [192, 208],
        "sourceSize": list(source_size), "sourceSha256": digest(source),
        "processing": "one shared nearest-neighbor grid normalization, binary alpha threshold128, zero transparent RGB, integer-only registration; exact approved endpoints",
        "bboxConvention": "head0:70 and body70:208 are reference bands NOT anatomical masks",
        "status": "CANDIDATE_REQUIRES_INDEPENDENT_VISUAL_QA", "runtimeEligible": False,
        "idleApproved": False, "runningApproved": False, "frames": records, "adjacentPairs": pairs,
    }
    report["structuralPass"] = all(r["baselineY"] == 203 and r["alphaValues"] == [0, 255]
                                   and not r["hiddenRgbPixels"] and not r["touchesCellEdge"]
                                   and not r["isolatedSinglePixels"]
                                   and 95.5 <= r["bodyBandCenterX"] <= 96.5 for r in records)
    (qa / "validation.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--direction", choices=SPECS, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--diagnostic-only", action="store_true")
    args = parser.parse_args()
    if args.diagnostic_only:
        result = diagnose_grid(args.source, args.direction, args.output)
        print(json.dumps({key: result[key] for key in ("direction", "playableFramesEmitted", "status")}))
    else:
        result = prepare(args.source, args.direction, args.output)
        print(json.dumps({key: result[key] for key in ("direction", "frameCount", "structuralPass", "status")}))
