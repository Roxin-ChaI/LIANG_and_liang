"""Bounded native-pixel KB2 -> KF1 -> KF2 -> F0 art contract.

Visual findings are independent of numeric geometry. No runtime code is touched.
"""
from __future__ import annotations

import json
from pathlib import Path

from PIL import Image

from tools.audit_b_endpoint_compatibility import KB2, KB2_SHA
from tools.f0_transition_endpoint_spec import OUT, specification as check_frozen
from tools.prepare_transition_animation_candidate import digest
from tools.transition_bridge_spec import landmark

OUTPUT = OUT / "morph-bridge"
F0 = OUT / "manual-pixel-art/F0.png"
F0_SHA = "9e3a64dd388318fa2d48ca630e71a765e3302093f9ff9c6571f8eadef38b8f84"
HEAD_GUIDES = {
    "KB2": [60, 4, 116, 72], "KF1": [61, 4, 115, 68],
    "KF2": [62, 4, 114, 63], "F0": [64, 4, 114, 59],
}
LIMITS = {"headSize": 6, "headCenterX": 3, "headCenterY": 4,
          "bodyWidth": 10, "handCenterX": 8, "handCenterY": 6}


def sources() -> dict[str, Image.Image]:
    check_frozen()
    images = {}
    for name, path, expected in (("KB2", KB2, KB2_SHA), ("F0", F0, F0_SHA)):
        if digest(path) != expected:
            raise ValueError(f"retained {name} changed")
        with Image.open(path) as image:
            if image.mode != "RGBA" or image.size != (192, 208):
                raise ValueError("native 192x208 RGBA required")
            images[name] = image.copy()
    return images


def hand_guides(image: Image.Image) -> dict:
    """Visible skin bounds below the chest; border/cloth not counted as hand.

    This is a repeatable advisory measurement, not an anatomical mask or
    identity proof. The numeric guides must be compared with the actual art.
    """
    result = {}
    for side, x0, x1 in (("left", 0, 96), ("right", 96, 192)):
        points = []
        for y in range(110, 175):
            for x in range(x0, x1):
                r, g, b, a = image.getpixel((x, y))
                if a and r > 140 and r-g > 12 and g-b > 5:
                    points.append((x, y))
        if not points:
            raise ValueError(f"no visible {side} hand skin guide")
        box = [min(x for x, _ in points), min(y for _, y in points),
               max(x for x, _ in points)+1, max(y for _, y in points)+1]
        result[side] = {"skinBbox": box, "center": [(box[0]+box[2])/2, (box[1]+box[3])/2]}
    return result


def pair(left: dict, right: dict, lh: dict, rh: dict) -> dict:
    hd = [b-a for a, b in zip(left["headSize"], right["headSize"])]
    hc = [b-a for a, b in zip(left["headCenter"], right["headCenter"])]
    bw = right["bodyWidth"]-left["bodyWidth"]
    hands = {side: [b-a for a,b in zip(lh[side]["center"], rh[side]["center"])]
             for side in ("left", "right")}
    checks = {
        "headSize": all(abs(d) <= LIMITS["headSize"] for d in hd),
        "headCenterX": abs(hc[0]) <= LIMITS["headCenterX"],
        "headCenterY": abs(hc[1]) <= LIMITS["headCenterY"],
        "bodyWidth": abs(bw) <= LIMITS["bodyWidth"],
        "hands": all(abs(d[0]) <= LIMITS["handCenterX"] and abs(d[1]) <= LIMITS["handCenterY"] for d in hands.values()),
        "baseline203": left["baselineY"] == right["baselineY"] == 203,
        "registration96": left["registrationX"] == right["registrationX"] == 96,
    }
    return {"headSizeDelta": hd, "headCenterDelta": hc, "bodyWidthDelta": bw,
            "handCenterDelta": hands, "checks": checks, "numericPass": all(checks.values()),
            "visualPass": None, "face": "INDEPENDENT_VISUAL_QA", "suit": "INDEPENDENT_VISUAL_QA",
            "arms": "INDEPENDENT_VISUAL_QA", "artApproved": False}


def specification() -> dict:
    images = sources()
    endpoints = {name: landmark(image, HEAD_GUIDES[name], approximate=True)
                 for name, image in images.items()}
    hands = {name: hand_guides(image) for name, image in images.items()}
    return {
        "status": "SPECIFICATION_ONLY", "imageOutputs": 0,
        "sources": {"KB2": {"path": str(KB2), "sha256": KB2_SHA},
                    "F0": {"path": str(F0), "sha256": F0_SHA, "artApproved": False}},
        "canvas": [192, 208], "baseline": 203, "registration": 96,
        "limits": LIMITS, "headGuides": HEAD_GUIDES,
        "endpoints": endpoints, "endpointHandSkinGuides": hands,
        "targetHandCenters": {"KF1": {"left": [75, 145], "right": [116, 148]},
                              "KF2": {"left": [69, 143.5], "right": [122, 145]}},
        "channels": {
            "KF1": {"identity": "KB2 hair/face/glasses source pixels, explicit local row/column removal only; relaxed expression retained",
                    "suit": "dark navy still dominant; initial blue shoulder/lapel accents and first tailored seam, no wholesale jacket replacement",
                    "arms": "hands move outward about 5px, slightly up; original low forearms and small hand shapes remain",
                    "legs": "feet and soles byte-identical to KB2; posture straightens above ankles"},
            "KF2": {"identity": "further bounded skull reduction; modest brow/lid tightening; no abrupt full-face replacement",
                    "suit": "blue tailored torso mostly developed; F0 sleeve/jacket structure emerges gradually",
                    "arms": "hands advance about 6px toward F0 low fists; clench and cuff shape develop",
                    "legs": "approach F0 neutral stance without a broad Feng Idle foot jump"},
            "F0": {"identity": "retained finished Feng face/pose; complete blue tailored suit and low arms"}},
        "method": "hand-selected native pixel parts, explicit row/column maps and palette/seam edits; no whole-character scaling or AI generation",
        "gates": ["Commit 2 must stop on KB2->KF1 visual FAIL", "KF2 requires fresh incoming KF1 PASS",
                  "KF1->KF2 and KF2->F0 require independent face/arm/suit review", "full K3->F0 chain required before F0_ART_APPROVED"],
        "runtimeIntegration": False, "F0ToIdleAudit": False,
    }


def write_spec() -> dict:
    dest = OUTPUT / "spec"
    if dest.exists():
        raise ValueError("refuse to overwrite specification evidence")
    report = specification()
    dest.mkdir(parents=True)
    (dest / "specification.json").write_text(json.dumps(report, indent=2)+"\n")
    return report


if __name__ == "__main__":
    print(write_spec()["status"])
