"""Specification-only gate for a distinct neutral Feng transition endpoint."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image

from tools.audit_b_endpoint_compatibility import FENG_ATLAS, FENG_ATLAS_SHA, KB2, KB2_SHA
from tools.prepare_transition_animation_candidate import digest
from tools.transition_bridge_spec import B_HEAD, ROOT, frozen_images, landmark

OUT = ROOT / "assets/rework/v0.1.0/transition-keyframes/feng-f0"
KB2_HEAD = [60, 4, 116, 72]
F0_TARGET = {
    "headWidthPx": [49, 52],
    "headHeightPx": [54, 57],
    "headCenterX": [86, 91],
    "headCenterY": [29, 34],
    "bodyBandWidthPx": [99, 104],
    "baselineY": 203,
    "registrationX": 96,
}


def specification() -> dict:
    frozen = frozen_images()
    if digest(KB2) != KB2_SHA or digest(FENG_ATLAS) != FENG_ATLAS_SHA:
        raise ValueError("approved KB2 or formal Feng atlas changed")
    with Image.open(KB2) as image:
        if image.mode != "RGBA" or image.size != (192, 208):
            raise ValueError("KB2 must remain native 192x208 RGBA")
        kb2 = image.copy()
    kb2_mark = landmark(kb2, KB2_HEAD)
    b_mark = landmark(frozen["B"], B_HEAD, approximate=True)
    return {
        "id": "F0_TRANSITION_ENDPOINT_SPEC_V1",
        "status": "SPECIFICATION_ONLY",
        "generatedImages": 0,
        "sourceSha256": {"KB2": digest(KB2), "B": digest(ROOT / "assets/rework/v0.1.0/manual-transition-endpoints/B-gu-to-feng-exit.png"),
                         "formalFengAtlas": digest(FENG_ATLAS)},
        "canvas": [192, 208],
        "baselineY": 203,
        "registrationX": 96,
        "KB2": kb2_mark,
        "B": b_mark,
        "F0TargetGuide": F0_TARGET,
        "identity": "fully Feng: canonical Feng hair, face, glasses, broad shoulders, muscular torso, and tailored blue suit; no Gu body proportions",
        "pose": "front-facing upright neutral finish; hands low or finishing a modest charge, not fingertip-to-chin; legs only gradually widen from KB2",
        "separateChannels": {"KB2_to_F0": "complete form/identity morph; hand and stance trajectories remain locally continuous",
                             "F0_to_FengIdle": "finish only pose: arm rises, fist sets and feet widen; no significant skull or shoulder change"},
        "oneDirectStepFromKB2CanMeetOldHeadGuideBudget": False,
        "reason": "nominal KB2 56x68 to nearest Feng-like F0 52x57 still reduces guide height by 11px, exceeding the previous 6px/link budget",
        "optionalMorphBridge": "one extra shape bridge may split the height/center change; each resulting link must pass identity, arm, stance and garment visual QA",
        "F0_to_BPolicy": "if the arm-to-chin, fist or wide-stance pose still snaps, require a separate Feng entry animation; never add unlimited morph bridges",
        "notAutomatedArtApproval": True,
        "approvedAssetsMayBeEdited": False,
        "appIntegrationAllowed": False,
        "fullAnimationAllowed": False,
        "tagAllowed": False,
    }


def prepare(output: Path = OUT / "spec") -> dict:
    if output.exists():
        raise ValueError("refuse to overwrite F0 specification")
    report = specification()
    output.mkdir(parents=True)
    (output / "specification.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUT / "spec")
    args = parser.parse_args()
    print(prepare(args.output)["status"])
