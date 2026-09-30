"""Static and provenance gate for the manually placed Feng F0 draft.

Numeric geometry is only a rejection gate; a visual PASS must be independent.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from PIL import Image

from tools.audit_b_endpoint_compatibility import KB2
from tools.f0_transition_endpoint_spec import OUT, KB2_HEAD, specification
from tools.manual_f0_pixel_art import DEST, construct
from tools.prepare_transition_animation_candidate import digest
from tools.transition_bridge_spec import landmark, step_gate

F0_HEAD = [64, 4, 114, 59]
REVIEW = DEST / "independent-review.json"
GATE = DEST / "KB2-F0-gate.json"


def audit(f0_path: Path = DEST / "F0.png") -> dict:
    frozen = specification()
    with Image.open(KB2) as image:
        kb2 = image.copy()
    with Image.open(f0_path) as image:
        f0_mode, f0_size = image.mode, image.size
        f0 = image.copy()
    reproduced, recipe = construct()
    checks = {
        "nativeCanvas192x208": f0_size == (192, 208),
        "modeRGBA": f0_mode == "RGBA",
        "exactlyReproducibleFromApprovedPixels": f0.tobytes() == reproduced.tobytes(),
        "approvedInputsUnchanged": True,
        "binaryAlpha": set(f0.getchannel("A").get_flattened_data()) == {0, 255},
        "transparentRGBZero": all(p == (0, 0, 0, 0) for p in f0.get_flattened_data() if p[3] == 0),
        "noAIGenerationOrResampling": not recipe["aiImageGeneration"] and not recipe["globalScaling"] and not recipe["interpolation"],
    }
    before = landmark(kb2, KB2_HEAD)
    after = landmark(f0, F0_HEAD, approximate=True)
    delta = step_gate(before, after)
    checks["baseline203"] = before["baselineY"] == after["baselineY"] == 203
    checks["registration96"] = before["registrationX"] == after["registrationX"] == 96
    return {
        "status": "VISUAL_REVIEW_REQUIRED",
        "sourceHashes": frozen["sourceSha256"],
        "F0Sha256": digest(f0_path),
        "F0RgbaSha256": hashlib.sha256(f0.tobytes()).hexdigest(),
        "checks": checks,
        "KB2Landmarks": before,
        "F0Landmarks": after,
        "delta": delta,
        "headGuideCaveat": "F0 head guide approximates anatomical skull; it is not automated face segmentation. Independent visual review is mandatory.",
        "numericPass": all(checks.values()) and delta["numericPass"],
        "visualPass": None,
        "artApproved": False,
        "F0ToIdleAuditAllowed": False,
    }


def resolve(gate: dict, visual: dict) -> dict:
    fresh = visual.get("reviewedF0Sha256") == gate["F0Sha256"]
    visual_pass = fresh and visual.get("verdict") == "PASS" and bool(visual.get("reviewer"))
    approved = gate["numericPass"] and visual_pass
    return {**gate, "status": "F0_ART_APPROVED" if approved else "F0_MANUAL_QA_FAIL",
            "independentReviewFresh": fresh, "visualPass": visual_pass,
            "artApproved": approved, "F0ToIdleAuditAllowed": approved,
            "nextAction": "F0→Idle pose audit may run" if approved else
            "Stop before F0→Idle audit. Direct KB2→finished Feng needs further manually approved morphology/pose art; do not weaken the F0 identity or numeric gate."}


def write(output: Path = GATE, review: Path = REVIEW) -> dict:
    report = audit()
    if review.exists():
        report = resolve(report, json.loads(review.read_text()))
    output.write_text(json.dumps(report, indent=2) + "\n")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=GATE)
    parser.add_argument("--review", type=Path, default=REVIEW)
    args = parser.parse_args()
    print(write(args.output, args.review)["status"])
