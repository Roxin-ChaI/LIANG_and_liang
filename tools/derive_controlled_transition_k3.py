"""Emit only one controlled K3; locked K2 identity and independent static gate."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image, ImageDraw

from tools.controlled_transition_k3 import K2_SHA, OUTPUT, assess, masks, source
from tools.locked_transition_k1 import sha
from tools.prepare_manual_transition_endpoints import pixel_overlay
from tools.prepare_transition_animation_candidate import digest

PLAN = OUTPUT/"pixel-edit-plan.json"
CANDIDATE = OUTPUT/"candidate"
STATIC_CHECKS = ("identity", "headNeckUnchanged", "shoulderGrowthGradual", "bodyPoseProgressive",
                 "clothSeamsPlausible", "handsLegsFeetStable", "K2K3Continuity", "noPixelArtifacts")


def apply_plan(k2: Image.Image, plan: dict) -> Image.Image:
    if k2.mode != "RGBA" or k2.size != (192,208) or k2.tobytes() != source().tobytes():
        raise ValueError("exact approved native K2 required; no scaling or substitute")
    if plan.get("sourceSha256") != K2_SHA or plan.get("id") != "K3_LOCAL_JACKET_PROGRESSION_V1":
        raise ValueError("pinned approved K2 and controlled plan required")
    if plan.get("leftSourceColumns") != [65,84] or plan.get("rightSourceColumns") != [103,124]:
        raise ValueError("local panels only, not whole-side scaling")
    if any(plan.get(key) is not False for key in ("headNeckEdited", "handsLegsFeetEdited", "effects", "globalScalingOrTranslation", "interpolation", "aiGeneration")):
        raise ValueError("no head edits, global fit, effects, interpolation or generation")
    locked, _ = masks()
    k3 = k2.copy()
    src, dst = k2.load(), k3.load()
    expected_y, previous_delta = 84, 0
    for band in plan["rowBands"]:
        y0, y1 = band["y"]
        delta = band["outwardPixels"]
        if type(delta) is not int or not 1 <= delta <= 5 or abs(delta-previous_delta) > 1:
            raise ValueError("movement at most5px and profile increments at most1px")
        if type(y0) is not int or type(y1) is not int or y0 != expected_y or not 84 <= y0 < y1 <= 140:
            raise ValueError("ordered continuous upper-body rows84:140 required")
        for y in range(y0,y1):
            for x in (*range(65-delta,84), *range(103,124+delta)):
                if locked.getpixel((x,y)):
                    raise ValueError("MANUAL_PIXEL_ART_REQUIRED: plan touches a locked region")
            for x in range(65,84):
                dst[x-delta,y] = src[x,y]
            for x in range(84-delta,84):
                dst[x,y] = src[83,y]
            for x in range(103,124):
                dst[x+delta,y] = src[x,y]
            for x in range(103,103+delta):
                dst[x,y] = src[103,y]
        expected_y, previous_delta = y1, delta
    if expected_y != 140 or previous_delta != 1:
        raise ValueError("complete tapered profile required, no partial shortcut")
    return k3


def resolve_review(candidate: Image.Image, review: dict) -> dict:
    report = assess(candidate)
    fresh = review.get("reviewedRgbaSha256") == sha(candidate.tobytes())
    visual_pass = (bool(review.get("reviewer")) and review.get("verdict") == "K2_K3_STATIC_PASS"
                   and all((value.get("status") if isinstance(value,dict) else value) == "PASS"
                           for key in STATIC_CHECKS for value in (review.get("checks",{}).get(key),)))
    if not report["technicalPass"]:
        status = "K3_QA_FAIL"
    elif fresh and visual_pass:
        status = "K2_K3_STATIC_PASS"
    elif fresh and review.get("verdict") in ("K3_QA_FAIL", "MANUAL_PIXEL_ART_REQUIRED"):
        status = review["verdict"]
    else:
        status = "K3_STATIC_NOT_VERIFIED"
    return {**report, "status": status, "independentReviewFresh": fresh,
            "localChainAllowed": status == "K2_K3_STATIC_PASS", "userK3ArtApproval": "PENDING", "runtimeEligible": False}


def prepare(output: Path = CANDIDATE) -> dict:
    if output.exists():
        raise ValueError("refuse to overwrite K3 candidate")
    plan = json.loads(PLAN.read_text())
    k2 = source()
    k3 = apply_plan(k2, plan)
    report = assess(k3)
    if not report["technicalPass"]:
        raise ValueError("K3_QA_FAIL before emitting candidate: "+str(report["checks"]))
    qa = output/"qa"
    qa.mkdir(parents=True)
    path = output/"K3.png"
    k3.save(path)
    difference = Image.new("L", (192,208))
    difference.putdata([255 if a != b else 0 for a,b in zip(k2.get_flattened_data(),k3.get_flattened_data())])
    difference.save(qa/"difference-mask.png")
    overlay = pixel_overlay(k2,k3)
    overlay.save(qa/"overlay.png")
    guide = k3.copy()
    gd = ImageDraw.Draw(guide)
    gd.rectangle((54,4,121,83), outline=(255,185,45,255))
    body = report["bodyBbox"]
    gd.rectangle((body[0],70,body[2]-1,203),outline=(130,230,190,255))
    gd.line((96,0,96,207),fill=(255,80,100,255))
    gd.line((0,203,191,203),fill=(255,185,45,255))
    guide.save(qa/"landmark-guide.png")
    sheet = Image.new("RGBA", (768,240), (35,35,35,255))
    draw = ImageDraw.Draw(sheet)
    for i,(label,image) in enumerate(zip(("K2 APPROVED / FROZEN", "K3 LOCAL CANDIDATE", "RGBA diff overlay", "guide ONLY / NOT art"), (k2,k3,overlay,guide))):
        sheet.alpha_composite(image,(i*192,28))
        draw.text((i*192+3,3),label,fill="white")
    sheet.save(qa/"contact-sheet.png")
    sheet.resize((2304,720),Image.Resampling.NEAREST).save(qa/"contact-sheet-nearest3x.png")
    report.update({"sourceSha256": K2_SHA, "candidatePngSha256": digest(path), "candidateRgbaSha256": sha(k3.tobytes()),
                   "pixelEditPlanSha256": digest(PLAN), "method": plan["method"], "newPoses": ["K3"],
                   "aiUsed": False, "globalScaling": False, "retryCount": 0, "BModified": False})
    (qa/"landmark-report.json").write_text(json.dumps(report,indent=2)+"\n")
    (qa/"locked-region-byte-comparison.json").write_text(json.dumps(report["lockedByteComparison"],indent=2)+"\n")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output",type=Path,default=CANDIDATE)
    parser.add_argument("--review",type=Path)
    args = parser.parse_args()
    if args.review:
        with Image.open(args.output/"K3.png") as image:
            report = resolve_review(image.copy(),json.loads(args.review.read_text()))
        (args.output/"qa/static-review-resolution.json").write_text(json.dumps(report,indent=2)+"\n")
    else:
        report = prepare(args.output)
    print(report["status"])
