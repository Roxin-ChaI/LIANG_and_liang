"""Prepare four exact canonical boundary PNGs for USER approval, not an animation.

No new character drawing, resampling, effects or intermediate frames are made.
"""
from __future__ import annotations

import argparse
from collections import deque
import hashlib
import json
from pathlib import Path

from PIL import Image, ImageDraw

from tools.specify_transition_endpoints import reference

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "assets/rework/v0.1.0/manual-transition-endpoints"
ENDPOINTS = (("A", "gu-to-feng-entry", "gu"), ("B", "gu-to-feng-exit", "feng"),
             ("C", "feng-to-gu-entry", "feng"), ("D", "feng-to-gu-exit", "gu"))


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical(form: str) -> tuple[Path, Image.Image]:
    source = ROOT / "assets/builds" / form / "spritesheet.webp"
    with Image.open(source) as atlas:
        if atlas.mode != "RGBA" or atlas.size != (1536, 2288):
            raise ValueError("canonical atlas geometry changed")
        return source, atlas.crop((0, 0, 192, 208))


def component_sizes(image: Image.Image) -> list[int]:
    points = {(x, y) for y in range(208) for x in range(192) if image.getpixel((x, y))[3]}
    sizes = []
    while points:
        queue = deque([points.pop()])
        size = 0
        while queue:
            x, y = queue.popleft()
            size += 1
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    point = (x + dx, y + dy)
                    if point in points:
                        points.remove(point)
                        queue.append(point)
        sizes.append(size)
    return sorted(sizes, reverse=True)


def compare(candidate: Image.Image, original: Image.Image) -> dict:
    if candidate.mode != "RGBA" or candidate.size != (192, 208):
        raise ValueError("endpoint must be 192x208 RGBA")
    values = list(candidate.get_flattened_data())
    different = sum(a != b for a, b in zip(values, original.get_flattened_data()))
    metrics, expected = reference(candidate), reference(original)
    body = metrics["bodyReferenceBbox"]
    result = {"rgbaDifferentPixels": different, "baselineY": metrics["alphaBbox"][3] - 1,
              "registrationAnchorX": 96, "measuredBodyBandCenterX": (body[0] + body[2]) / 2,
              "metrics": metrics, "canonicalMetrics": expected,
              "headPositionDelta": [metrics["headReferenceBbox"][i] - expected["headReferenceBbox"][i]
                                    for i in range(4)],
              "bodyBboxDelta": [body[i] - expected["bodyReferenceBbox"][i] for i in range(4)],
              "alphaValues": sorted({p[3] for p in values}),
              "hiddenRgbPixels": sum(any(p[:3]) for p in values if p[3] == 0),
              "connectedComponentSizes8": component_sizes(candidate),
              "canonicalComponentSizes8": component_sizes(original),
              "touchesCellEdge": any(p[3] for x in range(192) for p in
                                     (candidate.getpixel((x, 0)), candidate.getpixel((x, 207))))
                or any(p[3] for y in range(208) for p in
                       (candidate.getpixel((0, y)), candidate.getpixel((191, y))))}
    result["technicalPass"] = (different == 0 and result["baselineY"] == 203
                               and result["alphaValues"] == [0, 255] and not result["hiddenRgbPixels"]
                               and not result["touchesCellEdge"]
                               and result["connectedComponentSizes8"] == result["canonicalComponentSizes8"])
    return result


def pixel_overlay(original: Image.Image, candidate: Image.Image) -> Image.Image:
    """QA-only hard-edge overlay: white exact, cyan canonical, magenta candidate, yellow changed color."""
    out = Image.new("RGBA", (192, 208))
    values = []
    for a, b in zip(original.get_flattened_data(), candidate.get_flattened_data()):
        values.append((255, 255, 255, 255) if a == b and a[3]
                      else (0, 220, 255, 255) if a[3] and not b[3]
                      else (255, 0, 220, 255) if b[3] and not a[3]
                      else (255, 220, 0, 255) if a != b else (0, 0, 0, 0))
    out.putdata(values)
    return out


def prepare(output: Path = OUTPUT) -> dict:
    if output.exists():
        raise ValueError("refuse to overwrite an existing approval package")
    inputs = {form: canonical(form) for form in ("gu", "feng")}
    checks = {form: compare(cell, cell) for form, (_, cell) in inputs.items()}
    if not all(c["technicalPass"] for c in checks.values()):
        raise ValueError("canonical source failed; do not silently repair or recenter it")
    output.mkdir(parents=True)
    qa = output / "qa"
    qa.mkdir()
    strip = Image.new("RGBA", (768, 240), (35, 35, 35, 255))
    detailed = Image.new("RGBA", (768, 4 * 256), (35, 35, 35, 255))
    sd, dd = ImageDraw.Draw(strip), ImageDraw.Draw(detailed)
    records = []
    for index, (letter, name, form) in enumerate(ENDPOINTS):
        source, cell = inputs[form]
        file = output / f"{letter}-{name}.png"
        cell.save(file)
        with Image.open(file) as saved:
            check = compare(saved, cell)
        records.append({"id": letter, "name": name, "form": form, "file": file.name,
                        "canonicalSource": source.relative_to(ROOT).as_posix(), "row": 0, "frame": 0,
                        "sourceSha256": sha(source.read_bytes()), "pngSha256": sha(file.read_bytes()),
                        "humanApproval": "PENDING", **check})
        strip.alpha_composite(cell, (index * 192, 28))
        sd.text((index * 192 + 4, 4), f"{letter} {name}", fill="white")
        y = index * 256
        overlay = pixel_overlay(cell, cell)
        overlay.save(qa / f"{letter}-overlay.png")
        for col, (label, image) in enumerate((("canonical idle0", cell), ("endpoint draft", cell),
                                            ("overlay: white=exact", overlay), ("QA guides ONLY", cell))):
            x = col * 192
            detailed.alpha_composite(image, (x, y + 36))
            dd.text((x + 3, y + 3), f"{letter} {form} {label}", fill="white")
        x = 3 * 192
        dd.line((x + 96, y + 36, x + 96, y + 243), fill=(255, 100, 100, 255))
        dd.line((x, y + 36 + 203, x + 191, y + 36 + 203), fill=(255, 180, 60, 255))
        for key, color in (("headReferenceBbox", (90, 210, 255, 255)),
                           ("bodyReferenceBbox", (100, 255, 140, 255))):
            left, top, right, bottom = check["metrics"][key]
            dd.rectangle((x + left, y + 36 + top, x + right - 1, y + 36 + bottom - 1), outline=color)
        dd.text((4, y + 246), f"delta pixels=0; baseline=203; head/body deltas=0; body center={check['measuredBodyBandCenterX']}", fill="white")
    strip.save(qa / "four-endpoints-contact-sheet.png")
    detailed.save(qa / "canonical-overlay-and-landmarks.png")
    report = {"status": "AWAITING_MANUAL_ENDPOINT_APPROVAL", "technicalPass": True,
              "approvalScope": "Idle canonical frame0 only; not Running/hover/drag or full transition approval",
              "centerConvention": "x=96 registration anchor; measured asymmetric alpha/head/body hulls are not recentered",
              "bboxConvention": "half-open; head0:70/body70:208 fixed QA bands, NOT anatomical masks",
              "operation": "exact RGBA extraction; no translation, resizing, drawing, interpolation or effects",
              "intermediateFramesGenerated": 0, "animationGenerated": False, "runtimeEligible": False,
              "humanApproval": "PENDING", "endpoints": records}
    (qa / "validation.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    report = prepare(args.output)
    print(json.dumps({"status": report["status"], "count": len(report["endpoints"]),
                      "technicalPass": report["technicalPass"]}))
