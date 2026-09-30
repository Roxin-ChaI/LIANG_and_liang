"""Hand-selected KF1 identity pixels plus emerging F0 cloth/limb pixels."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from PIL import Image, ImageDraw

from tools.f0_morph_bridge import OUTPUT, HEAD_GUIDES, hand_guides, pair, sources
from tools.manual_kf1_pixel_art import DEST as KF1_DIR, contact, finalize as fresh_kf1
from tools.manual_kf1_pixel_art import masks as kb2_forearm_masks
from tools.prepare_transition_animation_candidate import digest, metrics
from tools.transition_bridge_spec import landmark
from tools.controlled_transition_k2 import transparent_holes

DEST = OUTPUT / "kf2"
KF1_SHA = "c189516b94db095e71a83460c7f2e831ca44841a6c97564f48252445ade1407b"
DROP_COLUMNS = (63,113)
DROP_ROWS = (12,23,54,61,66)
MID_BLUE = ((8,12,28,255),(16,22,46,255),(23,31,64,255),(28,39,81,255),
            (34,46,97,255),(40,53,113,255),(48,62,128,255),(58,74,143,255))
HAND_PARTS = {
    "left": {"box":[54,130,74,154],"dropCols":[57,61,65,70],"target":[61,131]},
    "right": {"box":[118,130,138,154],"dropCols":[121,125,129,134],"target":[114,131]},
}
FOREARM_OUTLINES = {
    "left": ((53,106),(47,115),(49,124),(58,131),(62,137),(75,137),(70,126),(60,119)),
    "right": ((138,106),(145,113),(146,123),(136,133),(130,137),(118,137),(124,126),(133,119)),
}
FOREARM_INNERS = {
    "left": ((53,109),(49,115),(51,123),(60,129),(64,135),(73,135),(68,127),(58,119)),
    "right": ((138,109),(143,114),(144,122),(134,132),(129,135),(120,135),(126,127),(135,120)),
}


def approved_kf1() -> Image.Image:
    if digest(KF1_DIR/"KF1.png") != KF1_SHA or not fresh_kf1()["KF2Allowed"]:
        raise ValueError("fresh reviewed KF1 PASS required before KF2")
    with Image.open(KF1_DIR/"KF1.png") as image:
        return image.copy()


def cloth(p: tuple) -> bool:
    r,g,b,a = p
    return bool(a and r < 105 and g < 120 and b > g and b > r)


def middle_blue(p: tuple) -> tuple:
    if not cloth(p) or sum(p[:3]) < 32:
        return p
    return min(MID_BLUE,key=lambda c:sum((a-b)**2 for a,b in zip(c[:3],p[:3])))


def construct() -> tuple[Image.Image,dict]:
    kf1 = approved_kf1()
    f0 = sources()["F0"]
    src,fs = kf1.load(),f0.load()
    out = Image.new("RGBA",(192,208))
    dst = out.load()
    # Same face lineage as KF1, with selected native hair/cheek row removal.
    cols = [x for x in range(61,115) if x not in DROP_COLUMNS]
    rows = [y for y in range(4,68) if y not in DROP_ROWS]
    for y,sy in enumerate(rows,4):
        for x,sx in enumerate(cols,62):
            dst[x,y] = src[sx,sy]
    # Only six hand-painted brow pixels begin tightening the expression;
    # the eyes, glasses, nose, mouth and face palette remain source pixels.
    brow_edits = []
    for x,y in ((74,35),(75,35),(80,37),(81,37),(82,37),
                (94,37),(95,37),(100,35),(101,35),(102,35)):
        r,g,b,a = dst[x,y]
        if a and r > 140 and r-g > 12:
            dst[x,y] = (14,14,16,255)
            brow_edits.append([x,y])

    # Keep the preceding posture/sleeve silhouette, then add selected F0
    # garment panels. No entire finished body is dropped into this middle pose.
    original_masks = kb2_forearm_masks()
    arm_masks = {}
    for name,dx,dy in (("left",-5,-2),("right",5,-3)):
        shifted = Image.new("L",(192,208))
        shifted.paste(original_masks[name],(dx,dy))
        arm_masks[name] = shifted
    for y in range(63,208):
        lift = 5 if y < 120 else 4 if y < 132 else 3 if y < 145 else 2 if y < 154 else 1 if y < 164 else 0
        sy = min(207,y+lift)
        for x in range(192):
            p = src[x,sy]
            if not p[3] or any(mask.getpixel((x,sy)) for mask in arm_masks.values()):
                continue
            dst[x,y] = middle_blue(p) if y < 192 else p

    # The same low forearms advance another small step; hands are separately
    # replaced with a partially formed clench rather than a full F0 fist.
    for side,dx,dy in (("left",-6,-1),("right",6,-3)):
        mask = arm_masks[side]
        hand_from_y = 135 if side == "left" else 138
        for y in range(115,hand_from_y):
            for x in range(50,145):
                if mask.getpixel((x,y)) and src[x,y][3]:
                    dst[x+dx,y+dy] = middle_blue(src[x,y])
    # Explicit hand-painted elbow/forearm surfaces connect the moving low
    # fists to the prior sleeve. Native swatches and integer polygon steps
    # form the intermediate bend; no alpha blending or geometric smoothing.
    brush = ImageDraw.Draw(out)
    for side in ("left","right"):
        brush.polygon(FOREARM_OUTLINES[side],fill=(13,18,35,255))
        brush.polygon(FOREARM_INNERS[side],fill=MID_BLUE[3])
    out.putpixel((57,112),MID_BLUE[3])

    # Local lapel and upper-sleeve fragments change the garment design,
    # while the original outer coat shape and lower leg lineage are retained.
    cloth_parts = ((68,60,123,132),(48,84,68,118),(123,84,145,118))
    for x0,y0,x1,y1 in cloth_parts:
        for sy in range(y0,y1):
            for x in range(x0,x1):
                if cloth(fs[x,sy]) and dst[x,sy+3][3] and cloth(dst[x,sy+3]):
                    dst[x,sy+3] = middle_blue(fs[x,sy])

    # Preserve KF1's shirt/button and neck identity inside the emerging
    # lapels. Hand-selected narrow interior region excludes jacket pixels.
    for y in range(63,118):
        sy = y+5
        for x in range(85,101):
            p = src[x,sy]
            if p[3] and min(p[:3]) > 90:
                dst[x,y] = p

    # The low fists form progressively: remove four selected native columns
    # from each F0 hand/cuff part (16px skin -> 12px), then register halfway.
    for item in HAND_PARTS.values():
        x0,y0,x1,y1 = item["box"]
        tx,ty = item["target"]
        cols = [x for x in range(x0,x1) if x not in item["dropCols"]]
        for y,sy in enumerate(range(y0,y1),ty):
            for x,sx in enumerate(cols,tx):
                if fs[sx,sy][3]:
                    dst[x,y] = middle_blue(fs[sx,sy])

    # Selected trouser strips broaden by one native pixel per side; soles
    # stay in KB2's approved footprint. Fill the two central native seam rows.
    leg_source = out.copy().load()
    for y in range(136,192):
        for x in range(78,116):
            if cloth(leg_source[x,y]):
                nx = x-1 if x < 96 else x+1
                dst[nx,y] = leg_source[x,y]
        for x in (95,96):
            if cloth(leg_source[x,y]):
                dst[x,y] = leg_source[x,y]
    out.paste(kf1.crop((0,192,192,208)),(0,192))
    # Retain the negative space between the source trouser legs through the
    # soles; outward native strip placement must not close it accidentally.
    for y in range(136,192):
        for x in range(94,100):
            if not src[x,y][3]:
                dst[x,y] = (0,0,0,0)

    for y in range(208):
        for x in range(192):
            if not dst[x,y][3]:
                dst[x,y] = (0,0,0,0)
    report = {"sourceKF1Sha256":KF1_SHA,"sourceF0Sha256":digest(DEST.parent.parent/"manual-pixel-art/F0.png"),
              "head":{"source":"KF1","box":[61,4,115,68],"target":HEAD_GUIDES["KF2"],
                      "removedColumns":DROP_COLUMNS,"removedRows":DROP_ROWS,"browPixels":brow_edits},
              "shirt":{"source":"KF1","targetBox":[85,63,101,118],"sourceRowOffset":5,"opaqueLightPixelsOnly":True},
              "cloth":{"source":"KF1 silhouette, selected retained F0 garment fragments",
                       "KF1LiftBands":[[63,120,5],[120,132,4],[132,145,3],[145,154,2],[154,164,1],[164,208,0]],
                       "F0DonorPartBoxes":cloth_parts,"F0DonorVerticalPlacement":3,
                       "forearmOutwardPlacement":6,"nativePaletteSubstitution":MID_BLUE,
                       "trouserOuterPlacement":1,"solesLockFromY":192},
              "hands":HAND_PARTS,"manualForearms":{"outline":FOREARM_OUTLINES,"inner":FOREARM_INNERS},
              "manualElbowSeamPixel":{"xy":[57,112],"rgba":MID_BLUE[3]},
              "legGap":{"box":[94,136,100,192],"source":"KF1 transparent pixels retained"},
              "aiGeneration":False,"globalScaling":False,"interpolation":False,
              "approvedSourcesModified":False}
    return out,report


def assess(image: Image.Image) -> dict:
    kf1,f0 = approved_kf1(),sources()["F0"]
    expected,_ = construct()
    images = {"KF1":kf1,"KF2":image,"F0":f0}
    marks = {n:landmark(i,HEAD_GUIDES[n],approximate=True) for n,i in images.items()}
    hands = {n:hand_guides(i) for n,i in images.items()}
    pairs = {f"{a}_{b}":pair(marks[a],marks[b],hands[a],hands[b]) for a,b in (("KF1","KF2"),("KF2","F0"))}
    info = metrics(image)
    checks = {"exactDocumentedEdit":image.tobytes() == expected.tobytes(),
              "canvas192x208RGBA":image.mode == "RGBA" and image.size == (192,208),
              "binaryAlpha":info["alphaValues"] == [0,255],"zeroHiddenRGB":info["hiddenRgbPixels"] == 0,
              "noClip":not info["touchesCellEdge"],"noIsolatedPixel":not info["isolatedSinglePixels"],
              "oneConnectedCharacter":len(info["connectedComponentSizes8"]) == 1,
              "noInteriorAlphaHoles":transparent_holes(image) == 0,
              "headHullMatchesGuide":list(image.getchannel("A").crop((0,0,192,63)).getbbox()) == HEAD_GUIDES["KF2"],
              "bothMotionBudgets":all(p["numericPass"] for p in pairs.values())}
    return {"status":"INDEPENDENT_VISUAL_QA_REQUIRED" if all(checks.values()) else "KF2_TECHNICAL_FAIL",
            "technicalPass":all(checks.values()),"checks":checks,"landmarks":marks,"handGuides":hands,
            "pairs":pairs,"metrics":info,"candidateRgbaSha256":hashlib.sha256(image.tobytes()).hexdigest(),
            "fullChainAllowed":False,"F0ArtApproved":False}


def write(output: Path = DEST, *, own_draft: bool = False) -> dict:
    if output.exists() and not own_draft:
        raise ValueError("refuse to overwrite KF2 evidence")
    image,provenance = construct()
    report = assess(image)
    output.mkdir(parents=True,exist_ok=own_draft)
    image.save(output/"KF2.png")
    images = [sources()["KB2"],approved_kf1(),image,sources()["F0"]]
    sheet = contact(images,["KB2 frozen","KF1 reviewed","KF2 draft","F0 retained"])
    sheet.save(output/"contact-sheet.png")
    sheet.resize((sheet.width*3,sheet.height*3),Image.Resampling.NEAREST).save(output/"contact-sheet-nearest3x.png")
    for a,b,li,ri in (("KF1","KF2",1,2),("KF2","F0",2,3)):
        Image.blend(images[li],images[ri],0.5).save(output/f"{a}-{b}-overlay.png")
    provenance["candidatePngSha256"] = digest(output/"KF2.png")
    (output/"manual-edit-provenance.json").write_text(json.dumps(provenance,indent=2)+"\n")
    (output/"landmark-report.json").write_text(json.dumps(report,indent=2)+"\n")
    return report


def resolve_review(report: dict, review: dict) -> dict:
    fresh = review.get("candidateRgbaSha256") == report["candidateRgbaSha256"]
    required = ("head","face","arms","suit","pose","alpha")
    visual = {name: all(review.get("pairs",{}).get(name,{}).get("checks",{}).get(key) == "PASS" for key in required)
              and review.get("pairs",{}).get(name,{}).get("verdict") == "PASS"
              for name in ("KF1_KF2","KF2_F0")}
    passed = report["technicalPass"] and fresh and bool(review.get("reviewer")) and all(visual.values())
    return {**report,"status":"KF1_KF2_F0_VISUAL_PASS" if passed else "MANUAL_BRIDGE_QA_FAIL",
            "independentReviewFresh":fresh,"visualPairPass":visual,"fullChainAllowed":passed,
            "F0ArtApproved":False}


def finalize(output: Path = DEST) -> dict:
    with Image.open(output/"KF2.png") as image:
        actual = assess(image.copy())
    if json.loads((output/"landmark-report.json").read_text()) != actual:
        raise ValueError("stale KF2 landmark evidence")
    review = json.loads((output/"independent-review.json").read_text())
    if review.get("candidatePngSha256") != digest(output/"KF2.png"):
        raise ValueError("review not bound to the current KF2 pixels")
    result = resolve_review(actual,review)
    (output/"static-review-resolution.json").write_text(json.dumps(result,indent=2)+"\n")
    return result


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--refresh-own-draft",action="store_true")
    p.add_argument("--finalize",action="store_true")
    args = p.parse_args()
    print((finalize() if args.finalize else write(own_draft=args.refresh_own_draft))["status"])
