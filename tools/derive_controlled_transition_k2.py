"""Single local K2 candidate from approved K1; no new K3 or animation frames."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image, ImageDraw

from tools.controlled_transition_k2 import K1_SHA, OUTPUT, assess, masks, source
from tools.locked_transition_k1 import sha
from tools.prepare_manual_transition_endpoints import pixel_overlay
from tools.prepare_transition_animation_candidate import digest

PLAN = OUTPUT / "pixel-edit-plan.json"
CANDIDATE = OUTPUT / "candidate-locked-hands"
STATIC_CHECKS = ("identity", "headNeckUnchanged", "shoulderGrowthGradual", "bodyIntermediate",
                 "clothSeamsPlausible", "handsLegsFeetStable", "K1K2Continuity", "noPixelArtifacts")


def apply_plan(k1: Image.Image, plan: dict) -> Image.Image:
    if k1.mode != "RGBA" or k1.size != (192, 208) or k1.tobytes() != source().tobytes():
        raise ValueError("exact approved native K1 required; no input scaling or substitution")
    if plan.get("sourceSha256") != K1_SHA or plan.get("id") != "K2_LOCAL_JACKET_THICKENING_V1":
        raise ValueError("pinned K1 and bounded local plan required")
    if plan.get("leftSourceColumns") != [69, 84] or plan.get("rightSourceColumns") != [103, 121]:
        raise ValueError("body panels fixed; no whole-side scaling")
    if any(plan.get(key) is not False for key in ("headNeckEdited", "handsLegsFeetEdited", "energyEffects", "globalScalingOrTranslation", "interpolation", "aiGeneration")):
        raise ValueError("plan cannot claim head/body fit, effects or generation")
    locked, _ = masks()
    k2 = k1.copy()
    src, dst = k1.load(), k2.load()
    visited = set()
    previous_delta = 0
    for band in plan["rowBands"]:
        y0, y1 = band["y"]
        delta = band["outwardPixels"]
        if type(delta) is not int or not 1 <= delta <= 4 or abs(delta-previous_delta) > 1:
            raise ValueError("local movement at most4px with at most1px profile steps")
        if type(y0) is not int or type(y1) is not int or not 84 <= y0 < y1 <= 140:
            raise ValueError("upper-body rows only")
        for y in range(y0, y1):
            if y in visited:
                raise ValueError("row bands must not overlap")
            visited.add(y)
            for x in (*range(69-delta, 84), *range(103, 121+delta)):
                if locked.getpixel((x, y)):
                    raise ValueError("MANUAL_PIXEL_ART_REQUIRED: plan would touch locked identity/body")
            # Native local-panel translation, never an affine scale/warp.
            for x in range(69, 84):
                dst[x-delta, y] = src[x, y]
            for x in range(84-delta, 84):
                dst[x, y] = src[83, y]
            for x in range(103, 121):
                dst[x+delta, y] = src[x, y]
            for x in range(103, 103+delta):
                dst[x, y] = src[103, y]
        previous_delta = delta
    if visited != set(range(84, 140)) or previous_delta != 1:
        raise ValueError("continuous documented profile required; no partial silhouette shortcut")
    return k2


def resolve_review(candidate: Image.Image, review: dict) -> dict:
    report = assess(candidate)
    fresh = review.get("reviewedRgbaSha256") == sha(candidate.tobytes())
    visual_pass = (bool(review.get("reviewer")) and review.get("verdict") == "K1_K2_STATIC_PASS"
                   and all((value.get("status") if isinstance(value, dict) else value) == "PASS"
                           for key in STATIC_CHECKS for value in (review.get("checks", {}).get(key),)))
    if not report["technicalPass"]:
        status = "K2_QA_FAIL"
    elif fresh and visual_pass:
        status = "K1_K2_STATIC_PASS"
    elif fresh and review.get("verdict") in ("K2_QA_FAIL", "MANUAL_PIXEL_ART_REQUIRED"):
        status = review["verdict"]
    else:
        status = "K2_STATIC_NOT_VERIFIED"
    return {**report, "status": status, "independentReviewFresh": fresh,
            "localChainAllowed": status == "K1_K2_STATIC_PASS",
            "userArtApproval": "PENDING", "runtimeEligible": False}


def prepare(output: Path = CANDIDATE) -> dict:
    if output.exists():
        raise ValueError("refuse to overwrite K2 candidate")
    plan = json.loads(PLAN.read_text())
    k1 = source()
    k2 = apply_plan(k1, plan)
    report = assess(k2)
    if not report["technicalPass"]:
        raise ValueError("K2_QA_FAIL: reject local derivation before emitting playable candidate: "+str(report["checks"]))
    qa = output/"qa"
    qa.mkdir(parents=True)
    path = output/"K2.png"
    k2.save(path)
    difference = Image.new("L", k1.size)
    difference.putdata([255 if a != b else 0 for a, b in zip(k1.get_flattened_data(), k2.get_flattened_data())])
    difference.save(qa/"difference-mask.png")
    overlay = pixel_overlay(k1, k2)
    overlay.save(qa/"overlay.png")
    guide = k2.copy()
    gd = ImageDraw.Draw(guide)
    gd.rectangle((54, 4, 121, 83), outline=(255, 185, 45, 255))
    gd.rectangle((report["bodyBbox"][0], 70, report["bodyBbox"][2]-1, 203), outline=(130, 230, 190, 255))
    gd.line((96, 0, 96, 207), fill=(255, 80, 100, 255))
    gd.line((0, 203, 191, 203), fill=(255, 185, 45, 255))
    guide.save(qa/"landmark-guide.png")
    sheet = Image.new("RGBA", (768, 240), (35, 35, 35, 255))
    draw = ImageDraw.Draw(sheet)
    for i, (label, image) in enumerate(zip(("K1 APPROVED", "K2 LOCAL CANDIDATE", "pixel diff overlay", "guides NOT art"), (k1, k2, overlay, guide))):
        sheet.alpha_composite(image, (i*192, 28))
        draw.text((i*192+3, 3), label, fill="white")
    sheet.save(qa/"contact-sheet.png")
    sheet.resize((2304, 720), Image.Resampling.NEAREST).save(qa/"contact-sheet-nearest3x.png")
    report.update({"sourceSha256": K1_SHA, "candidatePngSha256": digest(path),
                   "candidateRgbaSha256": sha(k2.tobytes()), "pixelEditPlanSha256": digest(PLAN),
                   "method": plan["method"], "newPoses": ["K2"], "aiUsed": False,
                   "scale": "none; QA magnification only uses nearest-neighbor", "retryCount": 0})
    (qa/"landmark-report.json").write_text(json.dumps(report, indent=2)+"\n")
    (qa/"locked-region-byte-comparison.json").write_text(json.dumps(report["lockedByteComparison"], indent=2)+"\n")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=CANDIDATE)
    parser.add_argument("--review", type=Path)
    args = parser.parse_args()
    if args.review:
        with Image.open(args.output/"K2.png") as image:
            report = resolve_review(image.copy(), json.loads(args.review.read_text()))
        (args.output/"qa/static-review-resolution.json").write_text(json.dumps(report, indent=2)+"\n")
    else:
        report = prepare(args.output)
    print(report["status"])
