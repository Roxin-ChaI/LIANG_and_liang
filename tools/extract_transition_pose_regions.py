"""Recover complete source regions, without resampling or changing RGBA pixels.

The installed hatch-pet component detector locates alpha>16 character cores.
Transparent gaps between actual core bounds, NOT equal slots, define regions.
All source pixels (including low-alpha fringe, hidden RGB and detached marks)
are retained exactly once in the native inspection PNGs. No runtime fit is
silently attempted when scaling is forbidden.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
from pathlib import Path

from PIL import Image, ImageDraw

from tools.prepare_transition_animation_candidate import harden_alpha

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "assets/rework/v0.1.0/transition-full/sources/feng-to-gu-generated-retry.png"
DETECTOR = Path.home() / ".codex/skills/hatch-pet/scripts/extract_strip_frames.py"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def detect_regions(image: Image.Image, detector: Path = DETECTOR) -> list[dict]:
    if image.mode != "RGBA":
        raise ValueError("RGBA source required; no conversion/background keying")
    spec = importlib.util.spec_from_file_location("hatch_component_detector", detector)
    if spec is None or spec.loader is None:
        raise ValueError("installed hatch-pet component detector required")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    components = module.connected_components(image)
    largest = max((c["area"] for c in components), default=0)
    cores = [c for c in components if c["area"] >= max(120, largest * .2)]
    if len(cores) != 8:
        raise ValueError("SOURCE_REGIONS_AMBIGUOUS: expected exactly eight substantial poses")
    for core in cores:
        l, t, r, b = core["bbox"]
        if l == 0 or t == 0 or r == image.width or b == image.height:
            raise ValueError("SOURCE_ART_INCOMPLETE: substantial character touches source edge")
    cores.sort(key=lambda c: (c["bbox"][1] + c["bbox"][3]) / 2)
    centers = [(c["bbox"][1] + c["bbox"][3]) / 2 for c in cores]
    split = max(range(1, 8), key=lambda i: centers[i] - centers[i - 1])
    rows = (cores[:split], cores[split:])
    if any(len(row) != 4 for row in rows):
        raise ValueError("SOURCE_REGIONS_AMBIGUOUS: actual bounds do not expose two four-pose rows")
    top_end = max(c["bbox"][3] for c in rows[0])
    bottom_start = min(c["bbox"][1] for c in rows[1])
    if bottom_start <= top_end:
        raise ValueError("SOURCE_REGIONS_AMBIGUOUS: no horizontal gap between rows")
    row_cut = (top_end + bottom_start) // 2
    result = []
    for row_index, row in enumerate(rows):
        row.sort(key=lambda c: c["center_x"])
        cuts = [0]
        for left, right in zip(row, row[1:]):
            a, b = left["bbox"][2], right["bbox"][0]
            if b <= a:
                raise ValueError("SOURCE_REGIONS_AMBIGUOUS: no gap between neighboring subjects")
            cuts.append((a + b) // 2)
        cuts.append(image.width)
        y1, y2 = (0, row_cut) if row_index == 0 else (row_cut, image.height)
        for column, core in enumerate(row):
            region = [cuts[column], y1, cuts[column + 1], y2]
            l, t, r, b = core["bbox"]
            if not (region[0] <= l < r <= region[2] and y1 <= t < b <= y2):
                raise ValueError("SOURCE_REGIONS_AMBIGUOUS: proposed boundary cuts character")
            lower = [p % image.width for p in core["pixels"]
                     if p // image.width >= t + .72 * (b - t)]
            anchor = (min(lower) + max(lower) + 1) / 2
            result.append({"index": len(result), "sourceRegion": region,
                           "subjectCoreBbox": list(core["bbox"]), "subjectCorePixels": core["area"],
                           "lowerBodyAnchorX": anchor, "sourceSoleY": b - 1})
    return result


def extract(source: Path, output: Path, detector: Path = DETECTOR) -> dict:
    if output.exists():
        raise ValueError("refuse to overwrite existing extraction")
    with Image.open(source) as opened:
        image = opened.copy()
    regions = detect_regions(image, detector)
    # The current reverse overlay's LOCAL anchor105/217 becomes logical96/203
    # via fixed offsets-9/-14. Preserve that contract; do not enlarge it silently.
    layout = json.loads((ROOT / "runtime-patch/fixtures/transition-overlay-layout.json").read_text())["feng_to_gu"]
    max_left = max(r["lowerBodyAnchorX"] - r["sourceRegion"][0] for r in regions)
    max_right = max(r["sourceRegion"][2] - r["lowerBodyAnchorX"] for r in regions)
    max_top = max(r["sourceSoleY"] - r["sourceRegion"][1] for r in regions)
    max_bottom = max(r["sourceRegion"][3] - r["sourceSoleY"] - 1 for r in regions)
    anchor = math.ceil(max_left) + 8
    sole = max_top + 8
    canvas = (anchor + math.ceil(max_right) + 8, sole + max_bottom + 9)
    frames, qa = output / "native-inspection-frames", output / "qa"
    frames.mkdir(parents=True)
    qa.mkdir()
    rebuilt = Image.new("RGBA", image.size)
    for item in regions:
        region = item["sourceRegion"]
        crop = image.crop(region)
        x = round(anchor - (item["lowerBodyAnchorX"] - region[0]))
        y = sole - (item["sourceSoleY"] - region[1])
        frame = Image.new("RGBA", canvas)
        frame.paste(crop, (x, y))  # NO alpha mask: retain original RGB/alpha values.
        if frame.crop((x, y, x + crop.width, y + crop.height)).tobytes() != crop.tobytes():
            raise ValueError("native canvas would truncate source pixels")
        rebuilt.paste(crop, (region[0], region[1]))
        file = frames / f"feng_to_gu_{item['index']:02d}.png"
        frame.save(file)
        with Image.open(file) as saved:
            if saved.tobytes() != frame.tobytes():
                raise ValueError("PNG roundtrip changed RGBA pixels")
        core = item["subjectCoreBbox"]
        dx = round(layout["anchorX"] - item["lowerBodyAnchorX"])
        dy = layout["anchorY"] - item["sourceSoleY"]
        projected = [core[0] + dx, core[1] + dy, core[2] + dx, core[3] + dy]
        fits = projected[0] >= 0 and projected[1] >= 0 and projected[2] <= layout["canvasWidth"] and projected[3] <= layout["canvasHeight"]
        item.update({"file": str(file.relative_to(output)), "pngSha256": sha(file),
                     "nativePaste": [x, y], "nativeSoleY": sole,
                     "nativeLowerBodyAnchorX": item["lowerBodyAnchorX"] - region[0] + x,
                     "sourceRgbaPreserved": True, "requestedRuntimeCoreBbox": projected,
                     "fitsUnscaledRuntime": fits})
    if rebuilt.tobytes() != image.tobytes():
        raise ValueError("source coverage mismatch; unassigned, lost or duplicated pixels")
    # Preview-only nearest-neighbor thumbnail. Native asset PNGs are NOT resized.
    thumb = .5
    w, h = round(canvas[0] * thumb), round(canvas[1] * thumb)
    sheet = Image.new("RGBA", (4 * w, 2 * (h + 30)), (35, 35, 35, 255))
    draw = ImageDraw.Draw(sheet)
    for item in regions:
        with Image.open(output / item["file"]) as frame:
            preview = frame.resize((w, h), Image.Resampling.NEAREST)
        x, y = item["index"] % 4 * w, item["index"] // 4 * (h + 30)
        sheet.alpha_composite(preview, (x, y + 26))
        draw.text((x + 3, y + 3), f"{item['index']:02d} NATIVE / not runtime", fill="white")
        draw.line((x, y + 26 + round(sole * thumb), x + w - 1, y + 26 + round(sole * thumb)), fill=(255, 170, 50, 255))
    sheet.save(qa / "contact-sheet.png")
    report = {"status": "NATIVE_EXTRACTION_PASS_RUNTIME_CANVAS_BLOCKED", "sourceSha256": sha(source),
              "sourceSize": list(image.size), "poseCount": 8, "subjectDetector": "hatch-pet alpha>16 components; eight substantial cores",
              "regionPolicy": "actual core gaps; every original RGBA pixel retained exactly once, including faint fringe and detached marks",
              "nativeCanvas": list(canvas), "nativeRegistrationX": anchor, "nativeBaselineY": sole,
              "runtimeCanvas": [layout["canvasWidth"], layout["canvasHeight"]], "runtimeAnchorX": layout["anchorX"],
              "runtimeBaselineY": layout["anchorY"], "logicalRegistration": {"x": 96, "baseline": 203},
              "sourceReconstructedExactly": True, "resizeOperationsOnAssets": 0, "redrawOperations": 0,
              "runtimeEligible": False, "sourceArtIncomplete": False, "visualIdentityApproved": False,
              "blocker": "SCALING_FORBIDDEN_NATIVE_POSES_EXCEED_EXISTING_RUNTIME_CANVAS",
              "previewOnlyScale": .5, "frames": regions}
    (qa / "validation.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


def normalize_shared_nearest(source: Path, output: Path, detector: Path = DETECTOR) -> dict:
    """Explicit opt-in authorized by user; one common scale, no per-pose fitting."""
    if output.exists():
        raise ValueError("refuse to overwrite existing normalized extraction")
    with Image.open(source) as opened:
        image = opened.copy()
    regions = detect_regions(image, detector)
    # The largest complete native pose controls one shared transform. Regions
    # include every detached mark; scale never depends on an individual frame.
    scale = min(1., 200 / max(r["subjectCoreBbox"][3] - r["subjectCoreBbox"][1] for r in regions))
    normal, runtime, qa = output / "normal-frames", output / "runtime-frames", output / "qa"
    cells, records = [], []
    for item in regions:
        region = item["sourceRegion"]
        original = image.crop(region)
        size = (round(original.width * scale), round(original.height * scale))
        nearest = original.resize(size, Image.Resampling.NEAREST)
        cleaned, partial = harden_alpha(nearest)
        bbox = cleaned.getchannel("A").getbbox()
        if bbox is None:
            raise ValueError("empty normalized pose")
        top = int(bbox[1] + .72 * (bbox[3] - bbox[1]))
        lower = cleaned.getchannel("A").crop((0, top, cleaned.width, cleaned.height)).getbbox()
        anchor = (lower[0] + lower[2]) / 2
        dx, dy = round(96 - anchor), 204 - bbox[3]
        projected = [bbox[0] + dx, bbox[1] + dy, bbox[2] + dx, bbox[3] + dy]
        if projected[0] < 1 or projected[1] < 1 or projected[2] > 191 or projected[3] > 207:
            raise ValueError("shared transform would clip foreground; no per-pose scale workaround")
        cell = Image.new("RGBA", (192, 208))
        cell.paste(cleaned, (dx, dy))
        if sum(cell.getchannel("A").histogram()[1:]) != sum(cleaned.getchannel("A").histogram()[1:]):
            raise ValueError("normalized foreground pixel lost during registration")
        cells.append(cell)
        records.append({**item, "sharedScale": scale, "sourceRegionSize": list(original.size),
                        "singleNearestResizeSize": list(size), "integerShift": [dx, dy],
                        "alphaHardenedPixels": partial, "alphaPolicy": "threshold128; RGB unchanged for kept pixels, transparent RGB zero",
                        "normalAlphaBbox": projected, "normalLowerBodyCenterX": anchor + dx,
                        "normalBaselineY": 203, "foregroundLostToCanvas": 0})
    normal.mkdir(parents=True)
    runtime.mkdir()
    qa.mkdir()
    sheet = Image.new("RGBA", (768, 480), (35, 35, 35, 255))
    draw = ImageDraw.Draw(sheet)
    for i, (cell, item) in enumerate(zip(cells, records)):
        filename = f"feng_to_gu_{i:02d}.png"
        cell.save(normal / filename)
        overlay = Image.new("RGBA", (208, 224))
        overlay.paste(cell, (9, 14))
        overlay.save(runtime / filename)
        assert overlay.crop((9, 14, 201, 222)).tobytes() == cell.tobytes()
        item.update({"normalFile": f"normal-frames/{filename}", "runtimeFile": f"runtime-frames/{filename}",
                     "normalSha256": sha(normal / filename), "runtimeSha256": sha(runtime / filename),
                     "runtimeCanvas": [208, 224], "runtimeBaselineY": 217,
                     "runtimeRegistrationX": 105, "logicalRegistration": {"x": 96, "baseline": 203}})
        x, y = i % 4 * 192, i // 4 * 240
        draw.text((x + 3, y + 3), f"{i:02d} extracted / art unapproved", fill="white")
        sheet.alpha_composite(cell, (x, y + 24))
        draw.line((x, y + 227, x + 191, y + 227), fill=(255, 170, 50, 255))
    sheet.save(qa / "contact-sheet.png")
    report = {"status": "EXTRACTION_PASS_ART_UNAPPROVED", "sourceSha256": sha(source), "poseCount": 8,
              "authorization": "User explicitly allowed ONE common nearest-neighbor normalization after native-size conflict was demonstrated",
              "sharedScale": scale, "sourceRegionsFromActualBounds": True, "perPoseScale": False,
              "scaleInterpolation": "NEAREST only, one resize from original region per pose",
              "nativeRgbaEvidence": "../qa/validation.json and ../native-inspection-frames/ retain original RGBA unchanged",
              "redrawOperations": 0, "foregroundLostToCanvas": 0,
              "normalCanvas": [192, 208], "runtimeCanvas": [208, 224],
              "runtimeOffset": [-9, -14], "logicalRegistration": {"x": 96, "baseline": 203},
              "alphaValues": [0, 255], "hiddenTransparentRgb": 0,
              "identityApproved": False, "endpointContinuityApproved": False,
              "appIntegrated": False, "runtimeEligible": False, "frames": records}
    (qa / "validation.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=SOURCE)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--detector", type=Path, default=DETECTOR)
    parser.add_argument("--normalize-shared-nearest", action="store_true", help="requires explicit authorization to relax no-scaling constraint")
    args = parser.parse_args()
    if args.normalize_shared_nearest:
        report = normalize_shared_nearest(args.source, args.output, args.detector)
        print(json.dumps({k: report[k] for k in ("status", "poseCount", "sharedScale", "runtimeEligible")}))
    else:
        report = extract(args.source, args.output, args.detector)
        print(json.dumps({k: report[k] for k in ("status", "poseCount", "nativeCanvas", "nativeBaselineY", "runtimeEligible")}))
