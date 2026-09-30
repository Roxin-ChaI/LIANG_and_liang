"""Documented local pixel construction of F0-v2 directly from KF2."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from PIL import Image, ImageDraw

from tools.f0_v2_spec import OUTPUT, SOURCE, HEAD, FACE_SOURCE, FACE_TARGET, HAND_LOCKS, FEET_LOCK, sources
from tools.f0_morph_bridge import HEAD_GUIDES, hand_guides, pair
from tools.manual_kf1_pixel_art import contact
from tools.prepare_transition_animation_candidate import digest, metrics
from tools.controlled_transition_k2 import transparent_holes
from tools.transition_bridge_spec import landmark

DEST = OUTPUT / "candidate"
DROP_COLUMNS = (63, 112)
DROP_ROWS = (10, 20, 58, 62)
COLORS = {
    "head": (227, 159, 64, 255), "upperSuit": (61, 155, 232, 255),
    "pants": (150, 93, 223, 255),
}


def is_cloth(p: tuple) -> bool:
    r,g,b,a = p
    return bool(a and r < 105 and g < 120 and b > g and b > r)


def construct() -> tuple[Image.Image, dict]:
    src = sources()["KF2"]
    out = src.copy()
    sp, dp = src.load(), out.load()
    operations = []
    # Two outer hair columns and four chosen hair/neck rows only. Inner
    # expression pixels receive a single rigid -2y placement, never scaling.
    out.paste((0,0,0,0), (0,0,192,63))
    cols = [x for x in range(62,114) if x not in DROP_COLUMNS]
    rows = [y for y in range(4,63) if y not in DROP_ROWS]
    for y, sy in enumerate(rows,4):
        for x, sx in enumerate(cols,63):
            dp[x,y] = sp[sx,sy]
    operations.append({"part":"head shell", "sourceBox":[62,4,114,63],
                       "targetBox":HEAD,"removedColumns":DROP_COLUMNS,"removedRows":DROP_ROWS})

    # Register only the collar / top torso upward in small integer bands.
    # Waist, hands and feet keep their original coordinates.
    lift_bands = ((59,72,4),(72,81,3),(81,90,2),(90,99,1))
    for y0,y1,dy in lift_bands:
        for y in range(y0,y1):
            for x in range(192):
                dp[x,y] = sp[x,y+dy]
    operations.append({"part":"collar and upper torso","sourceRowOffsets":lift_bands})

    # Small local shoulder-cap additions use their own adjacent sleeve pixels.
    # No complete body donor, face transplant or new hand pose is used.
    shoulder = out.copy().load()
    for y in range(73,107):
        left = [x for x in range(40,76) if shoulder[x,y][3]]
        right = [x for x in range(119,151) if shoulder[x,y][3]]
        if left:
            x = min(left)
            dp[x-1,y] = shoulder[x,y]
            if is_cloth(shoulder[x+1,y]):
                dp[x,y] = shoulder[x+1,y]
        if right:
            x = max(right)
            dp[x+1,y] = shoulder[x,y]
            if is_cloth(shoulder[x-1,y]):
                dp[x,y] = shoulder[x-1,y]
    operations.append({"part":"shoulder caps","yRange":[73,107],"outwardPixels":1})

    # Pick existing KF2 blue swatches. Map only central jacket dark panels;
    # keep native outlines and shading distinctions, not a flat color fill.
    blue = sorted({p for p in src.get_flattened_data() if is_cloth(p) and p[2] >= p[1]*1.6 and 50 <= sum(p[:3]) <= 230},
                  key=lambda p:sum(p[:3]))
    def suit_blue(p: tuple, minimum: int) -> tuple:
        if not is_cloth(p) or sum(p[:3]) < 40 or sum(p[:3]) >= minimum:
            return p
        return min(blue, key=lambda q:abs(sum(q[:3])-minimum))
    for y in range(75,137):
        for x in range(76,117):
            dp[x,y] = suit_blue(dp[x,y],95)
    operations.append({"part":"basic jacket","box":[76,75,117,137],
                       "source":"KF2 blue swatches","minInteriorBrightnessSum":95})

    # Strengthen each existing straight trouser leg by inserting up to three
    # native cloth columns. Inner gap, stride, knees and sole positions stay.
    # No crumpled F0 pants or wide Idle stance is copied.
    for y in range(138,192):
        extra = 3 if y < 163 else 2 if y < 177 else 1 if y < 187 else 0
        for x in range(76,96):
            sx = min(95, x+extra) if x < 87 else x
            p = sp[sx,y]
            if p[3] and is_cloth(p):
                dp[x,y] = suit_blue(p,105)
        for x in range(99,120):
            sx = max(99,x-extra) if x >= 108 else x
            p = sp[sx,y]
            if p[3] and is_cloth(p):
                dp[x,y] = suit_blue(p,105)
    operations.append({"part":"straight trousers","bands":[[138,163,3],[163,177,2],[177,187,1],[187,192,0]],
                       "leftInsertionColumn":86,"rightInsertionColumn":108,"source":"KF2 only"})

    # The existing right thigh has a two-column transparent indentation.
    # Local thickening encloses it; draw that specific seam with its adjacent
    # native trouser color rather than leaving a hole inside the fabric.
    seam_pixels = []
    for y in range(143,157):
        for x in (106,107):
            if not dp[x,y][3]:
                dp[x,y] = dp[108,y]
                seam_pixels.append([x,y])
    operations.append({"part":"right thigh insertion seam","pixels":seam_pixels,
                       "donorColumn":108,"sameRow":True})

    # A few hand-authored seam strokes give the emerging jacket continuous
    # side shaping, using existing darkest cloth colors, without Idle detail.
    brush = ImageDraw.Draw(out)
    outline = sp[80,120]
    seam_strokes = [((79,112),(78,119),(80,127)), ((111,112),(113,120),(111,128))]
    for stroke in seam_strokes:
        brush.line(stroke, fill=outline, width=1)
    operations.append({"part":"manual side seams","strokes":seam_strokes,"rgba":outline})

    # Reapply explicit locks last, including transparent bytes at their edges.
    out.paste(src.crop(FACE_SOURCE), (FACE_TARGET[0],FACE_TARGET[1]))
    for box in [*HAND_LOCKS, FEET_LOCK]:
        out.paste(src.crop(box),(box[0],box[1]))
    for y in range(208):
        for x in range(192):
            if not dp[x,y][3]:
                dp[x,y] = (0,0,0,0)
    return out, {"method":"KF2 native pixels plus explicit local edits", "operations":operations,
                 "expression":{"source":FACE_SOURCE,"target":FACE_TARGET,"byteIdentical":True},
                 "inPlaceLocks":[*HAND_LOCKS,FEET_LOCK],
                 "aiGeneration":False,"wholeCharacterScaling":False,"interpolation":False,
                 "newBridgeFrames":0,"retiredF0PixelsUsed":0,"BPixelDonorsUsed":0}


def assess(image: Image.Image) -> dict:
    source = sources()["KF2"]
    expected, recipe = construct()
    lm = {"KF2":landmark(source,HEAD_GUIDES["KF2"],approximate=True),
          "F0-v2":landmark(image,HEAD,approximate=True)}
    hands = {"KF2":hand_guides(source),"F0-v2":hand_guides(image)}
    delta = pair(lm["KF2"],lm["F0-v2"],hands["KF2"],hands["F0-v2"])
    info = metrics(image)
    lock_boxes = [*HAND_LOCKS,FEET_LOCK]
    locks = [{"box":box,"byteIdentical":source.crop(box).tobytes() == image.crop(box).tobytes(),
              "referenceSha256":hashlib.sha256(source.crop(box).tobytes()).hexdigest(),
              "actualSha256":hashlib.sha256(image.crop(box).tobytes()).hexdigest()} for box in lock_boxes]
    expression = source.crop(FACE_SOURCE).tobytes() == image.crop(FACE_TARGET).tobytes()
    checks = {
        "nativeRGBA":image.size == (192,208) and image.mode == "RGBA",
        "documentedPixels":image.tobytes() == expected.tobytes(),
        "expressionByteIdentical":expression,"handsFeetByteIdentical":all(x["byteIdentical"] for x in locks),
        "headGuideHull":list(image.getchannel("A").crop((0,0,192,59)).getbbox()) == HEAD,
        "geometryBudget":delta["numericPass"],"completedHeadSize":lm["F0-v2"]["headSize"] == [50,55],
        "broadBodyBand":96 <= lm["F0-v2"]["bodyWidth"] <= 104,
        "binaryAlpha":info["alphaValues"] == [0,255],"zeroHiddenRGB":not info["hiddenRgbPixels"],
        "noClip":not info["touchesCellEdge"],"oneCharacter":len(info["connectedComponentSizes8"]) == 1,
        "noIsolatedPixels":not info["isolatedSinglePixels"],"noNewAlphaHoles":transparent_holes(image) <= transparent_holes(source),
        "paletteFromKF2":set(image.get_flattened_data()) <= set(source.get_flattened_data()),
    }
    changed = [(x,y) for y in range(208) for x in range(192) if image.getpixel((x,y)) != source.getpixel((x,y))]
    return {"status":"STATIC_VISUAL_REVIEW_REQUIRED" if all(checks.values()) else "F0_V2_TECHNICAL_FAIL",
            "technicalPass":all(checks.values()),"checks":checks,"landmarks":lm,"delta":delta,
            "hands":hands,"lockedRegions":locks,"expressionByteIdentical":expression,
            "metrics":info,"changedPixels":len(changed),"rgbaSha256":hashlib.sha256(image.tobytes()).hexdigest(),
            "recipe":recipe,"morphApproved":False,"entryAuditAllowed":False,"humanApproval":"PENDING"}


def write(output: Path = DEST, *, refresh_draft: bool = False) -> dict:
    if output.exists() and not (refresh_draft and (output/"provenance.json").exists()):
        raise ValueError("refuse to overwrite unrelated evidence")
    candidate, recipe = construct()
    report = assess(candidate)
    source = sources()["KF2"]
    output.mkdir(parents=True,exist_ok=refresh_draft)
    candidate.save(output/"F0-v2.png")
    sheet = contact([source,candidate],["KF2 frozen","F0-v2 candidate"])
    sheet.save(output/"contact-sheet.png")
    sheet.resize((sheet.width*3,sheet.height*3),Image.Resampling.NEAREST).save(output/"contact-sheet-nearest3x.png")
    Image.blend(source,candidate,0.5).save(output/"KF2-F0-v2-overlay.png")
    diff = Image.new("RGBA",(192,208))
    semantic = Image.new("RGBA",(192,208))
    counts = dict.fromkeys(COLORS,0)
    for y in range(208):
        for x in range(192):
            if source.getpixel((x,y)) != candidate.getpixel((x,y)):
                diff.putpixel((x,y),(255,64,64,255))
                part = "head" if y < 59 else "upperSuit" if y < 138 else "pants"
                semantic.putpixel((x,y),COLORS[part])
                counts[part] += 1
    diff.save(output/"difference-mask.png")
    semantic.save(output/"semantic-change-mask.png")
    (output/"semantic-change-legend.json").write_text(json.dumps({"colors":COLORS,"changedPixelsByRegion":counts,
        "meaning":"spatial edit classification, not automatic expression or garment semantics","expressionLock":"exact source crop moved 2px upward"},indent=2)+"\n")
    recipe.update(sourceSha256=digest(SOURCE),
                  outputSha256=digest(output/"F0-v2.png"))
    (output/"provenance.json").write_text(json.dumps(recipe,indent=2)+"\n")
    (output/"landmark-report.json").write_text(json.dumps(report,indent=2)+"\n")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--refresh-draft",action="store_true")
    print(write(refresh_draft=parser.parse_args().refresh_draft)["status"])
