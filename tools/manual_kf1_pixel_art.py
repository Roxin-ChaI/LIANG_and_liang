"""Hand-authored native pixel edit recipe for the first KB2 -> F0 bridge."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from PIL import Image, ImageDraw

from tools.f0_morph_bridge import OUTPUT, HEAD_GUIDES, hand_guides, pair, sources
from tools.prepare_transition_animation_candidate import digest, metrics
from tools.transition_bridge_spec import landmark
from tools.controlled_transition_k2 import transparent_holes

DEST = OUTPUT / "kf1"
DROP_COLUMNS = (62, 113)
DROP_ROWS = (14, 27, 57, 67)
LEFT_FOREARM = ((62,119),(75,122),(82,133),(85,139),(85,155),(73,155),(73,139),(61,129))
RIGHT_FOREARM = ((120,121),(134,119),(136,132),(124,140),(118,144),(118,161),(104,161),(104,142),(113,134))
# These are individually chosen cloth swatches, never interpolated colors.
PALETTE = ((16,20,39,255),(23,29,54,255),(28,36,69,255),
           (33,43,85,255),(39,51,97,255))


def cloth(pixel: tuple) -> bool:
    r,g,b,a = pixel
    return bool(a and r < 75 and g < 85 and b > r and b > g)


def blue(pixel: tuple) -> tuple:
    if not cloth(pixel) or sum(pixel[:3]) < 32:
        return pixel
    return PALETTE[min(4, max(0, (pixel[2]-20)//15))]


def masks() -> dict[str, Image.Image]:
    source = sources()["KB2"]
    result = {}
    for name, polygon in (("left",LEFT_FOREARM),("right",RIGHT_FOREARM)):
        image = Image.new("L",(192,208))
        ImageDraw.Draw(image).polygon(polygon,fill=255)
        # Lower hand rectangles overlap the trousers in KB2's narrow pose.
        # Select hand/cuff colors and the immediately adjacent black outline,
        # keeping the original navy trouser pixels out of the moving parts.
        boundary = 137 if name == "left" else 141
        for y in range(boundary,164):
            for x in range(60,138):
                if not image.getpixel((x,y)):
                    continue
                color = source.getpixel((x,y))
                if cloth(color):
                    near_skin = any((lambda c:c[3] and c[0]>140 and c[0]-c[1]>12 and c[1]-c[2]>5)(source.getpixel((nx,ny)))
                                    for ny in range(y-1,y+2) for nx in range(x-1,x+2))
                    if sum(color[:3]) >= 45 or not near_skin:
                        image.putpixel((x,y),0)
        result[name] = image
    return result


def construct() -> tuple[Image.Image, dict]:
    source = sources()["KB2"]
    result = Image.new("RGBA",(192,208),(0,0,0,0))
    src,dst = source.load(),result.load()
    limbs = masks()
    left,right = limbs["left"].load(),limbs["right"].load()

    # Remove only these six manually selected hair/cheek rows and columns.
    # Eye/glasses rows remain original KB2 bytes, with relaxed expression.
    cols = [x for x in range(60,116) if x not in DROP_COLUMNS]
    rows = [y for y in range(4,72) if y not in DROP_ROWS]
    for ty,sy in enumerate(rows,4):
        for tx,sx in enumerate(cols,61):
            dst[tx,ty] = src[sx,sy]

    # Upper posture straightens four native rows. Taper the row placements
    # through trousers; approved ankles/feet are never moved or recolored.
    for y in range(68,208):
        lift = 4 if y < 126 else 3 if y < 138 else 2 if y < 151 else 1 if y < 164 else 0
        sy = min(207,y+lift)
        for x in range(192):
            if left[x,sy] or right[x,sy]:
                continue
            pixel = src[x,sy]
            if not pixel[3]:
                continue
            nx = x-1 if y < 140 and x < 85 else x+1 if y < 140 and x >= 104 else x
            dst[nx,y] = blue(pixel) if y < 140 else pixel
        # Two explicit native seam columns connect the moved side panels to
        # the fixed shirt panel; otherwise outward placement leaves alpha gaps.
        if y < 140:
            for seam_x in (84,104):
                if src[seam_x,sy][3] and not (left[seam_x,sy] or right[seam_x,sy]):
                    dst[seam_x,y] = blue(src[seam_x,sy])

    # Low original forearms and hands follow bounded outward/upward paths.
    for side,mask,dx,dy in (("left",left,-5,-2),("right",right,5,-3)):
        for y in range(119,164):
            for x in range(60 if side == "left" else 104,87 if side == "left" else 138):
                if mask[x,y] and src[x,y][3]:
                    dst[x+dx,y+dy] = blue(src[x,y])
    # Hand-selected vacated left-elbow cloth repair. Keep its original native
    # cloth colors under the moving forearm, with two explicit outline pixels.
    for y in range(115,138):
        lift = 4 if y < 126 else 3
        for x in range(60,85):
            original = src[x,y+lift]
            if not dst[x,y][3] and cloth(original):
                dst[x,y] = blue(original)
    dst[70,136] = (12,15,30,255)
    dst[71,137] = (12,15,30,255)

    # First tailoring phase: repaint only the upper two chest cloth panels;
    # the lower dark KB2 jacket remains. Clip every brush to existing cloth.
    brush = Image.new("L",(192,208))
    d = ImageDraw.Draw(brush)
    d.polygon(((66,84),(78,75),(84,82),(84,96),(68,96)),fill=255)
    d.polygon(((105,80),(112,76),(122,86),(120,96),(105,97)),fill=255)
    brush_pixels = brush.load()
    painted = 0
    for y in range(74,98):
        for x in range(64,124):
            if brush_pixels[x,y] and cloth(dst[x,y]):
                dst[x,y] = PALETTE[2 if x < 96 else 3]
                painted += 1
    # Explicit pixel lines establish the first lapel notch without replacing
    # the torso with a finished Feng donor.
    seams = ((78,75),(69,83),(73,87),(70,93),(77,104))
    seams_right = ((111,76),(120,85),(116,89),(119,94),(111,104))
    line = Image.new("L",(192,208))
    ld = ImageDraw.Draw(line)
    ld.line(seams,fill=255,width=1)
    ld.line(seams_right,fill=255,width=1)
    for y in range(74,106):
        for x in range(65,124):
            if line.getpixel((x,y)) and cloth(dst[x,y]):
                dst[x,y] = (12,15,30,255)
    # A black source cuff-outline pixel is vacated by the forearm placement.
    # Remove this one detached remnant explicitly, not by a cleanup filter.
    dst[123,140] = (0,0,0,0)
    # Every transparent texel remains canonical zero RGBA.
    for y in range(208):
        for x in range(192):
            if not dst[x,y][3]:
                dst[x,y] = (0,0,0,0)
    result.paste(source.crop((0,164,192,208)),(0,164))
    report = {"source": "frozen KB2", "sourceRgbaSha256":hashlib.sha256(source.tobytes()).hexdigest(),
              "headEdit": {"sourceBox":[60,4,116,72],"targetBox":HEAD_GUIDES["KF1"],
                           "removedSourceColumns":DROP_COLUMNS,"removedSourceRows":DROP_ROWS,
                           "faceExpressionEdits":0,"resampling":False},
              "body": {"liftBands":[[68,126,4],[126,138,3],[138,151,2],[151,164,1],[164,208,0]],
                       "outerClothColumnsShift":1,"seamColumns":[84,104],"feetLockFromY":164},
              "arms": {"left":{"sourcePolygon":LEFT_FOREARM,"shift":[-5,-2]},
                       "right":{"sourcePolygon":RIGHT_FOREARM,"shift":[5,-3]}},
              "cloth": {"palette":PALETTE,"upperPanelBrushPixels":painted,
                        "leftSeam":seams,"rightSeam":seams_right,
                        "lowerJacket": "source structure retained; no finished Feng torso copy"},
              "manualOutlineRepair": [{"xy":[123,140],"rgba":[0,0,0,0],"reason":"vacated detached cuff outline"},
                                      {"xy":[70,136],"rgba":[12,15,30,255]},
                                      {"xy":[71,137],"rgba":[12,15,30,255]}],
              "vacatedElbowRepair": {"box":[60,115,85,138],"onlyClearPixels":True,"donor":"KB2 original cloth rows y+4/y+3"},
              "aiGeneration":False,"globalScaling":False,"interpolation":False,
              "effects":False,"approvedSourcesModified":False}
    return result,report


def assess(candidate: Image.Image) -> dict:
    source = sources()["KB2"]
    expected,_ = construct()
    left = landmark(source,HEAD_GUIDES["KB2"],approximate=True)
    right = landmark(candidate,HEAD_GUIDES["KF1"],approximate=True)
    lh,rh = hand_guides(source),hand_guides(candidate)
    delta = pair(left,right,lh,rh)
    info = metrics(candidate)
    checks = {"exactDocumentedEdit":candidate.tobytes() == expected.tobytes(),
              "canvas192x208RGBA":candidate.mode == "RGBA" and candidate.size == (192,208),
              "feetByteIdenticalFrom164":candidate.crop((0,164,192,208)).tobytes() == source.crop((0,164,192,208)).tobytes(),
              "binaryAlpha":info["alphaValues"] == [0,255],"zeroHiddenRGB":info["hiddenRgbPixels"] == 0,
              "noClip":not info["touchesCellEdge"],"noIsolatedPixel":not info["isolatedSinglePixels"],
              "oneConnectedCharacter":len(info["connectedComponentSizes8"]) == 1,
              "noNewInteriorAlphaHoles":transparent_holes(candidate) <= transparent_holes(source),
              "headHullMatchesGuide":list(candidate.getchannel("A").crop((0,0,192,68)).getbbox()) == HEAD_GUIDES["KF1"],
              "motionBudget":delta["numericPass"]}
    return {"status":"INDEPENDENT_VISUAL_QA_REQUIRED" if all(checks.values()) else "KF1_TECHNICAL_FAIL",
            "checks":checks,"technicalPass":all(checks.values()),"KB2":left,"KF1":right,
            "handGuides":{"KB2":lh,"KF1":rh},"delta":delta,"metrics":info,
            "candidateRgbaSha256":hashlib.sha256(candidate.tobytes()).hexdigest(),
            "KF2Allowed":False,"F0ArtApproved":False}


def contact(images: list[Image.Image], names: list[str]) -> Image.Image:
    out = Image.new("RGBA",(192*len(images),230),(28,28,32,255))
    draw = ImageDraw.Draw(out)
    for n,(image,name) in enumerate(zip(images,names)):
        draw.text((192*n+4,3),name,fill="white")
        out.alpha_composite(image,(192*n,20))
    return out


def write(output: Path = DEST, *, own_draft: bool = False) -> dict:
    if output.exists() and not own_draft:
        raise ValueError("refuse to overwrite KF1 evidence")
    image,provenance = construct()
    report = assess(image)
    output.mkdir(parents=True,exist_ok=own_draft)
    source = sources()["KB2"]
    image.save(output/"KF1.png")
    sheet = contact([source,image,sources()["F0"]],["KB2 frozen","KF1 draft","F0 retained (pending)"])
    sheet.save(output/"contact-sheet.png")
    sheet.resize((sheet.width*3,sheet.height*3),Image.Resampling.NEAREST).save(output/"contact-sheet-nearest3x.png")
    Image.blend(source,image,0.5).save(output/"KB2-KF1-overlay.png")
    difference = Image.new("RGBA",(192,208))
    difference.putdata([(255,64,64,255) if a != b else (0,0,0,0)
                        for a,b in zip(source.get_flattened_data(),image.get_flattened_data())])
    difference.save(output/"difference-mask.png")
    provenance["candidatePngSha256"] = digest(output/"KF1.png")
    (output/"manual-edit-provenance.json").write_text(json.dumps(provenance,indent=2)+"\n")
    (output/"landmark-report.json").write_text(json.dumps(report,indent=2)+"\n")
    return report


def resolve_review(report: dict, review: dict) -> dict:
    fresh = review.get("candidateRgbaSha256") == report["candidateRgbaSha256"]
    required = ("face","head","arms","suit","legs","alpha")
    visual = all(review.get("checks",{}).get(key) == "PASS" for key in required)
    passed = report["technicalPass"] and fresh and visual and bool(review.get("reviewer")) and review.get("verdict") == "PASS"
    return {**report,"status":"KB2_KF1_VISUAL_PASS" if passed else "MANUAL_BRIDGE_QA_FAIL",
            "independentReviewFresh":fresh,"visualPass":visual,"KF2Allowed":passed}


def finalize(output: Path = DEST) -> dict:
    with Image.open(output/"KF1.png") as image:
        candidate = image.copy()
    actual = assess(candidate)
    if json.loads((output/"landmark-report.json").read_text()) != actual:
        raise ValueError("stale KF1 landmark evidence")
    review = json.loads((output/"independent-review.json").read_text())
    if review.get("candidatePngSha256") != digest(output/"KF1.png"):
        raise ValueError("visual review is not bound to current KF1 PNG")
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
