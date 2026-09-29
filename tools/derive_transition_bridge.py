"""One bounded local KB1 derivation; no whole-character fit or App integration."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image, ImageDraw

from tools.controlled_transition_k2 import transparent_holes
from tools.locked_transition_k1 import sha
from tools.prepare_manual_transition_endpoints import pixel_overlay
from tools.prepare_transition_animation_candidate import digest, metrics
from tools.transition_bridge_spec import K3_HEAD, OUTPUT, ROOT, frozen_images, landmark, step_gate

PLAN = OUTPUT/"kb1-edit-plan.json"
VISUAL_CHECKS = ("faceIdentity", "headContinuity", "neckCollarConnection", "bodyProgression",
                 "armAttachment", "clothSeams", "feetFixed", "noPixelArtifacts", "incomingContinuity")


def validate_plan(plan: dict) -> None:
    if plan.get("id") != "KB1_BOUNDED_LOCAL_V1" or plan.get("source") != "K3":
        raise ValueError("only KB1 from approved K3 authorized")
    if plan.get("headSourceBbox") != K3_HEAD or plan.get("headTargetBbox") != [57,4,119,78]:
        raise ValueError("pinned local head-part transform required")
    if plan.get("headResampler") != "NEAREST" or plan.get("lowerLockFromY") != 164:
        raise ValueError("nearest head only; original feet/lower body locked")
    if any(plan.get(key) is not False for key in ("globalScaling", "globalTranslation", "aiGeneration", "effects", "interpolation")):
        raise ValueError("no global transform, AI, effects or interpolation")
    if plan.get("sourceBodyColumns") != [60,84,103,129] or plan.get("bodyStartY") != 78:
        raise ValueError("documented local donor panels only")
    if plan.get("neckRowOffset") != 6 or plan.get("neckTaperEveryRows") != 5:
        raise ValueError("documented neck/shoulder row attachment required")
    if plan.get("armSourceBox") != [60,130,84,164] or plan.get("armShift") != [1,-1]:
        raise ValueError("one-pixel forearm onset only")
    last_y, last_d = 78, 0
    for band in plan["bodyBands"]:
        y0,y1,d = band
        if any(type(v) is not int for v in band) or y0 != last_y or not 78 <= y0 < y1 <= 140 or not 1 <= d <= 6 or abs(d-last_d) > 1:
            raise ValueError("continuous tapered native body copies required")
        last_y,last_d = y1,d
    if last_y != 140 or last_d != 1:
        raise ValueError("full tapered body profile required")


def apply_step(source: Image.Image, plan: dict) -> Image.Image:
    validate_plan(plan)
    approved = frozen_images()["K3"]
    if source.mode != "RGBA" or source.size != (192,208) or source.tobytes() != approved.tobytes():
        raise ValueError("exact frozen native K3 required")
    if plan.get("sourceRgbaSha256") != sha(source.tobytes()):
        raise ValueError("stale source pin")
    result = source.copy()
    dst, src = result.load(), source.load()
    # Replace only the upper assembly. Feet and lower body never undergo a fit.
    for y in range(84):
        for x in range(192):
            dst[x,y] = (0,0,0,0)
    target = plan["headTargetBbox"]
    part = source.crop(tuple(K3_HEAD)).resize((62,74), Image.Resampling.NEAREST)
    result.paste(part, (target[0],target[1]))
    # Move the upper jacket/neck connection up to meet the smaller head, then
    # taper to unchanged source rows. All body colors are native source donors.
    for y0,y1,d in plan["bodyBands"]:
        for y in range(y0,y1):
            sy = y+max(0,6-(y-78)//5)
            for x in range(54,135):
                dst[x,y] = (0,0,0,0)
            for x in range(60,84):
                dst[x-d,y] = src[x,sy]
            for x in range(84-d,84):
                dst[x,y] = src[83,sy]
            for x in range(84,103):
                dst[x,y] = src[x,sy]
            for x in range(103,103+d):
                dst[x,y] = src[103,sy]
            for x in range(103,129):
                dst[x+d,y] = src[x,sy]
    # Beginning forearm raise only; existing hand pixels stay attached to cuff.
    arm_box = tuple(plan["armSourceBox"])
    arm = result.crop(arm_box)
    ImageDraw.Draw(result).rectangle((60,130,83,163), fill=(0,0,0,0))
    result.paste(arm,(61,129))
    return result


def assess(source: Image.Image, candidate: Image.Image, plan: dict) -> dict:
    validate_plan(plan)
    if candidate.mode != "RGBA" or candidate.size != (192,208):
        raise ValueError("native 192x208 RGBA candidate required")
    expected = apply_step(source,plan)
    left = landmark(source,K3_HEAD)
    right = landmark(candidate,plan["headTargetBbox"])
    pair = step_gate(left,right)
    info = metrics(candidate)
    actual_head = candidate.getchannel("A").crop((0,0,192,78)).getbbox()
    checks = {"exactDocumentedLocalDerivation": expected.tobytes() == candidate.tobytes(),
              "headGuideMatchesActualPartHull": list(actual_head) == plan["headTargetBbox"] if actual_head else False,
              "numericBudget": pair["numericPass"],
              "lower164FeetByteIdentical": source.crop((0,164,192,208)).tobytes() == candidate.crop((0,164,192,208)).tobytes(),
              "sourcePaletteOnly": set(candidate.get_flattened_data()) <= set(source.get_flattened_data()),
              "binaryAlpha": info["alphaValues"] == [0,255], "noHiddenRGB": not info["hiddenRgbPixels"],
              "noClipping": not info["touchesCellEdge"], "noIsolatedPixels": not info["isolatedSinglePixels"],
              "oneConnectedCharacter": len(info["connectedComponentSizes8"]) == 1,
              "noNewTransparentHoles": transparent_holes(candidate) <= transparent_holes(source)}
    changed = Image.new("L",(192,208))
    changed.putdata([255 if a != b else 0 for a,b in zip(source.get_flattened_data(),candidate.get_flattened_data())])
    return {"status": "AWAITING_INDEPENDENT_STATIC_REVIEW" if all(checks.values()) else "KB1_QA_FAIL",
            "technicalPass": all(checks.values()), "checks": checks,
            "source": left, "candidate": right, "pair": pair, "measured": info,
            "changedPixels": sum(bool(v) for v in changed.get_flattened_data()), "changedBbox": changed.getbbox(),
            "method": "local head part NEAREST only; native jacket/neck/forearm copies; no whole-person resampling",
            "headGuideWarning": "historical neck-inclusive head reference part, not exact anatomical skull segmentation",
            "localChainAllowed": False, "artApproval": "PENDING_USER", "runtimeEligible": False}


def resolve_review(source: Image.Image, candidate: Image.Image, plan: dict, review: dict) -> dict:
    report = assess(source,candidate,plan)
    fresh = (review.get("sourceRgbaSha256") == sha(source.tobytes()) and
             review.get("candidateRgbaSha256") == sha(candidate.tobytes()))
    all_visual = all((value.get("status") if isinstance(value,dict) else value) == "PASS"
                     for key in VISUAL_CHECKS for value in (review.get("checks",{}).get(key),))
    passed = report["technicalPass"] and fresh and bool(review.get("reviewer")) and all_visual and review.get("verdict") == "K3_KB1_STATIC_PASS"
    return {**report,"status": "K3_KB1_STATIC_PASS" if passed else "KB1_QA_FAIL",
            "independentReviewFresh": fresh,"localChainAllowed": passed}


def contact(output: Path, names: list[str], images: list[Image.Image]) -> None:
    sheet = Image.new("RGBA",(192*len(images),240),(35,35,35,255))
    draw = ImageDraw.Draw(sheet)
    for i,(name,image) in enumerate(zip(names,images)):
        sheet.alpha_composite(image,(192*i,28))
        draw.text((192*i+3,3),name,fill="white")
        draw.line((192*i,231,192*i+191,231),fill=(255,185,45,255))
    sheet.save(output)
    sheet.resize((sheet.width*3,720),Image.Resampling.NEAREST).save(output.with_name(output.stem+"-nearest3x.png"))


def prepare(output: Path = OUTPUT/"kb1") -> dict:
    if output.exists():
        raise ValueError("refuse to overwrite KB1 candidate or evidence")
    plan = json.loads(PLAN.read_text())
    source = frozen_images()["K3"]
    image = apply_step(source,plan)
    report = assess(source,image,plan)
    qa = output/"qa"
    qa.mkdir(parents=True)
    image.save(output/"KB1.png")
    overlay = pixel_overlay(source,image)
    overlay.save(qa/"overlay.png")
    difference = Image.new("L",(192,208))
    difference.putdata([255 if a != b else 0 for a,b in zip(source.get_flattened_data(),image.get_flattened_data())])
    difference.save(qa/"difference-mask.png")
    contact(qa/"contact-sheet.png",["K3 FROZEN","KB1 CANDIDATE","RGBA diff"],[source,image,overlay])
    report.update({"planSha256": digest(PLAN),"candidatePngSha256": digest(output/"KB1.png"),
                   "candidateRgbaSha256": sha(image.tobytes()),"sourceRgbaSha256": sha(source.tobytes()),
                   "newPoses": ["KB1"], "aiUsed": False,"approvedFilesModified": False})
    (qa/"landmark-report.json").write_text(json.dumps(report,indent=2)+"\n")
    return report


def finalize(output: Path, review_file: Path) -> dict:
    plan = json.loads(PLAN.read_text())
    source = frozen_images()["K3"]
    with Image.open(output/"KB1.png") as image:
        candidate = image.copy()
    report = resolve_review(source,candidate,plan,json.loads(review_file.read_text()))
    (output/"qa/static-review-resolution.json").write_text(json.dumps(report,indent=2)+"\n")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output",type=Path,default=OUTPUT/"kb1")
    parser.add_argument("--review",type=Path)
    args = parser.parse_args()
    print((finalize(args.output,args.review) if args.review else prepare(args.output))["status"])
