"""K1-only references/extraction/QA. NO sprite resize, re-centering or anatomical repair."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil

from PIL import Image, ImageDraw

from tools.prepare_manual_transition_endpoints import pixel_overlay
from tools.prepare_transition_animation_candidate import digest, harden_alpha
from tools.specify_transition_keyframes import approved_inputs
from tools.validate_transition_k1 import assess

SLOT = (416, 408, 608, 616)


def native_geometry(image: Image.Image) -> dict:
    """Native-source diagnostics only; NEVER a registration or anatomical mask."""
    alpha = image.getchannel("A")
    box = alpha.getbbox()
    hard_box = alpha.point(lambda value: 255 if value >= 128 else 0).getbbox()
    histogram = alpha.histogram()
    return {"coordinateSpace":"native source; not192x208 runtime coordinates",
            "sourceSize":list(image.size), "sourceMode":image.mode,
            "alphaBbox":list(box) if box else None,
            "alphaBboxSize":[box[2]-box[0],box[3]-box[1]] if box else None,
            "lowestNonzeroAlphaY":box[3]-1 if box else None,
            "hardAlphaBboxAt128":list(hard_box) if hard_box else None,
            "hardAlphaBboxSizeAt128":[hard_box[2]-hard_box[0],hard_box[3]-hard_box[1]] if hard_box else None,
            "lowestHardAlphaY":hard_box[3]-1 if hard_box else None,
            "partialAlphaPixels":sum(histogram[1:255]),
            "alphaUniqueValueCount":sum(bool(n) for n in histogram),
            "warning":"whole-foreground bbox is not anatomical head/body; no fitting performed"}


def prepare_reference(path: Path) -> None:
    if path.exists():
        raise ValueError("refuse to overwrite reference")
    image = Image.new("RGBA", (1024, 1024))
    original = approved_inputs()[0][2]
    image.paste(original, SLOT[:2])
    assert image.crop(SLOT).tobytes() == original.tobytes()
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path)


def fixed_crop(image: Image.Image) -> tuple[Image.Image | None, dict]:
    if image.mode != "RGBA":
        raise ValueError("RGBA required; no background keying")
    if image.size not in ((192,208), (1024,1024)):
        return None, {"status":"SOURCE_LAYOUT_FAIL", "reason":"unexpected native dimensions; no whole-character resizing permitted", "sourceSize":list(image.size),
                      "resizeOperations":0,"integerRegistrationOperations":0,"alphaHardenedPixels":0}
    clean, partial = harden_alpha(image)
    slot = (0,0,192,208) if image.size == (192,208) else SLOT
    alpha = clean.getchannel("A")
    outside = alpha.copy()
    ImageDraw.Draw(outside).rectangle((slot[0],slot[1],slot[2]-1,slot[3]-1),fill=0)
    note = {"sourceSize":list(image.size), "fixedCrop":list(slot), "resizeOperations":0,
            "integerRegistrationOperations":0, "alphaHardenedPixels":partial,
            "alphaPolicy":"threshold128, retained RGB unchanged, transparent RGB zero; no shape correction",
            "sourceAlphaBbox":list(alpha.getbbox()) if alpha.getbbox() else None,
            "opaquePixelsOutsideFixedSlot":sum(outside.histogram()[1:])}
    if outside.getbbox():
        return None, {**note,"status":"SOURCE_LAYOUT_FAIL","reason":"foreground outside canonical slot; refuse clipping, recentering or scaling"}
    return clean.crop(slot), note


def rejected_overlay(canonical: Image.Image, original: Image.Image) -> Image.Image:
    """QA-only fixed edit-target coordinates. No output may be used as a K1 cell."""
    size = (max(original.width,SLOT[2]),max(original.height,SLOT[3]))
    expected, observed = Image.new("RGBA",size), Image.new("RGBA",size)
    expected.paste(canonical,SLOT[:2])
    hard_source,_ = harden_alpha(original)
    observed.paste(hard_source,(0,0))
    overlay = Image.new("RGBA",size)
    overlay.putdata([(255,255,255,255) if a == b and a[3]
                     else (0,220,255,255) if a[3] and not b[3]
                     else (255,0,220,255) if b[3] and not a[3]
                     else (255,220,0,255) if a != b else (0,0,0,0)
                     for a,b in zip(expected.get_flattened_data(),observed.get_flattened_data())])
    return overlay


def rejected_detail_sheet(canonical: Image.Image, original: Image.Image) -> Image.Image:
    """Native-scale QA display crop only. Full rejected source remains separately retained."""
    box = native_geometry(original)["hardAlphaBboxAt128"]
    detail = original.crop((max(0,box[0]-8),max(0,box[1]-8),
                            min(original.width,box[2]+8),min(original.height,box[3]+8))) if box else original
    width, height = max(192,detail.width), max(208,detail.height)
    sheet = Image.new("RGBA",(width*2,height+44),(35,35,35,255))
    sheet.alpha_composite(canonical,(0,28))
    sheet.alpha_composite(detail,(width,28))
    draw = ImageDraw.Draw(sheet)
    draw.text((3,3),"A / native200px",fill="white")
    draw.text((width+3,3),"REJECTED / no resampling",fill="white")
    draw.text((3,height+30),"QA display crop only; NOT a K1 cell",fill="white")
    return sheet


def prepare(source: Path, output: Path) -> dict:
    if output.exists():
        raise ValueError("refuse to overwrite K1 candidate")
    with Image.open(source) as image:
        original = image.copy()
    cell, processing = fixed_crop(original)
    qa = output / "qa"
    qa.mkdir(parents=True)
    shutil.copyfile(source, output / "raw-native.png")
    canonical_path, canonical = approved_inputs()[0][1:]
    shutil.copyfile(canonical_path, output / "A.png")
    if cell is not None:
        cell.save(output / "K1.png")
        overlay = pixel_overlay(canonical,cell)
        overlay.save(qa / "alpha-and-pixel-overlay.png")
        sheet = Image.new("RGBA",(576,240),(35,35,35,255))
        draw = ImageDraw.Draw(sheet)
        for i,(label,image) in enumerate((("A FROZEN",canonical),("K1 CANDIDATE",cell),("alpha/color diff overlay",overlay))):
            sheet.alpha_composite(image,(i*192,28))
            draw.text((i*192+3,3),label,fill="white")
            draw.line((i*192,231,i*192+191,231),fill=(255,175,45,255))
        sheet.save(qa / "contact-sheet.png")
        report = {**assess(cell), "processing":processing, "candidateSha256":digest(output/"K1.png")}
    else:
        # Native source shown without resampling, explicitly NOT a runtime cell.
        sheet = Image.new("RGBA",(192+original.width,28+max(208,original.height)),(35,35,35,255))
        sheet.alpha_composite(canonical,(0,28))
        sheet.alpha_composite(original,(192,28))
        draw = ImageDraw.Draw(sheet)
        draw.text((3,3),"A native192x208",fill="white")
        draw.text((195,3),"REJECTED native source / no resize",fill="white")
        sheet.save(qa/"contact-sheet.png")
        rejected_overlay(canonical,original).save(qa/"rejected-native-layout-overlay.png")
        rejected_detail_sheet(canonical,original).save(qa/"native-detail-contact-sheet.png")
        report = {"status":"K1_QA_FAIL","processing":processing,"candidateEmitted":False,
                  "reason":processing["reason"],"localChainAllowed":False,"runtimeEligible":False,
                  "headLandmarks":"NOT_VERIFIED: source cannot enter fixed canvas without forbidden fitting"}
    report.update({"sourceSha256":digest(source), "sourceRetained":"raw-native.png", "newPose":"K1 only",
                   "nativeSourceGeometry":native_geometry(original),
                   "K2K3Regenerated":False,"appIntegrated":False,"runtimeEligible":False})
    (qa/"validation.json").write_text(json.dumps(report,indent=2)+"\n")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source",type=Path,required=True)
    parser.add_argument("--output",type=Path,required=True)
    args = parser.parse_args()
    print(prepare(args.source,args.output)["status"])
