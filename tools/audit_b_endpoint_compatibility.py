"""Read-only Feng B endpoint audit; canonical equality is not art suitability."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image, ImageDraw

from tools.prepare_transition_animation_candidate import digest, metrics
from tools.locked_transition_k1 import sha
from tools.transition_bridge_spec import B_HEAD, FROZEN, K3_HEAD, OUTPUT, ROOT, frozen_images, landmark

QA = OUTPUT / "b-endpoint-compatibility"
KB2 = OUTPUT / "kb2/KB2.png"
KB2_SHA = "622c81f99cde42f5846044a391424e7f4a8afa326d2c5e235470b2cacb618b19"
FENG_ATLAS = ROOT / "assets/builds/feng/spritesheet.webp"
FENG_ATLAS_SHA = "d697e573268b66cb0f6a062480ec87c8c11712ca34b57f8c2fc0a97ed6e2164a"
FENG_IDLE = ROOT / "hatch-runs/feng-v2/jobs/idle/decoded/idle.png"


def inputs() -> tuple[dict, Image.Image, Image.Image, Image.Image]:
    frozen = frozen_images()
    if digest(KB2) != KB2_SHA:
        raise ValueError("reviewed KB2 changed")
    if digest(FENG_ATLAS) != FENG_ATLAS_SHA:
        raise ValueError("formal Feng atlas changed")
    with Image.open(KB2) as image:
        if image.mode != "RGBA" or image.size != (192,208):
            raise ValueError("native KB2 geometry changed")
        kb2 = image.copy()
    with Image.open(FENG_ATLAS) as atlas:
        if atlas.mode != "RGBA" or atlas.size != (1536,2288):
            raise ValueError("formal Feng atlas geometry changed")
        atlas_idle = atlas.crop((0,0,192,208))
    with Image.open(FENG_IDLE) as strip:
        if strip.mode != "RGBA" or strip.size != (1152,208):
            raise ValueError("approved Feng idle strip geometry changed")
        strip_idle = strip.crop((0,0,192,208))
    return frozen,kb2,atlas_idle,strip_idle


def evidence() -> dict:
    frozen,kb2,atlas_idle,strip_idle = inputs()
    b = frozen["B"]
    b_metrics, kb2_metrics = metrics(b),metrics(kb2)
    bbox = b_metrics["alphaBbox"]
    guide_b = landmark(b,B_HEAD,approximate=True)
    guide_gu = landmark(frozen["A"],K3_HEAD)
    exact = (b.tobytes()==atlas_idle.tobytes()==strip_idle.tobytes())
    checks = {"frozenBMatchesFormalFengIdle0RawRgba": exact,
              "BMatchesC": digest(ROOT/FROZEN["B"][0]) == digest(ROOT/"assets/rework/v0.1.0/manual-transition-endpoints/C-feng-to-gu-entry.png"),
              "BHasCanvasSafetyMargin": bbox is not None and bbox[0]>=4 and bbox[1]>=4 and 192-bbox[2]>=4 and 208-bbox[3]>=4,
              "binaryAlpha": b_metrics["alphaValues"]==[0,255],
              "noHiddenRgb": not b_metrics["hiddenRgbPixels"],
              "baseline203": b_metrics["baselineY"]==kb2_metrics["baselineY"]==203,
              "noClipping": not b_metrics["touchesCellEdge"],
              "singleCharacter": len(b_metrics["connectedComponentSizes8"])==1}
    return {"status":"AWAITING_INDEPENDENT_B_ART_COMPATIBILITY_REVIEW" if all(checks.values()) else "B_TECHNICAL_QA_FAIL",
            "technicalPass":all(checks.values()),"checks":checks,
            "B":guide_b,"GuA":guide_gu,"KB2":landmark(kb2,[60,4,116,72]),
            "BFullAlphaBbox":bbox,"BVisibleMarginPx":{"left":bbox[0],"top":bbox[1],"right":192-bbox[2],"bottom":208-bbox[3]},
            "BFormalFengIdentityEvidence":"exact RGBA equality to formal v2 atlas Idle row0/frame0 and approved Feng idle strip frame0",
            "BIsUsableTransitionEndpoint":"NOT_YET_PROVEN_BY_CANONICAL_EQUALITY",
            "headGuideCaveat":"B49x54 manually approximated ±3px; chin occluded by finger; guide not skull segmentation",
            "headSizeGuToBApproxDelta":[guide_b["headSize"][i]-guide_gu["headSize"][i] for i in range(2)],
            "coordinateErrorCause":"EXCLUDED_IF_CHECKS_PASS",
            "changeStillToReview":"large anatomical head/face proportions; hand-to-chin vs Gu hands-at-side; wide stance; jacket cut, lapels, palette and expression",
            "hashes":{"B":sha(b.tobytes()),"KB2":sha(kb2.tobytes()),"FengAtlas":digest(FENG_ATLAS),
                      "FengIdle0":sha(strip_idle.tobytes())},
            "newArtGenerated":0,"approvedImagesModified":False,"runtimeEligible":False}


def prepare(output: Path = QA) -> dict:
    if output.exists():
        raise ValueError("refuse to overwrite compatibility evidence")
    data = evidence()
    frozen,kb2,atlas_idle,_ = inputs()
    output.mkdir(parents=True)
    frames = [("A / GU",frozen["A"]),("KB2",kb2),("B / FENG",frozen["B"]),("ATLAS IDLE 0",atlas_idle)]
    sheet = Image.new("RGBA",(768,240),(35,35,35,255))
    draw = ImageDraw.Draw(sheet)
    for index,(label,image) in enumerate(frames):
        sheet.alpha_composite(image,(index*192,28))
        draw.text((index*192+3,3),label,fill="white")
        draw.line((index*192,231,index*192+191,231),fill=(255,185,45,255))
    sheet.save(output/"endpoint-compatibility-contact.png")
    sheet.resize((2304,720),Image.Resampling.NEAREST).save(output/"endpoint-compatibility-nearest3x.png")
    (output/"technical-report.json").write_text(json.dumps(data,indent=2)+"\n")
    return data


def resolve(report: dict, review: dict) -> dict:
    fresh = review.get("reviewedBRgbaSha256")==report["hashes"]["B"] and review.get("reviewedKB2RgbaSha256")==report["hashes"]["KB2"]
    answered = (review.get("headIsCanonicalDesign") in ("CONFIRMED","NOT_PROVEN","UNKNOWN")
                and review.get("identityContinuityFeasibleWithTwoMoreFrames") in ("LIKELY","NOT_PROVEN","UNLIKELY")
                and review.get("chinHandIdleEndpointSuitability") in ("SUITABLE","NOT_PROVEN","UNSUITABLE"))
    accepted = (report["technicalPass"] and fresh and answered and bool(review.get("reviewer"))
                and review.get("verdict")=="B_ENDPOINT_COMPATIBLE" and
                review.get("headIsCanonicalDesign")=="CONFIRMED" and
                review.get("identityContinuityFeasibleWithTwoMoreFrames")=="LIKELY" and
                review.get("chinHandIdleEndpointSuitability")=="SUITABLE")
    rework = (report["technicalPass"] and fresh and answered and bool(review.get("reviewer"))
              and review.get("verdict")=="B_ENDPOINT_REWORK_REQUIRED")
    status = "B_ENDPOINT_COMPATIBLE" if accepted else "B_ENDPOINT_REWORK_REQUIRED" if rework else "B_ENDPOINT_NOT_VERIFIED"
    return {"status":status,"technicalPass":report["technicalPass"],"independentReviewFresh":fresh,
            "KB3Allowed":accepted,"newArtGenerated":0,"BModified":False,"runtimeEligible":False}


def finalize(output: Path, review_path: Path) -> dict:
    actual = evidence()
    saved = json.loads((output/"technical-report.json").read_text())
    if saved != actual:
        raise ValueError("stale or altered endpoint evidence")
    result = resolve(actual,json.loads(review_path.read_text()))
    (output/"final-verdict.json").write_text(json.dumps(result,indent=2)+"\n")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output",type=Path,default=QA)
    parser.add_argument("--review",type=Path)
    args = parser.parse_args()
    print((finalize(args.output,args.review) if args.review else prepare(args.output))["status"])
