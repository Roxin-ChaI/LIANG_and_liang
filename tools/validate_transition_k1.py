"""Strict K1-only evidence gate. No art synthesis, fitting, resizing or approval by proxy."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image

from tools.prepare_transition_animation_candidate import metrics
from tools.specify_transition_keyframes import approved_inputs

ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "assets/rework/v0.1.0/transition-keyframes/k1-only/specification.json"


def constraints() -> dict:
    return {"id": "K1_ONLY_CONSTRAINTS_V2", "supersedes": "K1 only in gu-to-feng-spec/specification.json; K2/K3 untouched",
            "scope": "Idle canonical A; only beginning Charge / tiny straightening, still clearly Gu",
            "canvas": [192, 208], "headWidthRange": [65, 69], "headHeightRange": [77, 81],
            "maxHeadCenterDeltaX": 2, "maxHeadCenterDeltaY": 2, "baselineY": 203,
            "maxShoulderWidthDelta": 4, "maxBodyLeftDelta": 3, "maxBodyRightDelta": 3,
            "canonical": {"headBbox": [54, 4, 122, 84], "headCenter": [88, 44],
                          "shoulderPoints": [[75, 83], [108, 83]], "shoulderWidth": 33,
                          "bodyReferenceBbox": [69, 70, 122, 204]},
            "measurement": "head/shoulders independently pixel-reviewed anatomical annotations; body alpha band70:208 remains fixed, not whole-pose bbox; uncertain anatomy never PASS",
            "maxAnnotationUncertaintyPx": 1, "candidateAttemptsMaximum": 2,
            "processing": "NO sprite resize, warp, fit or interpolation; fixed canvas crop only; binary-alpha hardening may be recorded, never anatomical correction",
            "visualChecks": ["faceIdentity", "stillGu", "neckUnchanged", "noPrematureFeng", "poseContinuity", "noClipping"],
            "nextGate": "A_K1_PASS is NOT K1_APPROVED; only then inspect frozen K2 without changing it",
            "candidateGenerated": False, "appIntegrationAllowed": False, "fullAnimationAllowed": False,
            "runtimeEligible": False}


def numeric_checks(head: list[int], shoulder_width: float, body: list[int], baseline: int) -> dict:
    if len(head) != 4 or not all(type(v) is int for v in head) or not (0 <= head[0] < head[2] <= 192 and 0 <= head[1] < head[3] <= 208):
        raise ValueError("head bbox must be pixel-reviewed half-open integer coordinates")
    spec = constraints()
    center = [(head[0] + head[2]) / 2, (head[1] + head[3]) / 2]
    delta = [v - u for u, v in zip(spec["canonical"]["headCenter"], center)]
    width, height = head[2] - head[0], head[3] - head[1]
    left, right = body[0] - 69, body[2] - 122
    shoulder = shoulder_width - 33
    checks = {"headWidth": 65 <= width <= 69, "headHeight": 77 <= height <= 81,
              "headCenterX": abs(delta[0]) <= 2, "headCenterY": abs(delta[1]) <= 2,
              "baseline": baseline == 203, "shoulderWidth": abs(shoulder) <= 4,
              "bodyLeft": abs(left) <= 3, "bodyRight": abs(right) <= 3}
    return {"pass": all(checks.values()), "checks": checks, "headBbox": head,
            "headWidth": width, "headHeight": height, "headCenter": center, "headCenterDelta": delta,
            "shoulderWidth": shoulder_width, "shoulderWidthDelta": shoulder,
            "bodyReferenceBbox": body, "bodyLeftDelta": left, "bodyRightDelta": right,
            "baselineY": baseline, "baselineDelta": baseline - 203}


def assess(candidate: Image.Image, annotation: dict | None = None) -> dict:
    # Canonical hash verification precedes every candidate assessment.
    canonical = approved_inputs()[0][2]
    if candidate.mode != "RGBA" or candidate.size != (192, 208):
        raise ValueError("native192x208 RGBA required; no whole-character resizing to satisfy gate")
    info = metrics(candidate)
    structural = (info["baselineY"] == 203 and info["alphaValues"] == [0, 255]
                  and not info["hiddenRgbPixels"] and not info["touchesCellEdge"]
                  and not info["isolatedSinglePixels"])
    report = {"status": "AWAITING_INDEPENDENT_K1_REVIEW" if structural else "K1_QA_FAIL",
              "structuralPass": structural, "numeric": None, "visual": "NOT_VERIFIED",
              "runtimeEligible": False, "localChainAllowed": False, "resizeOperations": 0,
              "measured": info, "rgbaChangedPixelsFromA": sum(a != b for a, b in zip(canonical.get_flattened_data(), candidate.get_flattened_data()))}
    if annotation is None or info["bodyReferenceBbox"] is None or info["baselineY"] is None:
        return report
    head = annotation["headBbox"]
    points = annotation["shoulderPoints"]
    if len(points) != 2 or any(len(p) != 2 or not all(type(v) is int for v in p) or not (0 <= p[0] < 192 and 0 <= p[1] < 208) for p in points):
        raise ValueError("pixel-reviewed shoulder points required")
    numeric = numeric_checks(head, abs(points[1][0] - points[0][0]), info["bodyReferenceBbox"], info["baselineY"])
    report["numeric"] = numeric
    cap = candidate.getchannel("A").crop((0, 0, 192, 55)).getbbox()
    includes_cap = bool(cap and head[0] <= cap[0] and head[1] <= cap[1] and head[2] >= cap[2])
    report["headAnnotationContainsUpperHead"] = includes_cap
    visual = {key: annotation.get(key, "unknown") for key in constraints()["visualChecks"]}
    if any(v not in ("pass", "fail", "unknown") for v in visual.values()):
        raise ValueError("visual results must be pass/fail/unknown, not inferred from metrics")
    report["visual"] = visual
    uncertainty = annotation.get("uncertaintyPx")
    confirmed = (annotation.get("independentReviewer") and type(uncertainty) in (int, float)
                 and 0 <= uncertainty <= 1 and all(v == "pass" for v in visual.values()))
    report["annotationConfirmed"] = bool(confirmed)
    if not structural or not numeric["pass"] or not includes_cap or "fail" in visual.values():
        report["status"] = "K1_QA_FAIL"
    elif not confirmed:
        report["status"] = "K1_VISUAL_NOT_VERIFIED"
    else:
        report["status"] = "A_K1_PASS"
        report["localChainAllowed"] = True
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--annotation", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    with Image.open(args.candidate) as image:
        report = assess(image, json.loads(args.annotation.read_text()) if args.annotation else None)
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(report["status"])
