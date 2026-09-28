"""Extract three already-generated poses and compare five keys, not an animation."""
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
import shutil

from PIL import Image, ImageDraw

from tools.extract_transition_pose_regions import DETECTOR
from tools.prepare_manual_transition_endpoints import pixel_overlay
from tools.prepare_transition_animation_candidate import digest, harden_alpha, metrics
from tools.specify_transition_keyframes import approved_inputs, specification


def source_regions(image: Image.Image, detector: Path = DETECTOR) -> list[list[int]]:
    if image.mode != "RGBA" or image.getchannel("A").getextrema()[0] != 0:
        raise ValueError("genuine transparent RGBA source required")
    spec = importlib.util.spec_from_file_location("hatch_key_component_detector", detector)
    if spec is None or spec.loader is None:
        raise ValueError("installed hatch component detector required")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    components = module.connected_components(image)
    largest = max((c["area"] for c in components), default=0)
    cores = sorted([c for c in components if c["area"] >= max(120, largest * .2)], key=lambda c: c["center_x"])
    if len(cores) != 3:
        raise ValueError("expected exactly THREE separated intermediate poses; do not manufacture missing keys")
    for core in cores:
        l, t, r, b = core["bbox"]
        if l == 0 or t == 0 or r == image.width or b == image.height:
            raise ValueError("source character touches edge; reject incomplete source")
    cuts = [0]
    for left, right in zip(cores, cores[1:]):
        a, b = left["bbox"][2], right["bbox"][0]
        if a >= b:
            raise ValueError("overlapping poses; cannot safely recover horizontal keys")
        cuts.append((a + b) // 2)
    cuts.append(image.width)
    return [[cuts[i], 0, cuts[i + 1], image.height] for i in range(3)]


def prepare(source: Path, output: Path) -> dict:
    if output.exists():
        raise ValueError("refuse to overwrite existing keyframe candidates")
    with Image.open(source) as opened:
        original = opened.copy()
    regions = source_regions(original)
    raw = [original.crop(region) for region in regions]
    clean = [harden_alpha(image)[0] for image in raw]
    bounds = [image.getchannel("A").getbbox() for image in clean]
    if any(b is None for b in bounds):
        raise ValueError("empty generated key pose")
    scale = min(1., 200 / max(b[3] - b[1] for b in bounds))
    cells, records = [], []
    for i, (region, crop) in enumerate(zip(regions, raw)):
        # One common NN normalization from the original, never independent fit.
        size = [round(crop.width * scale), round(crop.height * scale)]
        cell_source, alpha_changes = harden_alpha(crop.resize(size, Image.Resampling.NEAREST))
        bbox = cell_source.getchannel("A").getbbox()
        lower_top = int(bbox[1] + .72 * (bbox[3] - bbox[1]))
        lower = cell_source.getchannel("A").crop((0, lower_top, cell_source.width, cell_source.height)).getbbox()
        anchor = (lower[0] + lower[2]) / 2
        dx, dy = round(96 - anchor), 204 - bbox[3]
        projected = [bbox[0] + dx, bbox[1] + dy, bbox[2] + dx, bbox[3] + dy]
        if projected[0] < 1 or projected[1] < 1 or projected[2] > 191 or projected[3] > 207:
            raise ValueError("common normalization would clip foreground; no per-pose scale workaround")
        cell = Image.new("RGBA", (192, 208))
        cell.paste(cell_source, (dx, dy))
        if sum(cell.getchannel("A").histogram()[1:]) != sum(cell_source.getchannel("A").histogram()[1:]):
            raise ValueError("foreground lost during registration")
        cells.append(cell)
        cap = cell.getchannel("A").crop((0, 0, 192, 55)).getbbox()
        records.append({"id": f"K{i + 1}", "origin": "generated intermediate artwork, not transformed endpoints",
                        "sourceRegion": region, "sourceResizeSize": size, "commonScale": scale,
                        "integerShift": [dx, dy], "alphaHardenedPixels": alpha_changes,
                        "lowerBodyAnchorX": anchor + dx, "headCapBbox0to55": list(cap) if cap else None,
                        **metrics(cell)})
    approved = approved_inputs()
    all_cells = [approved[0][2], *cells, approved[1][2]]
    all_records = [{"id": "A", "origin": "exact approved PNG", **metrics(approved[0][2])}, *records,
                   {"id": "B", "origin": "exact approved PNG", **metrics(approved[1][2])}]
    frames, qa = output / "keys", output / "qa"
    frames.mkdir(parents=True)
    qa.mkdir()
    sheet = Image.new("RGBA", (960, 240), (35, 35, 35, 255))
    guides = Image.new("RGBA", (960, 240), (35, 35, 35, 255))
    sd, gd = ImageDraw.Draw(sheet), ImageDraw.Draw(guides)
    for i, (cell, item) in enumerate(zip(all_cells, all_records)):
        file = frames / f"{item['id']}.png"
        if i in (0, 4):
            shutil.copyfile(approved[0 if i == 0 else 1][1], file)
        else:
            cell.save(file)
        item.update({"file": f"keys/{item['id']}.png", "sha256": digest(file)})
        if "headCapBbox0to55" not in item:
            item["headCapBbox0to55"] = list(cell.getchannel("A").crop((0, 0, 192, 55)).getbbox())
        for canvas, draw in ((sheet, sd), (guides, gd)):
            x = i * 192
            canvas.alpha_composite(cell, (x, 28))
            draw.text((x + 3, 3), f"{item['id']} {'FROZEN' if i in (0, 4) else 'CANDIDATE'}", fill="white")
        gd.line((i * 192 + 96, 28, i * 192 + 96, 235), fill=(255, 90, 90, 255))
        gd.line((i * 192, 231, i * 192 + 191, 231), fill=(255, 175, 45, 255))
    sheet.save(qa / "contact-sheet.png")
    guides.save(qa / "registration-guide.png")
    pairs = []
    for i, (a, b) in enumerate(zip(all_cells, all_cells[1:])):
        left, right = all_records[i], all_records[i + 1]
        cap_a, cap_b = left["headCapBbox0to55"], right["headCapBbox0to55"]
        ac = [(cap_a[0] + cap_a[2]) / 2, (cap_a[1] + cap_a[3]) / 2] if cap_a else None
        bc = [(cap_b[0] + cap_b[2]) / 2, (cap_b[1] + cap_b[3]) / 2] if cap_b else None
        pairs.append({"pair": f"{left['id']}->{right['id']}", "baselineDelta": right["baselineY"] - left["baselineY"],
                      "headCapCenterDelta": [v - u for u, v in zip(ac, bc)] if ac and bc else None,
                      "bodyBandBboxDelta": [v - u for u, v in zip(left["bodyReferenceBbox"], right["bodyReferenceBbox"])],
                      "rgbaChangedPixels": sum(a != b for a, b in zip(a.get_flattened_data(), b.get_flattened_data()))})
        panel = Image.new("RGBA", (576, 244), (35, 35, 35, 255))
        pd = ImageDraw.Draw(panel)
        for j, (label, image) in enumerate(((left["id"], a), (right["id"], b), ("diff overlay", pixel_overlay(a, b)))):
            panel.alpha_composite(image, (j * 192, 28))
            pd.text((j * 192 + 3, 3), label, fill="white")
            pd.line((j * 192, 231, j * 192 + 191, 231), fill=(255, 175, 45, 255))
        panel.save(qa / f"pair-{i + 1}.png")
    report = {"status": "AWAITING_INDEPENDENT_KEYFRAME_REVIEW", "sourceSha256": digest(source),
              "sourceSize": list(original.size), "poseCount": 5, "newArtworkCount": 3,
              "fullAnimationGenerated": False, "appIntegrated": False, "runtimeEligible": False,
              "manualApproval": "PENDING", "commonNearestScale": scale, "perPoseScale": False,
              "bboxConvention": specification()["landmarkConvention"],
              "headMeasurement": "head-cap0:55 proxy only; anatomical head/shoulders require independent manual annotation, not assumed from specification targets",
              "frames": all_records, "adjacentPairs": pairs}
    report["structuralPass"] = all(r["baselineY"] == 203 and r["alphaValues"] == [0, 255]
                                   and not r["hiddenRgbPixels"] and not r["touchesCellEdge"]
                                   and not r["isolatedSinglePixels"] for r in all_records)
    (qa / "validation.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


def annotate_landmarks(output: Path, annotations: Path) -> dict:
    """Measure independently annotated anatomy; never assume target ROIs are actual."""
    report = json.loads((output / "qa/validation.json").read_text())
    notes = json.loads(annotations.read_text())
    if [r["id"] for r in notes["frames"]] != ["A", "K1", "K2", "K3", "B"]:
        raise ValueError("exact five manual landmark records required")
    if len(notes["adjacentPairs"]) != 4:
        raise ValueError("exact four manual pair verdicts required")
    if notes["visualVerdict"] not in ("KEYFRAME_QA_FAIL", "AWAITING_MANUAL_KEYFRAME_APPROVAL"):
        raise ValueError("tool cannot grant human keyframe approval")
    result = {"status": notes["visualVerdict"], "manualApproval": "PENDING", "runtimeEligible": False,
              "annotationConvention": "independent approximate anatomical ROIs; half-open logical192x208 coordinates; not automatic segmentation",
              "annotationUncertainty": notes.get("annotationUncertainty", "approximate manual annotations; not segmentation ground truth"),
              "reviewer": notes["reviewer"], "frames": [], "adjacentPairs": []}
    for frame, note in zip(report["frames"], notes["frames"]):
        bbox = note["headApproxBbox"]
        if len(bbox) != 4 or not (0 <= bbox[0] < bbox[2] <= 192 and 0 <= bbox[1] < bbox[3] <= 208):
            raise ValueError("invalid manual head ROI")
        points = note["shoulderGuidePoints"]
        if len(points) != 2 or any(len(p) != 2 or not (0 <= p[0] < 192 and 0 <= p[1] < 208) for p in points):
            raise ValueError("invalid manual shoulder annotation")
        center = [(bbox[0] + bbox[2]) / 2, (bbox[1] + bbox[3]) / 2]
        values = {"id": frame["id"], "headApproxBbox": bbox, "headApproxCenter": center,
                  "shoulderGuidePoints": points, "shoulderGuideWidth": abs(points[1][0] - points[0][0]),
                  "bodyReferenceBbox": frame["bodyReferenceBbox"], "baselineY": frame["baselineY"],
                  "bodyBandCenterX": frame["bodyBandCenterX"], "visualNotes": note["visualNotes"]}
        result["frames"].append(values)
    for i, (a, b) in enumerate(zip(result["frames"], result["frames"][1:])):
        verdict = notes["adjacentPairs"][i]
        if verdict["pair"] != f"{a['id']}->{b['id']}":
            raise ValueError("manual pair order mismatch")
        if verdict["verdict"] not in ("pass", "warning", "fail"):
            raise ValueError("invalid manual pair verdict")
        if verdict["verdict"] == "fail" and notes["visualVerdict"] != "KEYFRAME_QA_FAIL":
            raise ValueError("failed pair cannot be marked awaiting approval")
        result["adjacentPairs"].append({**verdict,
            "headCenterDelta": [v - u for u, v in zip(a["headApproxCenter"], b["headApproxCenter"])],
            "baselineDelta": b["baselineY"] - a["baselineY"],
            "bodyBboxDelta": [v - u for u, v in zip(a["bodyReferenceBbox"], b["bodyReferenceBbox"])],
            "shoulderWidthDelta": b["shoulderGuideWidth"] - a["shoulderGuideWidth"],
            "visualBodyCenterDelta": b["bodyBandCenterX"] - a["bodyBandCenterX"]})
    result["observedIssues"] = notes.get("observedIssues", [])
    (output / "qa/landmark-comparison.json").write_text(json.dumps(result, indent=2) + "\n")
    sheet = Image.new("RGBA", (960, 240), (35, 35, 35, 255))
    draw = ImageDraw.Draw(sheet)
    for i, (frame, note) in enumerate(zip(report["frames"], result["frames"])):
        with Image.open(output / frame["file"]) as image:
            sheet.alpha_composite(image, (i * 192, 28))
        x = i * 192
        draw.text((x + 3, 3), f"{note['id']} manual head/shoulder", fill="white")
        l, t, r, b = note["headApproxBbox"]
        draw.rectangle((x + l, t + 28, x + r - 1, b + 27), outline=(90, 215, 255, 255))
        a, b = note["shoulderGuidePoints"]
        draw.line((x + a[0], a[1] + 28, x + b[0], b[1] + 28), fill=(100, 255, 130, 255))
        draw.line((x + 96, 28, x + 96, 235), fill=(255, 90, 90, 255))
        draw.line((x, 231, x + 191, 231), fill=(255, 175, 45, 255))
    sheet.save(output / "qa/manual-landmark-contact-sheet.png")
    report["status"] = result["status"]
    report["independentVisualQa"] = result["status"]
    report["landmarkEvidence"] = "qa/landmark-comparison.json"
    (output / "qa/validation.json").write_text(json.dumps(report, indent=2) + "\n")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = prepare(args.source, args.output)
    print(json.dumps({k: result[k] for k in ("status", "poseCount", "newArtworkCount", "structuralPass")}))
