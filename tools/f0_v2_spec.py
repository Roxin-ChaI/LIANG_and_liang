"""Separate the completed Feng morphology from its subsequent Idle entrance."""
from __future__ import annotations

import json
from pathlib import Path

from PIL import Image

from tools.f0_morph_bridge import HEAD_GUIDES, OUTPUT as BRIDGE, sources as retained_sources
from tools.prepare_transition_animation_candidate import digest
from tools.review_f0_morph_chain import KF1_SHA, KF2_SHA, KB1_SHA
from tools.transition_bridge_spec import ROOT, frozen_images, landmark

OUTPUT = ROOT / "assets/rework/v0.1.0/transition-keyframes/feng-f0/v2"
SOURCE = BRIDGE / "kf2/KF2.png"
HEAD = [63, 4, 113, 59]
FACE_SOURCE = [67, 28, 110, 56]
FACE_TARGET = [67, 26, 110, 54]
HAND_LOCKS = [[60, 130, 79, 155], [112, 130, 135, 155]]
FEET_LOCK = [0, 192, 192, 208]


def sources() -> dict[str, Image.Image]:
    frozen = frozen_images()
    retained_sources()  # Validate KB2, retired F0 and the official Feng atlas.
    protected = {
        BRIDGE.parent.parent / "k3-b-bridge/kb1/KB1.png": KB1_SHA,
        BRIDGE / "kf1/KF1.png": KF1_SHA,
        SOURCE: KF2_SHA,
    }
    for path, expected in protected.items():
        if digest(path) != expected:
            raise ValueError(f"approved input changed: {path.name}")
    with Image.open(SOURCE) as image:
        if image.mode != "RGBA" or image.size != (192, 208):
            raise ValueError("native KF2 required")
        kf2 = image.copy()
    return {"KF2": kf2, "B": frozen["B"]}


def spec() -> dict:
    images = sources()
    return {
        "status": "SPECIFICATION_ONLY", "generatedCandidates": 0,
        "source": str(SOURCE.relative_to(ROOT)), "sourceSha256": KF2_SHA,
        "retiredF0": "preserved as historical evidence, rejected as final candidate",
        "canvas": [192, 208], "baselineY": 203, "registrationX": 96,
        "sourceLandmark": landmark(images["KF2"], HEAD_GUIDES["KF2"], approximate=True),
        "targetHeadGuide": HEAD,
        "morph": {
            "meaning": "completed Feng body, neutral finishing pose; relaxed source expression intentionally retained",
            "mustComplete": ["Feng head-size range", "broad shoulders and strong torso", "basic blue tailored suit silhouette"],
            "headWidthRange": [49, 52], "headHeightRange": [54, 57],
            "maxHeadSizeDelta": 6, "maxHeadCenterDelta": [3, 4],
            "bodyBandWidthRange": [96, 104], "maxBodyWidthDelta": 10,
            "maxTrouserOuterEdgeMove": 3,
            "facePixelLock": {"source": FACE_SOURCE, "target": FACE_TARGET,
                              "rule": "exact RGBA crop, integer 2px upward placement only; no expression edits"},
            "handsPixelLocks": HAND_LOCKS, "feetPixelLock": FEET_LOCK,
            "locksIncludeTransparentPixels": True,
            "deferred": ["sharp Feng facial performance", "hand to chin", "wide stance", "deep trouser folds", "final Idle garment detailing"],
            "visualChecks": ["same character", "head continuity", "completed Feng torso and shoulders", "arm continuity", "pants continuity", "jacket continuity"],
        },
        "entry": {
            "onlyAfter": "F0_MORPH_ENDPOINT_APPROVED",
            "allowed": ["relaxed to sharp expression", "raise arm", "fist adjustment", "widen stance", "finish suit detailing"],
            "forbidden": ["large skull rescaling", "another body-form change", "identity replacement"],
            "ifDirectConnectionFails": "FENG_ENTRY_ANIMATION_REQUIRED; plan 2-4 separate poses, no generation this phase",
            "notPartOfMorphFrameBudget": True,
        },
        "method": "hand-selected native pixel copies, documented part maps and explicit pixel/seam edits",
        "aiGeneration": False, "globalScaling": False, "interpolation": False,
        "newBridgeFramesAllowed": False, "approvedInputsEditable": False,
        "geometryAloneApprovesArt": False, "runtimeIntegrationAllowed": False,
        "humanApproval": "PENDING",
    }


def write(output: Path = OUTPUT / "spec") -> dict:
    report = spec()
    output.mkdir(parents=True, exist_ok=False)
    (output / "specification.json").write_text(json.dumps(report, indent=2)+"\n")
    return report


if __name__ == "__main__":
    print(write()["status"])
