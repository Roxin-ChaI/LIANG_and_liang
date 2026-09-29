"""Read-only KB1->B gate; incoming static PASS cannot waive endpoint budgets."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image

from tools.derive_transition_bridge import PLAN, contact, resolve_review
from tools.locked_transition_k1 import sha
from tools.prepare_manual_transition_endpoints import pixel_overlay
from tools.prepare_transition_animation_candidate import digest
from tools.transition_bridge_spec import B_HEAD, K3_HEAD, OUTPUT, frozen_images, landmark, step_gate

KB1_SHA = "4d1b307e3e251352d3cc165c95f85009d445f797efd94bfeb28fe682a30cd837"


def kb1_inputs(review_file: Path | None = None) -> tuple[dict,Image.Image,dict]:
    frozen = frozen_images()
    path = OUTPUT/"kb1/KB1.png"
    if digest(path) != KB1_SHA:
        raise ValueError("KB1 candidate changed since independent review")
    with Image.open(path) as image:
        kb1 = image.copy()
    plan = json.loads(PLAN.read_text())
    review_path = review_file or OUTPUT/"kb1/qa/independent-review.json"
    fresh = resolve_review(frozen["K3"],kb1,plan,json.loads(review_path.read_text()))
    if not fresh["localChainAllowed"]:
        raise ValueError("fresh K3_KB1_STATIC_PASS required before endpoint gate")
    return frozen,kb1,plan


def measure(frozen: dict, kb1: Image.Image, plan: dict) -> dict:
    left = landmark(kb1,plan["headTargetBbox"])
    right = landmark(frozen["B"],B_HEAD,approximate=True)
    return {"status":"AWAITING_INDEPENDENT_ENDPOINT_REVIEW", "incoming":"K3_KB1_STATIC_PASS",
            "KB1":left,"B":right,"pair":step_gate(left,right), "newPosesGenerated":0,
            "remainingArmPose":"KB1 only1px inward/up forearm onset; B bends screen-left hand to chin and spreads stance; manual visual comparison required",
            "BModified":False,"KB1ModifiedForB":False,"runtimeEligible":False,"fullAnimationAllowed":False}


def resolve(report: dict, review: dict) -> dict:
    fresh = (review.get("kb1RgbaSha256") == report["KB1"]["rgbaSha256"] and
             review.get("bRgbaSha256") == report["B"]["rgbaSha256"])
    valid = fresh and bool(review.get("reviewer")) and report["incoming"] == "K3_KB1_STATIC_PASS"
    outgoing_pass = (valid and report["pair"]["numericPass"] and review.get("KB1_B") == "PASS"
                     and review.get("faceIdentity") == review.get("armPoseContinuity") == "PASS")
    outgoing_fail = valid and review.get("KB1_B") == "FAIL"
    status = "BRIDGE_COMPLETE" if outgoing_pass else "KB2_REQUIRED" if outgoing_fail else "ENDPOINT_NOT_VERIFIED"
    return {"status":status,"incoming":report["incoming"],"outgoing":"STATIC_PASS" if outgoing_pass else "STATIC_FAIL" if outgoing_fail else "NOT_VERIFIED",
            "numericPass":report["pair"]["numericPass"],"independentReviewFresh":fresh,
            "KB2Allowed":outgoing_fail,"B_BRIDGE_ART_APPROVED":False,"userArtApproval":"PENDING",
            "fullAnimationAllowed":False,"runtimeEligible":False,"approvedFilesModified":False}


def prepare(output: Path = OUTPUT/"kb1-b-gate", review_file: Path | None = None) -> dict:
    if output.exists():
        raise ValueError("refuse to overwrite endpoint gate")
    frozen,kb1,plan = kb1_inputs(review_file)
    report = measure(frozen,kb1,plan)
    output.mkdir(parents=True)
    contact(output/"contact-sheet.png",["KB1 STATIC PASS","B FROZEN","RGBA diff"],
            [kb1,frozen["B"],pixel_overlay(kb1,frozen["B"])])
    names = ["A","K1","K2","K3","KB1","B"]
    contact(output/"full-chain-contact-sheet.png",names,[*(frozen[name] for name in names[:4]),kb1,frozen["B"]])
    (output/"landmark-report.json").write_text(json.dumps(report,indent=2)+"\n")
    return report


def finalize(output: Path, review_file: Path) -> dict:
    frozen,kb1,plan = kb1_inputs()
    actual = measure(frozen,kb1,plan)
    saved = json.loads((output/"landmark-report.json").read_text())
    if saved != actual:
        raise ValueError("stale or altered endpoint report")
    result = resolve(actual,json.loads(review_file.read_text()))
    (output/"final-verdict.json").write_text(json.dumps(result,indent=2)+"\n")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output",type=Path,default=OUTPUT/"kb1-b-gate")
    parser.add_argument("--review",type=Path)
    args = parser.parse_args()
    print((finalize(args.output,args.review) if args.review else prepare(args.output))["status"])
