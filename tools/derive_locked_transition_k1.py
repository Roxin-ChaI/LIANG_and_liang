"""Apply the user-authorized explicit local pixel edit plan to A; never redraw identity."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil

from PIL import Image, ImageDraw

from tools.locked_transition_k1 import OUTPUT, assess, masks, sha
from tools.prepare_manual_transition_endpoints import pixel_overlay
from tools.prepare_transition_animation_candidate import digest
from tools.specify_transition_keyframes import approved_inputs

PLAN = OUTPUT / "pixel-edit-plan.json"
STATIC_CHECKS = ("identity","lockedRegions","headNeckProportions","seamsAndHoles",
                 "handArmPlausibility","noClip","AtoK1Continuity","restrainedGuAppearance")


def resolve_static_review(candidate: Image.Image, review: dict) -> dict:
    report = assess(candidate)
    evidence_matches = review.get("reviewedRgbaSha256") == sha(candidate.tobytes())
    checks = {key:review.get("checks",{}).get(key,{}).get("status","unknown") for key in STATIC_CHECKS}
    visual_pass = (review.get("reviewer") and review.get("verdict") == "A_K1_STATIC_PASS"
                   and evidence_matches and all(value == "pass" for value in checks.values()))
    report["status"] = ("A_K1_STATIC_PASS" if report["technicalPass"] and visual_pass
                        else "K1_QA_FAIL" if not report["technicalPass"] or "fail" in checks.values()
                        else "K1_STATIC_NOT_VERIFIED")
    report.update({"independentStaticChecks":checks,"reviewedPixelsMatch":evidence_matches,
                   "localChainAllowed":report["status"] == "A_K1_STATIC_PASS",
                   "chargeIntent":review.get("checks",{}).get("chargeIntentReadability",{}).get("status","unknown"),
                   "userArtApproval":"PENDING","runtimeEligible":False,
                   "approvalScope":"A->K1 static continuity only; never full chain, animation or App approval"})
    return report


def apply_plan(a: Image.Image, plan: dict) -> tuple[Image.Image, list[dict]]:
    if a.size != (192,208) or a.mode != "RGBA":
        raise ValueError("native A required; no fit")
    locked,editable = masks()
    result = a.copy()
    records, occupied = [],set()
    for op in plan["operations"]:
        l,t,r,b = op["sourceBox"]
        dx,dy = op["integerDelta"]
        if not all(type(v) is int for v in (l,t,r,b,dx,dy)) or not (0 <= l < r <= 192 and 0 <= t < b <= 208):
            raise ValueError("integer in-cell source rectangle required")
        if abs(dx) > 1 or abs(dy) > 1 or (r-l)*(b-t) > 1024:
            raise ValueError("only small manually specified local pixel moves allowed")
        sources = {(x,y) for y in range(t,b) for x in range(l,r)}
        destinations = {(x+dx,y+dy) for x,y in sources}
        touched = sources | destinations
        if any(not (0 <= x < 192 and 0 <= y < 208) or not editable.getpixel((x,y)) for x,y in touched):
            raise ValueError("MANUAL_PIXEL_ART_REQUIRED: edit touches frozen/locked region")
        if occupied & touched:
            raise ValueError("overlapping edit operations require a separate manual plan")
        occupied |= touched
        for xy in sources-destinations:
            result.putpixel(xy,(0,0,0,0))
        for x,y in sorted(sources):
            result.putpixel((x+dx,y+dy),a.getpixel((x,y)))
        records.append({**op,"copiedPixels":len(sources),"clearedVacatedPixels":len(sources-destinations),
                        "donor":"exact immutable A pixel","interpolation":False})
    return result,records


def prepare(output: Path = OUTPUT / "candidate") -> dict:
    if output.exists():
        raise ValueError("refuse to overwrite pixel candidate")
    plan = json.loads(PLAN.read_text())
    _,source,a = approved_inputs()[0]
    k,operations = apply_plan(a,plan)
    report = assess(k)
    if not report["technicalPass"]:
        raise ValueError("K1_QA_FAIL: do not emit an unsafe pixel-derived candidate")
    output.mkdir(parents=True)
    qa = output/"qa"
    qa.mkdir()
    shutil.copyfile(source,output/"A.png")
    k.save(output/"K1.png")
    diff = Image.new("L",(192,208))
    diff.putdata([255 if p != q else 0 for p,q in zip(a.get_flattened_data(),k.get_flattened_data())])
    diff.save(qa/"difference-mask.png")
    overlay = pixel_overlay(a,k)
    overlay.save(qa/"overlay.png")
    sheet = Image.new("RGBA",(576,240),(35,35,35,255))
    draw = ImageDraw.Draw(sheet)
    for i,(label,image) in enumerate((("A FROZEN",a),("K1 LOCAL PIXELS",k),("RGBA diff overlay",overlay))):
        sheet.alpha_composite(image,(i*192,28))
        draw.text((i*192+3,3),label,fill="white")
        draw.line((i*192,231,i*192+191,231),fill=(255,175,45,255))
    sheet.save(qa/"contact-sheet.png")
    # Enlarged only for diagnostic pixel inspection, never as candidate art.
    sheet.resize((1728,720),Image.Resampling.NEAREST).save(qa/"contact-sheet-nearest3x.png")
    report.update({"sourceSha256":digest(source),"candidateSha256":digest(output/"K1.png"),
                   "method":"explicit user-authorized local integer A pixel derivation",
                   "operations":operations,"globalScaleOperations":0,"AIUsed":False,"effectsAdded":False,
                   "K2K3Modified":False,"appIntegrated":False})
    (qa/"landmark-report.json").write_text(json.dumps(report,indent=2)+"\n")
    (qa/"locked-region-byte-comparison.json").write_text(json.dumps(report["lockedByteComparison"],indent=2)+"\n")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output",type=Path,default=OUTPUT/"candidate")
    parser.add_argument("--review",type=Path)
    args = parser.parse_args()
    if args.review:
        with Image.open(args.output/"K1.png") as image:
            result = resolve_static_review(image,json.loads(args.review.read_text()))
        (args.output/"qa/static-review-resolution.json").write_text(json.dumps(result,indent=2)+"\n")
        print(result["status"])
    else:
        print(prepare(args.output)["status"])
