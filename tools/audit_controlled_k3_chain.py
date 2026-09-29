"""Read-only K2->controlled K3->frozen B; no automatic bridge frame synthesis."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image, ImageDraw

from tools.controlled_transition_k2 import cap_bbox
from tools.controlled_transition_k3 import B_SHA, OUTPUT, endpoint_b, source
from tools.derive_controlled_transition_k3 import CANDIDATE, resolve_review
from tools.locked_transition_k1 import sha
from tools.prepare_manual_transition_endpoints import pixel_overlay
from tools.prepare_transition_animation_candidate import digest, metrics

K3_SHA = "2b5651503d4d223d5c670152a1425ebafd6d55b5802f55794c6c70b3624876f6"


def frozen_inputs(review_path: Path | None = None) -> tuple[Image.Image, Image.Image, Image.Image]:
    k2 = source()
    if digest(CANDIDATE/"K3.png") != K3_SHA:
        raise ValueError("new K3 changed; stop, do not reshape it for B")
    with Image.open(CANDIDATE/"K3.png") as image:
        k3 = image.copy()
    review_file = review_path or CANDIDATE/"qa/independent-review.json"
    prerequisite = resolve_review(k3,json.loads(review_file.read_text()))
    if not prerequisite["localChainAllowed"]:
        raise ValueError("fresh K2_K3_STATIC_PASS required before B audit")
    return k2,k3,endpoint_b()[1]


def pair_metrics(k3: Image.Image, b: Image.Image) -> dict:
    a_info,b_info = metrics(k3),metrics(b)
    cap_a,cap_b = cap_bbox(k3),cap_bbox(b)
    return {
        "headSize": {"K3": [68,80], "BApprox": [49,54], "deltaApprox": [-19,-26]},
        "headCenter": {"K3": [88,44], "BApprox": [88.5,31], "deltaApprox": [0.5,-13]},
        "BAnatomicalGuideUncertaintyPx": 3,
        "headGuideWarning": "B is a historical manual guide with hand-occluded chin, not exact segmentation",
        "upperShoulderGuide": {"K3LockedWidth": 33, "BApproxWidth": 68, "deltaApprox": 35,
                               "warning": "K3y83 vs By65 annotations, not a same-band exact skeletal measurement"},
        "shoulderCapBand": {"K3Bbox": cap_a, "BBbox": cap_b, "widthDelta": (cap_b[2]-cap_b[0])-(cap_a[2]-cap_a[0]),
                            "warning": "same alpha band84:100; jacket/arm hull, not anatomical shoulder width"},
        "bodyBandBbox": {"K3": a_info["bodyReferenceBbox"], "B": b_info["bodyReferenceBbox"],
                         "delta": [v-u for u,v in zip(a_info["bodyReferenceBbox"],b_info["bodyReferenceBbox"])],
                         "widthDelta": (b_info["bodyReferenceBbox"][2]-b_info["bodyReferenceBbox"][0])-(a_info["bodyReferenceBbox"][2]-a_info["bodyReferenceBbox"][0])},
        "bodyBandCenterDelta": b_info["bodyBandCenterX"]-a_info["bodyBandCenterX"],
        "baselineDelta": b_info["baselineY"]-a_info["baselineY"],
        "numericEvidenceOnly": True, "visualVerdict": "AWAITING_INDEPENDENT_REVIEW",
    }


def resolve_chain(report: dict, review: dict) -> dict:
    fresh = (review.get("reviewedK3RgbaSha256") == report["K3RgbaSha256"]
             and review.get("reviewedBRgbaSha256") == report["BRgbaSha256"])
    incoming = report.get("K2_K3") == "K2_K3_STATIC_PASS" and review.get("K2_K3") == "PASS"
    valid = fresh and incoming and bool(review.get("reviewer"))
    if valid and review.get("K3_B") == "PASS" and review.get("verdict") == "K3_ART_APPROVED":
        status = "K3_ART_APPROVED"
    elif valid and review.get("K3_B") == "FAIL" and review.get("verdict") == "B_TRANSITION_BRIDGE_REQUIRED":
        status = "B_TRANSITION_BRIDGE_REQUIRED"
    else:
        status = "CHAIN_NOT_VERIFIED"
    return {"status": status, "K2_K3": report["K2_K3"],
            "K3_B": "STATIC_PASS" if status == "K3_ART_APPROVED" else "STATIC_FAIL" if status == "B_TRANSITION_BRIDGE_REQUIRED" else "NOT_VERIFIED",
            "K3ArtGate": "PASS_BOTH_STATIC_LINKS" if status == "K3_ART_APPROVED" else "FAIL_OUTGOING_LINK" if status == "B_TRANSITION_BRIDGE_REQUIRED" else "NOT_VERIFIED",
            "bridgeFramesRequired": True if status == "B_TRANSITION_BRIDGE_REQUIRED" else False if status == "K3_ART_APPROVED" else "NOT_VERIFIED",
            "bridgeFrameCount": "NOT_SPECIFIED_PENDING_ART_DESIGN", "bridgeFramesGenerated": 0,
            "K1K2K3BModifiedForOutgoingMatch": False, "userK3ArtApproval": "PENDING", "runtimeEligible": False,
            "scope": "paired static QA only; no App, full animation or user/release approval"}


def prepare(output: Path = OUTPUT/"chain-qa", review_path: Path | None = None) -> dict:
    if output.exists():
        raise ValueError("refuse to overwrite chain evidence")
    k2,k3,b = frozen_inputs(review_path)
    output.mkdir(parents=True)
    sheet = Image.new("RGBA",(576,240),(35,35,35,255))
    draw = ImageDraw.Draw(sheet)
    for i,(label,image) in enumerate(zip(("K2 APPROVED / FROZEN","K3 CONTROLLED / STATIC PASS","B APPROVED / FROZEN"),(k2,k3,b))):
        sheet.alpha_composite(image,(i*192,28))
        draw.text((i*192+3,3),label,fill="white")
        draw.line((i*192,231,i*192+191,231),fill=(255,185,45,255))
    sheet.save(output/"contact-sheet.png")
    sheet.resize((1728,720),Image.Resampling.NEAREST).save(output/"contact-sheet-nearest3x.png")
    for name,left,right in (("K2-K3",k2,k3),("K3-B",k3,b)):
        panel = Image.new("RGBA",(576,240),(35,35,35,255))
        pd = ImageDraw.Draw(panel)
        for i,(label,image) in enumerate(zip((name+" LEFT",name+" RIGHT","RGBA diff overlay"),(left,right,pixel_overlay(left,right)))):
            panel.alpha_composite(image,(i*192,28))
            pd.text((i*192+3,3),label,fill="white")
        panel.save(output/f"{name}-overlay-contact.png")
    report = {"status": "AWAITING_INDEPENDENT_CHAIN_REVIEW", "K2_K3": "K2_K3_STATIC_PASS",
              "K3_B": pair_metrics(k3,b), "K3Sha256": K3_SHA, "BSha256": B_SHA,
              "K3RgbaSha256": sha(k3.tobytes()), "BRgbaSha256": sha(b.tobytes()),
              "newPosesGenerated": 0, "BModified": False, "K3ModifiedForB": False,
              "userK3ArtApproval": "PENDING", "runtimeEligible": False}
    (output/"landmark-report.json").write_text(json.dumps(report,indent=2)+"\n")
    return report


def finalize(output: Path, review_path: Path) -> dict:
    report = json.loads((output/"landmark-report.json").read_text())
    # Re-read actual frozen pixels and fresh incoming review before recording a verdict.
    _,k3,b = frozen_inputs()
    if (report["K3RgbaSha256"] != sha(k3.tobytes()) or report["BRgbaSha256"] != sha(b.tobytes())
            or report["K3Sha256"] != K3_SHA or report["BSha256"] != B_SHA):
        raise ValueError("stale chain evidence does not match current frozen inputs")
    final = resolve_chain(report,json.loads(review_path.read_text()))
    (output/"final-verdict.json").write_text(json.dumps(final,indent=2)+"\n")
    return final


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output",type=Path,default=OUTPUT/"chain-qa")
    parser.add_argument("--review",type=Path)
    args = parser.parse_args()
    print((finalize(args.output,args.review) if args.review else prepare(args.output))["status"])
