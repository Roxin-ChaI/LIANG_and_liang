"""Frozen K3->B bridge contract. Numeric gates never imply visual approval."""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

from PIL import Image

from tools.controlled_transition_k3 import endpoint_b
from tools.locked_transition_k1 import sha
from tools.prepare_transition_animation_candidate import digest, metrics

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "assets/rework/v0.1.0/transition-keyframes/k3-b-bridge"
FROZEN = {
    "A": ("assets/rework/v0.1.0/manual-transition-endpoints/A-gu-to-feng-entry.png", "6c925bbcd1386cad107cdffb5aa7569d9ace295790cb9542d7dd0629f074cab3"),
    "K1": ("assets/rework/v0.1.0/transition-keyframes/k1-locked/candidate/K1.png", "3fe2510fce45d2e7fb63e2018f79fe69ef9f05c470634903fa580700acc9e246"),
    "K2": ("assets/rework/v0.1.0/transition-keyframes/k2-controlled/candidate-locked-hands/K2.png", "565122ea1364eebd56a0d6d3b53934bef8d45d53cb1787eedf4ee1f812cdfcec"),
    "K3": ("assets/rework/v0.1.0/transition-keyframes/k3-controlled/candidate/K3.png", "2b5651503d4d223d5c670152a1425ebafd6d55b5802f55794c6c70b3624876f6"),
    "B": ("assets/rework/v0.1.0/manual-transition-endpoints/B-gu-to-feng-exit.png", "4ae8848d3a40e6c3d8507b7fda119d58462f3236b3202471239ee0b9c0ac506b"),
}
# Historical guides include the neck/upper collar in K3 and a hand-occluded chin
# in B. They must not be advertised as exact anatomical segmentation.
K3_HEAD = [54, 4, 122, 84]
B_HEAD = [64, 4, 113, 58]
LIMITS = {"headSize": 6, "headCenterX": 3, "headCenterY": 4, "bodyWidth": 15}


def frozen_images() -> dict[str, Image.Image]:
    result = {}
    for name, (relative, expected) in FROZEN.items():
        path = ROOT / relative
        if digest(path) != expected:
            raise ValueError(f"frozen {name} changed; do not adapt bridge to it")
        with Image.open(path) as image:
            if image.mode != "RGBA" or image.size != (192, 208):
                raise ValueError("native 192x208 RGBA required")
            result[name] = image.copy()
    # Also retain the original endpoint approval gate.
    endpoint_b()
    return result


def landmark(image: Image.Image, head: list[int], *, approximate: bool = False) -> dict:
    if image.mode != "RGBA" or image.size != (192, 208):
        raise ValueError("native 192x208 RGBA required")
    if len(head) != 4 or not (0 <= head[0] < head[2] <= 192 and 0 <= head[1] < head[3] <= 208):
        raise ValueError("valid head guide required")
    info = metrics(image)
    body = info["bodyReferenceBbox"]
    return {"headBbox": head, "headSize": [head[2]-head[0], head[3]-head[1]],
            "headCenter": [(head[0]+head[2])/2, (head[1]+head[3])/2],
            "headGuideApproximate": approximate, "headGuideUncertaintyPx": 3 if approximate else 0,
            "bodyBbox": body, "bodyWidth": body[2]-body[0],
            "bodyBandCenterX": info["bodyBandCenterX"], "baselineY": info["baselineY"],
            "registrationX": 96, "rgbaSha256": sha(image.tobytes())}


def step_gate(left: dict, right: dict) -> dict:
    size = [b-a for a,b in zip(left["headSize"], right["headSize"])]
    center = [b-a for a,b in zip(left["headCenter"], right["headCenter"])]
    width = right["bodyWidth"]-left["bodyWidth"]
    checks = {"headSizeAtMost6": all(abs(v) <= LIMITS["headSize"] for v in size),
              "headCenterXAtMost3": abs(center[0]) <= LIMITS["headCenterX"],
              "headCenterYAtMost4": abs(center[1]) <= LIMITS["headCenterY"],
              "bodyGrowth0to15": 0 <= width <= LIMITS["bodyWidth"],
              "baseline203": left["baselineY"] == right["baselineY"] == 203,
              "registration96": left["registrationX"] == right["registrationX"] == 96}
    return {"numericPass": all(checks.values()), "checks": checks, "headSizeDelta": size,
            "headCenterDelta": center, "bodyWidthDelta": width,
            "bodyBboxDelta": [b-a for a,b in zip(left["bodyBbox"], right["bodyBbox"])],
            "bodyBandCenterDelta": right["bodyBandCenterX"]-left["bodyBandCenterX"],
            "baselineDelta": right["baselineY"]-left["baselineY"],
            "headEndpointUncertaintyPx": max(left["headGuideUncertaintyPx"], right["headGuideUncertaintyPx"]),
            "faceIdentity": "MANUAL_VISUAL_QA", "armPose": "MANUAL_VISUAL_QA", "staticVerdict": "NOT_VERIFIED"}


def capacity(left: dict, right: dict, bridges: int) -> dict:
    if type(bridges) is not int or bridges < 0:
        raise ValueError("non-negative integer bridge count required")
    pair = step_gate(left, right)
    segments = bridges+1
    requirements = {
        "headWidth": math.ceil(abs(pair["headSizeDelta"][0])/LIMITS["headSize"]),
        "headHeight": math.ceil(abs(pair["headSizeDelta"][1])/LIMITS["headSize"]),
        "headCenterX": math.ceil(abs(pair["headCenterDelta"][0])/LIMITS["headCenterX"]),
        "headCenterY": math.ceil(abs(pair["headCenterDelta"][1])/LIMITS["headCenterY"]),
        "bodyWidth": math.ceil(abs(pair["bodyWidthDelta"])/LIMITS["bodyWidth"]),
    }
    return {"bridges": bridges, "segments": segments, "requiredSegmentsByNominalGuide": requirements,
            "nominalMinimumBridges": max(requirements.values())-1,
            "numericCapacitySufficient": all(v <= segments for v in requirements.values()),
            "meaning": "lower bound from nominal guides only, not a promise of face/arm/pose continuity",
            "headGuideUncertaintyPx": pair["headEndpointUncertaintyPx"]}


def specification() -> dict:
    images = frozen_images()
    k3 = landmark(images["K3"], K3_HEAD)
    b = landmark(images["B"], B_HEAD, approximate=True)
    return {"id": "K3_B_BRIDGE_CONTRACT_V1", "status": "SPECIFICATION_ONLY", "generatedPoses": 0,
            "frozenFiles": {name: {"path": path, "sha256": digest(ROOT/path)} for name,(path,_) in FROZEN.items()},
            "approvalProvenance": "current user explicitly approves K1/K2/K3 and A->K1->K2->K3; historical QA is not rewritten",
            "canvas": [192,208], "registrationX": 96, "baselineY": 203,
            "limits": LIMITS, "K3": k3, "B": b,
            "guideWarning": "K3 reference includes lower neck/collar; B chin hand-occluded, manual +/-3px; not exact skull segmentation",
            "capacity": [capacity(k3,b,1), capacity(k3,b,2)],
            "twoBridgeFeasibility": "INSUFFICIENT_NOMINAL_HEAD_HEIGHT_AND_CENTER_BUDGET",
            "authorizedNewPoses": ["KB1", "KB2 only after KB2_REQUIRED"],
            "KB1": "from K3: local head decrease up to6px/axis, center up to4px up; body grows up to15px; begin arm pose; still not full Feng",
            "KB2": "from fresh static-pass KB1 only; same budgets; final KB2->B evaluated independently, never waived",
            "localHeadMethod": "nearest-neighbor anatomical-part raster only, retaining original face/hair/glasses palette; no whole-person scaling",
            "bodyMethod": "documented native integer cloth/limb copies, limited donor repairs; visual seam/identity gate mandatory",
            "effects": "none; never hide differences", "globalScalingAllowed": False,
            "faceIdentityGate": "independent visual PASS and eventual human art approval; numeric bbox is insufficient",
            "failurePolicy": "incoming KB1 FAIL stops; insufficient outgoing KB1->B gives KB2_REQUIRED; KB2->B FAIL blocks completion and asks for more art scope, not KB3 synthesis",
            "appIntegrationAllowed": False, "fullAnimationAllowed": False, "runtimeEligible": False}


def prepare_spec(output: Path = OUTPUT/"spec") -> dict:
    if output.exists():
        raise ValueError("refuse to overwrite specification")
    report = specification()
    output.mkdir(parents=True)
    (output/"specification.json").write_text(json.dumps(report,indent=2)+"\n")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUTPUT/"spec")
    args = parser.parse_args()
    print(prepare_spec(args.output)["status"])
