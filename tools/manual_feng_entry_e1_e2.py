"""Local native-pixel hand/arm and stance edits for E1/E2 Entry drafts."""
from __future__ import annotations

import json
import math
from pathlib import Path

from PIL import Image, ImageDraw

from tools.feng_entry_spec import ROOT, F0_SHA, anchors
from tools.manual_kf1_pixel_art import contact
from tools.prepare_transition_animation_candidate import digest, metrics
from tools.controlled_transition_k2 import transparent_holes
from tools.transition_bridge_spec import landmark
from tools.audit_f0_v2_entry import foot_guides

OUT = ROOT / "e1-e2"
FRAMES = {"E1":{"degrees":-32,"armShiftX":-15,"browStep":1,"leftStep":0,"rightHandShift":[0,0]},
          "E2":{"degrees":-65,"armShiftX":-17,"browStep":2,"leftStep":8,"rightHandShift":[4,-2]}}
LEFT_ARM_SOURCE = [40,119,81,156]
LEFT_ARM_CLEAR = [40,119,81,156]
LEFT_LEG_X = [68,98]
SOURCE_HEAD = [63,4,113,59]


def _skin(pixel: tuple) -> bool:
    r,g,b,a = pixel
    return bool(a and r>140 and r-g>12 and g-b>5)


def hand_box(image: Image.Image, side: str) -> list[int]:
    # Region excludes facial skin even after the viewer-left hand approaches.
    area = (35,90,100,155) if side == "left" else (109,120,150,157)
    pixels = [(x,y) for y in range(area[1],area[3]) for x in range(area[0],area[2]) if _skin(image.getpixel((x,y)))]
    if not pixels: raise ValueError("hand disappeared")
    return [min(x for x,y in pixels),min(y for x,y in pixels),max(x for x,y in pixels)+1,max(y for x,y in pixels)+1]


def arm_mask(x: int,y: int) -> bool:
    # Explicit source-side forearm polygon, excluding the shirt/torso.
    if not (40 <= x < 81 and 119 <= y < 156): return False
    return x < 80 if y < 137 else x < 78


def _place_rotated_forearm(out: Image.Image, original: Image.Image, degrees: int, shift_x: int) -> int:
    """Inverse-map only this masked limb, using nearest original RGBA pixels."""
    dst, src = out.load(), original.load()
    theta = math.radians(degrees)
    c,s = math.cos(theta),math.sin(theta)
    changed = 0
    for ty in range(87,153):
        for tx in range(34,105):
            dx,dy = tx - 56 - shift_x, ty - 106
            sx = round(56 + dx*c + dy*s)
            sy = round(106 - dx*s + dy*c)
            if arm_mask(sx,sy) and src[sx,sy][3]:
                dst[tx,ty] = src[sx,sy]
                changed += 1
    return changed


def _move_left_leg(out: Image.Image, original: Image.Image, maximum: int) -> None:
    if maximum == 0: return
    dst,src = out.load(),original.load()
    # Copy only the lower left leg; its hip stays planted while the lower leg
    # and shoe take an 8-pixel outward step over forty source rows.
    for y in range(151,208):
        x0 = 76 if y < 156 else LEFT_LEG_X[0]
        for x in range(x0,LEFT_LEG_X[1]):
            dst[x,y] = (0,0,0,0)
        shift = -min(maximum,max(0,(y-151)*maximum//41))
        for x in range(x0,LEFT_LEG_X[1]):
            p = src[x,y]
            if p[3]: dst[x+shift,y] = p


def construct(name: str) -> tuple[Image.Image,dict]:
    if name not in FRAMES: raise ValueError("E1 or E2 only")
    params = FRAMES[name]
    original = anchors()["F0-v2"]
    out = original.copy()
    dst,src = out.load(),original.load()
    # Source forearm/hand pixels are removed as a *part*, not a broad cutout
    # through the shirt or torso. The static shoulder cap remains unchanged.
    for y in range(LEFT_ARM_CLEAR[1],LEFT_ARM_CLEAR[3]):
        for x in range(LEFT_ARM_CLEAR[0],LEFT_ARM_CLEAR[2]):
            if arm_mask(x,y): dst[x,y]=(0,0,0,0)
    if name == "E1":
        # Two explicit jacket polygons bridge the new elbow bend to its cuff.
        # They use native KF2/F0 sleeve colors and stay inside the same limb.
        bridge=ImageDraw.Draw(out)
        bridge.polygon(((54,109),(64,111),(77,119),(80,128),(72,134),(59,128),(52,118)),
                       fill=(13,18,35,255))
        bridge.polygon(((56,112),(64,114),(74,121),(75,128),(68,131),(58,125)),
                       fill=(40,53,113,255))
    placed = _place_rotated_forearm(out,original,params["degrees"],params["armShiftX"])
    if name == "E1":
        for x,y in ((78,119),(79,119),(78,120),(79,120),(79,121),(79,122),(79,123),(79,130),(63,131)):
            if not dst[x,y][3]: dst[x,y]=(13,18,35,255)
    # Native jacket palette for two small elbow bridge stitches, which tie
    # the turned lower sleeve back to the stationary upper arm.
    seam_color = src[60,116]
    draw = ImageDraw.Draw(out)
    for x,y in ((46,119),(47,119),(48,118)):
        if not dst[x,y][3]: draw.point((x,y),fill=seam_color)

    # Only selected eyebrow positions tighten: E1 begins at outer brows,
    # E2 adds inner pixels. Glasses, face outline and skull are unchanged.
    brow_positions = ((72,35),(73,35),(99,35),(100,35))
    if params["browStep"] == 2:
        brow_positions += ((76,36),(77,36),(95,36),(96,36),(81,37),(93,37))
    face_edits=[]
    face_ink=(22,20,26,255)
    for x,y in brow_positions:
        if dst[x,y][3] and _skin(dst[x,y]):
            dst[x,y]=face_ink
            face_edits.append([x,y])

    if name == "E2":
        # Right low fist begins to turn inward. The cuff is translated only
        # two rows up and four columns out, using its exact original colors.
        box=(112,133,133,154)
        part=original.crop(box)
        for y in range(box[1],box[3]):
            for x in range(box[0],box[2]):
                if 113 <= x <= 132 and y >= 134: dst[x,y]=(0,0,0,0)
        hand_rows=[y for y in range(part.height) if box[1]+y not in (146,148)]
        for target_y,y in enumerate(hand_rows):
            for x in range(part.width):
                p=part.getpixel((x,y))
                if p[3]: dst[box[0]+x+4,box[1]+target_y-2]=p
        _move_left_leg(out,original,params["leftStep"])

    for y in range(208):
        for x in range(192):
            if not dst[x,y][3]: dst[x,y]=(0,0,0,0)
    recipe={"sourceF0Sha256":F0_SHA,"frame":name,"localForearmNearestAngle":params["degrees"],
            "forearmShiftX":params["armShiftX"],"forearmSourceMask":"explicit LEFT_ARM_SOURCE polygon",
            "forearmCopiedPixels":placed,"browPixels":face_edits,"leftFootOutwardPx":params["leftStep"],
            "rightHandShift":params["rightHandShift"],"rightHandLocalRowsRemoved":[146,148] if name=="E2" else [],
            "globalScaling":False,
            "wholeCharacterRotation":False,"aiGeneration":False,"colorInterpolation":False}
    return out,recipe


def assess(name: str,image: Image.Image) -> dict:
    expected,recipe=construct(name)
    old=anchors()["F0-v2"]
    info=metrics(image)
    head=landmark(image,SOURCE_HEAD,approximate=True)
    baseline=landmark(old,SOURCE_HEAD,approximate=True)
    checks={"documentedPixels":expected.tobytes()==image.tobytes(),
            "nativeRGBA":image.mode=="RGBA" and image.size==(192,208),
            "binaryAlpha":info["alphaValues"]==[0,255],"zeroHiddenRGB":info["hiddenRgbPixels"]==0,
            "singleCharacter":len(info["connectedComponentSizes8"])==1,
            "noIsolated":not info["isolatedSinglePixels"],"noClipping":not info["touchesCellEdge"],
            "baseline203":info["baselineY"]==203,"headSizeFixed":head["headSize"]==baseline["headSize"],
            "noNewAlphaHoles":transparent_holes(image)<=transparent_holes(old),
            "sameSkullContour":image.crop((0,0,192,32)).tobytes()==old.crop((0,0,192,32)).tobytes()}
    return {"status":"VISUAL_REVIEW_REQUIRED" if all(checks.values()) else "ENTRY_TECHNICAL_FAIL",
            "technicalPass":all(checks.values()),"checks":checks,"metrics":info,"landmark":head,
            "hands":{"left":hand_box(image,"left"),"right":hand_box(image,"right")},
            "feet":foot_guides(image),"recipe":recipe,"artApproved":False}


def write(output: Path = OUT, *, own_draft: bool = False) -> dict:
    if output.exists() and not own_draft: raise ValueError("refuse to overwrite E1/E2 evidence")
    output.mkdir(parents=True,exist_ok=own_draft)
    original=anchors()["F0-v2"]
    images={"F0-v2":original}
    reports={}
    for name in ("E1","E2"):
        image,recipe=construct(name)
        image.save(output/f"{name}.png")
        reports[name]=assess(name,image)
        (output/f"{name}-provenance.json").write_text(json.dumps(recipe,indent=2)+"\n")
    images.update({n:Image.open(output/f"{n}.png").copy() for n in ("E1","E2")})
    sheet=contact(list(images.values()),list(images))
    sheet.save(output/"contact-sheet.png")
    sheet.resize((sheet.width*3,sheet.height*3),Image.Resampling.NEAREST).save(output/"contact-sheet-nearest3x.png")
    for a,b in (("F0-v2","E1"),("E1","E2")):
        Image.blend(images[a],images[b],0.5).save(output/f"{a}-{b}-overlay.png")
    (output/"landmarks.json").write_text(json.dumps(reports,indent=2)+"\n")
    return reports


if __name__=="__main__":
    import argparse
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--refresh-own-draft",action="store_true")
    r=write(own_draft=p.parse_args().refresh_own_draft)
    print({n:r[n]["status"] for n in r})
