"""One bounded E3 hand/stance pose; preserve prior reviewed Entry art."""
from __future__ import annotations

import json
import math
from pathlib import Path

from PIL import Image, ImageDraw

from tools.feng_entry_spec import ROOT, anchors
from tools.gate_feng_entry_e1_e2 import audit as prior_audit, resolve as prior_resolve, REVIEW
from tools.manual_feng_entry_e1_e2 import OUT as PRIOR, arm_mask, hand_box
from tools.audit_f0_v2_entry import foot_guides
from tools.manual_kf1_pixel_art import contact
from tools.prepare_transition_animation_candidate import digest, metrics
from tools.controlled_transition_k2 import transparent_holes
from tools.transition_bridge_spec import landmark, B_HEAD

OUT=ROOT/"e3-gate"
E2_SHA="387b3ac21644c5bf8a33c4cbef8e05e4fa574622cbb12d0347ad1a9b6577901d"
E3_HEAD=[63,4,113,59]


def source_frames() -> dict[str,Image.Image]:
    if not prior_resolve(prior_audit(),json.loads(REVIEW.read_text()))["E3Allowed"]:
        raise ValueError("fresh E1/E2 visual PASS required")
    if digest(PRIOR/"E2.png")!=E2_SHA: raise ValueError("reviewed E2 changed")
    with Image.open(PRIOR/"E2.png") as image:e2=image.copy()
    return {"E2":e2,"B":anchors()["Idle B"]}


def construct() -> tuple[Image.Image,dict]:
    e2=source_frames()["E2"]
    f0=anchors()["F0-v2"]
    out=e2.copy()
    dst,old=e2.load(),f0.load()
    dp=out.load()
    # Hand moves again along the same local arm arc. Use original approved
    # F0 limb pixels, sampled at nearest integer coordinates only.
    for y in range(91,120):
        for x in range(42,97):
            if dp[x,y][3] and (x<90 and y>=96):
                # Restrict erasure to the E2 moved forearm patch, preserving
                # shirt/upper arm along the shoulder and center line.
                if x < 86 and y>=99: dp[x,y]=(0,0,0,0)
    angle=-85; shift_x=-10; shift_y=-16
    c,s=math.cos(math.radians(angle)),math.sin(math.radians(angle))
    placed=0
    for ty in range(65,123):
        for tx in range(42,105):
            dx,dy=tx-56-shift_x,ty-106-shift_y
            sx=round(56+dx*c+dy*s)
            sy=round(106-dx*s+dy*c)
            if arm_mask(sx,sy) and sy < 132 and old[sx,sy][3]:
                dp[tx,ty]=old[sx,sy];placed+=1
    draw=ImageDraw.Draw(out)
    draw.polygon(((56,105),(65,103),(77,94),(84,88),(87,96),(74,108),(60,115)),fill=(13,18,35,255))
    draw.polygon(((59,105),(67,102),(80,94),(82,98),(71,108),(62,111)),fill=(40,53,113,255))
    # Lay the native hand above the sleeve surface, retaining its expression
    # of a near-lip gesture but not copying B's final finger-to-lip artwork.
    hand=f0.crop((61,132,79,153))
    for sy in range(hand.height):
        for sx in range(hand.width):
            p=hand.getpixel((sx,sy))
            if p[3]:dp[77+sx,69+sy]=p

    # Continue brow tightening using a narrow approved B brow strip. Eyes,
    # glasses and mouth are retained; final sharp expression is still pending.
    b=source_frames()["B"]
    for box in ((70,34,83,37),(92,34,104,37)):
        for y in range(box[1],box[3]):
            for x in range(box[0],box[2]):
                p=b.getpixel((x,y))
                if p[3]:dp[x,y]=p

    # Existing left leg already stepped outward in E2. The other leg now
    # moves right, row by row from its hip; no whole-body transform or growth.
    for y in range(146,208):
        for x in range(96,141):dp[x,y]=(0,0,0,0)
        shift=min(14,max(0,(y-146)*14//47))
        for x in range(96,141):
            p=e2.getpixel((x,y))
            if p[3]:dp[x+shift,y]=p

    # Move the supporting left sole/leg another 6px from E2 while keeping
    # the already-transformed thickness. The upper leg remains attached.
    for y in range(151,208):
        for x in range(49,97):dp[x,y]=(0,0,0,0)
        shift=-min(6,max(0,(y-151)*6//42))
        for x in range(49,97):
            p=e2.getpixel((x,y))
            if p[3]:dp[x+shift,y]=p
    # Erase specific orphaned pixels where the old knee/cuff no longer has
    # its source limb. Repair the few enclosed arm/trouser seam pixels with
    # existing dark suit pixels from the same local row.
    for x,y in ((49,120),(52,120),(96,157),(95,158),(95,159),(95,160),(95,161),
                (94,162),(94,163),(94,164),(93,165),(93,166)):
        dp[x,y]=(0,0,0,0)
    for x,y in ((68,99),(69,99),(67,100),(68,100),(65,101),(66,101),(67,101),
                (65,102),(61,103),(62,103),(96,150),(100,157),(100,158),(100,159)):
        if not dp[x,y][3]:dp[x,y]=(13,18,35,255)
    for y in range(208):
        for x in range(192):
            if not dp[x,y][3]:dp[x,y]=(0,0,0,0)
    return out,{"sourceE2Sha256":E2_SHA,"sourceF0":"approved native left-arm pixels",
                "forearmAngleNearest":angle,"forearmShift":[shift_x,shift_y],"forearmCopiedPixels":placed,
                "leftLegMaxShift":6,"rightLegMaxShift":14,"BPixelReuse":"two local brow/eye windows only",
                "globalScaling":False,"interpolation":False,"aiGeneration":False}


def assess(image:Image.Image)->dict:
    expected,recipe=construct()
    info=metrics(image)
    source=source_frames()["E2"]
    head=landmark(image,E3_HEAD,approximate=True)
    controls={"exactRecipe":image.tobytes()==expected.tobytes(),"nativeRGBA":image.size==(192,208) and image.mode=="RGBA",
              "binaryAlpha":info["alphaValues"]==[0,255],"zeroHiddenRGB":info["hiddenRgbPixels"]==0,
              "baseline203":info["baselineY"]==203,"headGuideStable":head["headSize"]==[50,55],
              "singleConnected":len(info["connectedComponentSizes8"])==1,"noIsolated":not info["isolatedSinglePixels"],
              "noClip":not info["touchesCellEdge"],"noNewHoles":transparent_holes(image)<=transparent_holes(source)}
    return {"technicalPass":all(controls.values()),"checks":controls,"landmark":head,
            "hands":{"left":hand_box(image,"left"),"right":hand_box(image,"right")},
            "feet":foot_guides(image),"recipe":recipe,"visualPass":None,"entryApproved":False}


def write(output:Path=OUT,*,refresh:bool=False)->dict:
    if output.exists() and not refresh:raise ValueError("refuse to overwrite Entry evidence")
    output.mkdir(parents=True,exist_ok=refresh)
    image,recipe=construct()
    image.save(output/"E3.png")
    sources=source_frames()
    sheet=contact([sources["E2"],image,sources["B"]],["E2","E3 draft","Idle B frozen"])
    sheet.save(output/"contact-sheet.png")
    sheet.resize((sheet.width*3,sheet.height*3),Image.Resampling.NEAREST).save(output/"contact-sheet-nearest3x.png")
    Image.blend(sources["E2"],image,0.5).save(output/"E2-E3-overlay.png")
    Image.blend(image,sources["B"],0.5).save(output/"E3-B-overlay.png")
    report=assess(image)
    (output/"provenance.json").write_text(json.dumps(recipe,indent=2)+"\n")
    (output/"landmarks.json").write_text(json.dumps(report,indent=2)+"\n")
    return report


if __name__=="__main__":
    import argparse
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("--refresh-own-draft",action="store_true")
    r=write(refresh=p.parse_args().refresh_own_draft)
    print("E3_TECHNICAL_PASS" if r["technicalPass"] else "E3_TECHNICAL_FAIL")
