"""Write three pose specifications and QA guides; never draw intermediate art."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image, ImageDraw

from tools.prepare_transition_animation_candidate import ENDPOINT_ROOT, digest, metrics

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "assets/rework/v0.1.0/transition-keyframes/gu-to-feng-spec"


def approved_inputs() -> list[tuple[str, Path, Image.Image]]:
    approval = json.loads((ENDPOINT_ROOT / "approval.json").read_text())
    if approval["status"] != "ENDPOINT_ART_APPROVED":
        raise ValueError("canonical endpoints not approved")
    result = []
    for letter, name in (("A", "A-gu-to-feng-entry.png"), ("B", "B-gu-to-feng-exit.png")):
        path = ENDPOINT_ROOT / name
        if digest(path) != approval["approvedFiles"][name]:
            raise ValueError("frozen endpoint changed")
        with Image.open(path) as image:
            result.append((letter, path, image.copy()))
    return result


def specification() -> dict:
    endpoints = []
    for letter, path, image in approved_inputs():
        info = metrics(image)
        # These MANUAL approximate anatomical guides are not automatic masks.
        # Feng's chin is partly obscured by his hand. Report that uncertainty.
        head = [54, 4, 122, 84] if letter == "A" else [64, 4, 113, 58]
        shoulders = [[75, 83], [108, 83]] if letter == "A" else [[60, 65], [128, 65]]
        endpoints.append({"id": letter, "file": str(path.relative_to(ROOT)), "sha256": digest(path),
                          "alphaBbox": info["alphaBbox"], "bodyReferenceBandBbox": info["bodyReferenceBbox"],
                          "headApproxBbox": head, "headApproxCenter": [(head[0] + head[2]) / 2, (head[1] + head[3]) / 2],
                          "hairTopY": 4, "chinYVisualRange": [78, 84] if letter == "A" else [54, 60],
                          "headCapBbox0to55": list(image.getchannel("A").crop((0, 0, 192, 55)).getbbox()),
                          "shoulderGuidePoints": shoulders, "shoulderGuideWidth": shoulders[1][0] - shoulders[0][0],
                          "registrationX": 96, "baselineY": 203})
    poses = [
        {"id": "K1", "progress": .1, "headApproxBboxTarget": [55, 4, 122, 81],
         "headCenterXRange": [86, 91], "hairTopYRange": [3, 6], "shoulderGuideWidthRange": [33, 40],
         "bodyBandWidthRange": [53, 61], "action": "Charge: still recognizably Gu; tiny straightening, shoulders still narrow; hands barely begin leaving resting position; no sudden chin-hand pose"},
        {"id": "K2", "progress": .5, "headApproxBboxTarget": [59, 4, 118, 71],
         "headCenterXRange": [86, 91], "hairTopYRange": [3, 6], "shoulderGuideWidthRange": [46, 55],
         "bodyBandWidthRange": [70, 86], "action": "Mid Transformation: genuinely intermediate torso/shoulders, legs gradually widen; same face turning slightly, hand travels gradually toward chin"},
        {"id": "K3", "progress": .9, "headApproxBboxTarget": [63, 4, 114, 61],
         "headCenterXRange": [86, 91], "hairTopYRange": [3, 6], "shoulderGuideWidthRange": [62, 68],
         "bodyBandWidthRange": [95, 104], "action": "Pre-Feng: nearly exact B stance, face angle, hair and hand-to-chin pose; no frontal round face, enlarged skull or over-wide body before B"},
    ]
    return {"status": "KEYFRAME_SPECIFICATION_ONLY", "scope": "Idle canonical; Running NOT APPROVED",
            "sequence": ["A", "K1", "K2", "K3", "B"], "newPoseCount": 3,
            "canvas": [192, 208], "registrationX": 96, "baselineY": 203,
            "endpointOperation": "exact frozen PNG copy; no recoloring, translating or resampling",
            "generatedArtworkCount": 0, "fullAnimationAllowed": False, "appIntegrationAllowed": False,
            "manualApprovalRequired": True, "runtimeEligible": False,
            "landmarkConvention": "half-open; anatomical head/shoulder guides are manual approximate visual annotations, not segmentation ground truth; headCap0:55/body70:208 are fixed alpha reference bands, not anatomy",
            "uncertainty": "Feng chin partly hand-occluded; Gu jaw roughly y78-84, Feng y54-60; re-annotate candidates rather than measuring shoulders as head",
            "effects": {"preferred": "none for keyframe approval; character change is primary", "allowed": "small attached hard-edge accents only outside face/glasses/shirt/torso/feet", "forbidden": "glow, blur, aura, detached speckles, effects used to hide silhouette/face changes"},
            "pairChecks": ["head center delta and hair-top continuity", "baseline exactly203", "body band bbox and monotonic width evidence", "manual shoulder width", "face/glasses/hair identity", "hand/leg pose continuity", "visual center distinct from registration anchor"],
            "gatePolicy": "metrics only flag evidence; obvious visual snap is FAIL even if metrics pass; no KEYFRAME_ART_APPROVED before user approval; no remaining five frames",
            "endpoints": endpoints, "poses": poses}


def prepare(output: Path = OUTPUT) -> dict:
    if output.exists():
        raise ValueError("refuse to overwrite specification")
    report = specification()
    output.mkdir(parents=True)
    # QA-only reference drawings; never offered as candidate character artwork.
    sheet = Image.new("RGBA", (768, 260), (35, 35, 35, 255))
    draw = ImageDraw.Draw(sheet)
    for i, (letter, _, image) in enumerate(approved_inputs()):
        item = report["endpoints"][i]
        for col in (i * 2, i * 2 + 1):
            x = col * 192
            sheet.alpha_composite(image, (x, 28))
            draw.text((x + 3, 3), f"{letter} {'canonical' if col % 2 == 0 else 'QA guides ONLY'}", fill="white")
            if col % 2:
                draw.line((x + 96, 28, x + 96, 235), fill=(255, 90, 90, 255))
                draw.line((x, 231, x + 191, 231), fill=(255, 175, 45, 255))
                l, t, r, b = item["headApproxBbox"]
                draw.rectangle((x + l, 28 + t, x + r - 1, 28 + b - 1), outline=(90, 215, 255, 255))
                p, q = item["shoulderGuidePoints"]
                draw.line((x + p[0], p[1] + 28, x + q[0], q[1] + 28), fill=(100, 255, 130, 255))
                draw.text((x + 3, 240), "manual ROI / not auto mask", fill="white")
    sheet.save(output / "canonical-landmark-guide.png")
    layout = Image.new("RGBA", (576, 208), (245, 245, 245, 255))
    ld = ImageDraw.Draw(layout)
    for i, pose in enumerate(report["poses"]):
        x = i * 192
        ld.rectangle((x, 0, x + 191, 207), outline=(180, 180, 180, 255))
        ld.line((x + 96, 0, x + 96, 207), fill=(190, 110, 110, 255))
        ld.line((x, 203, x + 191, 203), fill=(150, 120, 80, 255))
        l, t, r, b = pose["headApproxBboxTarget"]
        ld.rectangle((x + l, t, x + r - 1, b - 1), outline=(90, 155, 190, 255))
    layout.save(output / "layout-guide.png")
    (output / "specification.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    print(json.dumps({k: v for k, v in prepare(args.output).items() if k in ("status", "newPoseCount", "generatedArtworkCount")}))
