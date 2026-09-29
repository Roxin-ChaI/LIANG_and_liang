"""Refuse non-native F0 candidates; never normalize failed source art into approval."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image

from tools.f0_transition_endpoint_spec import OUT, specification
from tools.prepare_transition_animation_candidate import digest

CANDIDATE = OUT / "rejected-candidate/f0-local-edit-attempt-01-REJECTED.png"
QA = OUT / "rejected-candidate/qa"


def audit(path: Path = CANDIDATE) -> dict:
    specification()  # Recheck all frozen inputs before discussing a candidate.
    with Image.open(path) as source:
        mode, size = source.mode, list(source.size)
        image = source.copy()
    checks = {"native192x208": size == [192, 208], "rgba": mode == "RGBA"}
    if mode == "RGBA":
        alpha = image.getchannel("A")
        values = sorted(set(alpha.get_flattened_data()))
        checks["binaryAlpha"] = values == [0, 255]
    else:
        values = []
        checks["binaryAlpha"] = False
    try:
        recorded_path = str(path.relative_to(OUT))
    except ValueError:
        recorded_path = str(path)
    return {
        "status": "F0_CANDIDATE_REJECTED" if not all(checks.values()) else "MANUAL_VISUAL_QA_REQUIRED",
        "checks": checks,
        "candidatePath": recorded_path,
        "candidateSha256": digest(path),
        "candidateMode": mode,
        "candidateCanvas": size,
        "alphaValues": values,
        "approvedF0": False,
        "F0Written": False,
        "nearestNeighborDownsampleAllowedAsRepair": False,
        "reason": "Non-native full-body rendering cannot demonstrate a controlled pixel edit of KB2; shrinking it to 192x208 would resample the entire character rather than preserve source pixels.",
        "nextAction": "Do not integrate or accept this candidate. A 192x208 controlled local pixel derivation, with at most one independently gated morphology bridge if necessary, still requires actual art and visual QA.",
    }


def prepare(path: Path = CANDIDATE, output: Path = QA) -> dict:
    if output.exists():
        raise ValueError("refuse to overwrite F0 rejection evidence")
    data = audit(path)
    output.mkdir(parents=True)
    (output / "candidate-audit.json").write_text(json.dumps(data, indent=2) + "\n")
    return data


def resolve(report: dict, review: dict) -> dict:
    fresh = review.get("reviewedCandidateSha256") == report["candidateSha256"]
    accepted = (all(report["checks"].values()) and fresh and bool(review.get("reviewer"))
                and review.get("verdict") == "VISUAL_PASS")
    return {"status": "F0_CANDIDATE_VISUAL_PASS_NOT_YET_APPROVED" if accepted else "F0_CANDIDATE_REJECTED",
            "technicalPass": all(report["checks"].values()), "independentReviewFresh": fresh,
            "eligibleForF0Promotion": accepted, "F0Written": False,
            "appIntegrationAllowed": False}


def finalize(path: Path = CANDIDATE, output: Path = QA) -> dict:
    actual = audit(path)
    saved = json.loads((output / "candidate-audit.json").read_text())
    if saved != actual:
        raise ValueError("stale or altered F0 candidate audit")
    review = json.loads((output / "independent-review.json").read_text())
    result = resolve(actual, review)
    (output / "final-verdict.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", type=Path, default=CANDIDATE)
    parser.add_argument("--output", type=Path, default=QA)
    parser.add_argument("--review", action="store_true")
    args = parser.parse_args()
    print((finalize(args.candidate, args.output) if args.review else prepare(args.candidate, args.output))["status"])
