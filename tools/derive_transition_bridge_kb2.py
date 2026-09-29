"""Conditional KB2 local derivation and fail-closed full static-chain recheck."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image, ImageDraw

from tools.audit_transition_bridge import kb1_inputs, measure, resolve
from tools.controlled_transition_k2 import assess as assess_k2, transparent_holes
from tools.controlled_transition_k3 import assess as assess_k3
from tools.derive_transition_bridge import VISUAL_CHECKS, contact
from tools.locked_transition_k1 import assess as assess_k1, sha
from tools.prepare_manual_transition_endpoints import pixel_overlay
from tools.prepare_transition_animation_candidate import digest, metrics
from tools.transition_bridge_spec import B_HEAD, K3_HEAD, OUTPUT, landmark, step_gate

PLAN = OUTPUT/"kb2-edit-plan.json"


def authorized_inputs(review_file: Path | None = None) -> tuple[dict,Image.Image,dict]:
    frozen,kb1,kb1_plan = kb1_inputs()
    report = measure(frozen,kb1,kb1_plan)
    path = review_file or OUTPUT/"kb1-b-gate/independent-review.json"
    verdict = resolve(report,json.loads(path.read_text()))
    if verdict["status"] != "KB2_REQUIRED":
        raise ValueError("fresh incoming PASS and KB2_REQUIRED required; no unconditional second bridge")
    return frozen,kb1,kb1_plan


def validate_plan(plan: dict, source: Image.Image) -> None:
    if plan.get("id") != "KB2_BOUNDED_LOCAL_V1" or plan.get("sourceRgbaSha256") != sha(source.tobytes()):
        raise ValueError("pinned static-pass KB1 required")
    if plan.get("headSourceBbox") != [57,4,119,78] or plan.get("headTargetBbox") != [60,4,116,72]:
        raise ValueError("no head step beyond6px/axis")
    if plan.get("sourceBodyColumns") != [54,84,103,135] or plan.get("bodyStartY") != 72:
        raise ValueError("local KB1 donor panels only")
    if plan.get("headResampler") != "NEAREST" or plan.get("lowerLockFromY") != 164:
        raise ValueError("nearest local head and fixed feet only")
    if plan.get("neckRowOffset") != 6 or plan.get("neckTaperEveryRows") != 5:
        raise ValueError("documented upper-body connection required")
    if plan.get("armSourceBox") != [54,128,84,164] or plan.get("armShift") != [2,-2]:
        raise ValueError("small native forearm onset only")
    if any(plan.get(key) is not False for key in ("globalScaling","globalTranslation","aiGeneration","effects","interpolation")):
        raise ValueError("no global fit, generation, interpolation or effects")
    last_y,last_d = 72,0
    for band in plan["bodyBands"]:
        y0,y1,d = band
        if any(type(v) is not int for v in band) or y0 != last_y or not 72 <= y0 < y1 <= 140 or not 1 <= d <= 6 or abs(d-last_d) > 1:
            raise ValueError("continuous native body taper required")
        last_y,last_d = y1,d
    if last_y != 140 or last_d != 1:
        raise ValueError("complete tapered profile required")


def apply_step(source: Image.Image, plan: dict) -> Image.Image:
    _,actual,_ = authorized_inputs()
    if source.mode != "RGBA" or source.size != (192,208) or source.tobytes() != actual.tobytes():
        raise ValueError("exact native reviewed KB1 required")
    validate_plan(plan,source)
    result = source.copy()
    src,dst = source.load(),result.load()
    for y in range(78):
        for x in range(192):
            dst[x,y] = (0,0,0,0)
    part = source.crop((57,4,119,78)).resize((56,68),Image.Resampling.NEAREST)
    result.paste(part,(60,4))
    for y0,y1,d in plan["bodyBands"]:
        for y in range(y0,y1):
            sy = y+max(0,6-(y-72)//5)
            for x in range(48,141):
                dst[x,y] = (0,0,0,0)
            for x in range(54,84):
                dst[x-d,y] = src[x,sy]
            for x in range(84-d,84):
                dst[x,y] = src[83,sy]
            for x in range(84,103):
                dst[x,y] = src[x,sy]
            for x in range(103,103+d):
                dst[x,y] = src[103,sy]
            for x in range(103,135):
                dst[x+d,y] = src[x,sy]
    arm = result.crop((54,128,84,164))
    ImageDraw.Draw(result).rectangle((54,128,83,163),fill=(0,0,0,0))
    result.paste(arm,(56,126))
    return result


def assess(source: Image.Image, candidate: Image.Image, plan: dict) -> dict:
    validate_plan(plan,source)
    if candidate.mode != "RGBA" or candidate.size != (192,208):
        raise ValueError("native 192x208 RGBA required")
    expected = apply_step(source,plan)
    left = landmark(source,plan["headSourceBbox"])
    right = landmark(candidate,plan["headTargetBbox"])
    pair = step_gate(left,right)
    info = metrics(candidate)
    head = candidate.getchannel("A").crop((0,0,192,72)).getbbox()
    checks = {"exactDocumentedLocalDerivation":expected.tobytes() == candidate.tobytes(),
              "headGuideMatchesActualPartHull":list(head) == plan["headTargetBbox"] if head else False,
              "numericBudget":pair["numericPass"],
              "lower164FeetByteIdentical":source.crop((0,164,192,208)).tobytes() == candidate.crop((0,164,192,208)).tobytes(),
              "sourcePaletteOnly":set(candidate.get_flattened_data()) <= set(source.get_flattened_data()),
              "binaryAlpha":info["alphaValues"] == [0,255],"noHiddenRGB":not info["hiddenRgbPixels"],
              "noClipping":not info["touchesCellEdge"],"oneConnectedCharacter":len(info["connectedComponentSizes8"]) == 1,
              "noIsolatedPixels":not info["isolatedSinglePixels"],
              "noNewTransparentHoles":transparent_holes(candidate) <= transparent_holes(source)}
    return {"status":"AWAITING_INDEPENDENT_STATIC_REVIEW" if all(checks.values()) else "KB2_QA_FAIL",
            "technicalPass":all(checks.values()),"checks":checks,"source":left,"candidate":right,"pair":pair,
            "measured":info,"localChainAllowed":False,"userArtApproval":"PENDING","runtimeEligible":False}


def resolve_review(source: Image.Image, candidate: Image.Image, plan: dict, review: dict) -> dict:
    report = assess(source,candidate,plan)
    fresh = review.get("sourceRgbaSha256") == sha(source.tobytes()) and review.get("candidateRgbaSha256") == sha(candidate.tobytes())
    visual = all((value.get("status") if isinstance(value,dict) else value) == "PASS"
                 for key in VISUAL_CHECKS for value in (review.get("checks",{}).get(key),))
    passed = report["technicalPass"] and fresh and bool(review.get("reviewer")) and visual and review.get("verdict") == "KB1_KB2_STATIC_PASS"
    return {**report,"status":"KB1_KB2_STATIC_PASS" if passed else "KB2_QA_FAIL",
            "independentReviewFresh":fresh,"localChainAllowed":passed}


def prepare(output: Path = OUTPUT/"kb2") -> dict:
    if output.exists():
        raise ValueError("refuse to overwrite KB2 or evidence")
    _,source,_ = authorized_inputs()
    plan = json.loads(PLAN.read_text())
    image = apply_step(source,plan)
    report = assess(source,image,plan)
    qa = output/"qa"
    qa.mkdir(parents=True)
    image.save(output/"KB2.png")
    overlay = pixel_overlay(source,image)
    overlay.save(qa/"overlay.png")
    diff = Image.new("L",(192,208))
    diff.putdata([255 if a != b else 0 for a,b in zip(source.get_flattened_data(),image.get_flattened_data())])
    diff.save(qa/"difference-mask.png")
    contact(qa/"contact-sheet.png",["KB1 STATIC PASS","KB2 CANDIDATE","RGBA diff"],[source,image,overlay])
    report.update({"planSha256":digest(PLAN),"candidatePngSha256":digest(output/"KB2.png"),
                   "candidateRgbaSha256":sha(image.tobytes()),"sourceRgbaSha256":sha(source.tobytes()),
                   "newPoses":["KB2"],"aiUsed":False,"approvedFilesModified":False})
    (qa/"landmark-report.json").write_text(json.dumps(report,indent=2)+"\n")
    return report


def finalize_incoming(output: Path, review_file: Path) -> dict:
    _,source,_ = authorized_inputs()
    with Image.open(output/"KB2.png") as image:
        candidate = image.copy()
    plan = json.loads(PLAN.read_text())
    report = resolve_review(source,candidate,plan,json.loads(review_file.read_text()))
    (output/"qa/static-review-resolution.json").write_text(json.dumps(report,indent=2)+"\n")
    return report


def chain_data(frozen: dict, kb1: Image.Image, kb2: Image.Image) -> tuple[dict,list,dict]:
    """Measure all seven actual PNGs; original gates apply to prior approvals."""
    prior = {"A_K1":assess_k1(frozen["K1"])["technicalPass"],
             "K1_K2":assess_k2(frozen["K2"])["technicalPass"],
             "K2_K3":assess_k3(frozen["K3"])["technicalPass"]}
    if not all(prior.values()):
        raise ValueError("approved prior chain no longer satisfies original gates")
    names = ["A","K1","K2","K3","KB1","KB2","B"]
    images = [*(frozen[name] for name in names[:4]),kb1,kb2,frozen["B"]]
    guides = [K3_HEAD]*4+[[57,4,119,78],[60,4,116,72],B_HEAD]
    landmarks = {name:landmark(image,guide,approximate=name=="B") for name,image,guide in zip(names,images,guides)}
    pairs = {f"{left}_{right}":step_gate(landmarks[left],landmarks[right]) for left,right in zip(names,names[1:])}
    # Bridge budgets apply only to new links, not retroactively to approved A/K1.
    for name in ("A_K1","K1_K2","K2_K3"):
        pairs[name]["approval"] = "PASS_CURRENT_USER_ART_APPROVAL_AND_ORIGINAL_TECHNICAL_GATE"
        pairs[name]["newBridgeBudgetApplies"] = False
        pairs[name]["staticVerdict"] = "PASS_USER_ART_APPROVAL_AND_ORIGINAL_TECHNICAL_GATE"
        pairs[name]["effectiveGatePass"] = prior[name]
    for name in ("K3_KB1","KB1_KB2"):
        pairs[name]["newBridgeBudgetApplies"] = True
        pairs[name]["staticVerdict"] = "PASS_FRESH_INDEPENDENT_INCOMING_REVIEW_REQUIRED_BY_CALLER"
        pairs[name]["effectiveGatePass"] = pairs[name]["numericPass"]
    report = {"status":"AWAITING_INDEPENDENT_FINAL_ENDPOINT_REVIEW","landmarks":landmarks,"pairs":pairs,
              "previousApprovedChainTechnicalPass":prior,"K3_KB1":"STATIC_PASS","KB1_KB2":"STATIC_PASS",
              "bridgeFramesGenerated":2,"additionalFramesGenerated":0,"approvedInputsModified":False,
              "newBridgeUserArtApproval":"PENDING","fullAnimationAllowed":False,"runtimeEligible":False}
    return report,images,pairs


def full_chain_measure(output: Path = OUTPUT/"full-chain-qa", incoming_review_file: Path | None = None) -> dict:
    if output.exists():
        raise ValueError("refuse to overwrite full chain evidence")
    frozen,kb1,_ = authorized_inputs()
    with Image.open(OUTPUT/"kb2/KB2.png") as image:
        kb2 = image.copy()
    plan = json.loads(PLAN.read_text())
    review_file = incoming_review_file or OUTPUT/"kb2/qa/independent-review.json"
    incoming = resolve_review(kb1,kb2,plan,json.loads(review_file.read_text()))
    if not incoming["localChainAllowed"]:
        raise ValueError("fresh KB1_KB2_STATIC_PASS required before full chain audit")
    report,images,_ = chain_data(frozen,kb1,kb2)
    names = list(report["landmarks"])
    output.mkdir(parents=True)
    contact(output/"contact-sheet.png",names,images)
    for left,right in (("K3","KB1"),("KB1","KB2"),("KB2","B")):
        li,ri = names.index(left),names.index(right)
        contact(output/f"{left}-{right}-overlay-contact.png",[left,right,"RGBA diff"],
                [images[li],images[ri],pixel_overlay(images[li],images[ri])])
    (output/"landmark-report.json").write_text(json.dumps(report,indent=2)+"\n")
    return report


def resolve_final(report: dict, review: dict) -> dict:
    # Incoming links must also remain valid when finalizing; no cached QA PASS.
    frozen,kb1,_ = authorized_inputs()
    with Image.open(OUTPUT/"kb2/KB2.png") as image:
        kb2 = image.copy()
    incoming = resolve_review(kb1,kb2,json.loads(PLAN.read_text()),json.loads((OUTPUT/"kb2/qa/independent-review.json").read_text()))
    current,_,_ = chain_data(frozen,kb1,kb2)
    if report != current or not incoming["localChainAllowed"]:
        raise ValueError("stale or altered full-chain evidence")
    actual,b,pair = current["landmarks"]["KB2"],current["landmarks"]["B"],current["pairs"]["KB2_B"]
    fresh = review.get("kb2RgbaSha256") == actual["rgbaSha256"] and review.get("bRgbaSha256") == b["rgbaSha256"]
    valid = fresh and bool(review.get("reviewer"))
    incoming_budgets = all(current["pairs"][name]["numericPass"] for name in ("K3_KB1","KB1_KB2"))
    passed = valid and incoming_budgets and pair["numericPass"] and review.get("KB2_B") == "PASS" and review.get("faceIdentity") == review.get("armPoseContinuity") == "PASS"
    failed = valid and review.get("KB2_B") == "FAIL"
    status = "B_BRIDGE_ART_APPROVED" if passed else "B_BRIDGE_QA_FAIL_MORE_ART_SCOPE_REQUIRED" if failed else "B_BRIDGE_NOT_VERIFIED"
    return {"status":status,"B_BRIDGE_ART_APPROVED":passed,"wholeChainStaticPass":passed,
            "K3_KB1":"STATIC_PASS","KB1_KB2":"STATIC_PASS","KB2_B":"STATIC_PASS" if passed else "STATIC_FAIL" if failed else "NOT_VERIFIED",
            "independentReviewFresh":fresh,"outgoingNumericPass":pair["numericPass"],
            "actualBridgeFrames":2,"twoBridgesSufficient":passed,"additionalBridgeFramesAuthorized":False,
            "nominalAdditionalBridgeLowerBound":max((abs(v)+5)//6 for v in pair["headSizeDelta"])-1,
            "fullAnimationAllowed":passed,"runtimeEligible":False,"manualUserReviewNewBridges":"NOT_PERFORMED"}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output",type=Path,default=OUTPUT/"kb2")
    parser.add_argument("--review",type=Path)
    parser.add_argument("--full-chain",action="store_true")
    parser.add_argument("--final-review",type=Path)
    args = parser.parse_args()
    if args.final_review:
        report = json.loads((OUTPUT/"full-chain-qa/landmark-report.json").read_text())
        result = resolve_final(report,json.loads(args.final_review.read_text()))
        (OUTPUT/"full-chain-qa/final-verdict.json").write_text(json.dumps(result,indent=2)+"\n")
    elif args.full_chain:
        result = full_chain_measure()
    elif args.review:
        result = finalize_incoming(args.output,args.review)
    else:
        result = prepare(args.output)
    print(result["status"])
