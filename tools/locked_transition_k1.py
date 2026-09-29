"""User-authorized K1 local pixel derivation contract; no AI generation or global fit."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from PIL import Image, ImageDraw

from tools.specify_transition_keyframes import approved_inputs
from tools.prepare_transition_animation_candidate import digest, metrics

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "assets/rework/v0.1.0/transition-keyframes/k1-locked"
HEAD = (54,4,122,84)


def masks() -> tuple[Image.Image, Image.Image]:
    editable = Image.new("L",(192,208))
    draw = ImageDraw.Draw(editable)
    # Conservative allowance: shoulders, arms, torso and upper legs only.
    draw.rectangle((66,90,125,179),fill=255)
    # Preserve the neck/collar connection in addition to the entire upper90 rows.
    draw.rectangle((84,90,102,100),fill=0)
    locked = editable.point(lambda value: 255-value)
    return locked,editable


def masked_bytes(image: Image.Image, mask: Image.Image) -> bytes:
    if image.mode != "RGBA" or image.size != (192,208) or mask.mode != "L" or mask.size != image.size:
        raise ValueError("native192x208 RGBA and192x208 L mask required")
    return bytes(channel for pixel,selected in zip(image.get_flattened_data(),mask.get_flattened_data())
                 if selected for channel in pixel)


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def specification() -> dict:
    _,path,a = approved_inputs()[0]
    locked,editable = masks()
    return {"id":"K1_LOCKED_REGION_V1","status":"SPECIFICATION_ONLY",
            "source":str(path.relative_to(ROOT)),"sourceSha256":digest(path),
            "canvas":[192,208],"registrationX":96,"baselineY":203,
            "headBbox":list(HEAD),"headSize":[68,80],"headCenter":[88,44],
            "maxHeadCenterDelta":1,"effectiveHeadDeltaRequired":0,
            "lockedPolicy":"entire y0:90 incl transparent pixels; neck/collar x84:103,y90:101; outside conservative body edit rectangle; feet/lower legs y180:208",
            "editableBbox":[66,90,126,180],"maskConvention":"L binary255 selected; row-major RGBA bytes incl transparent RGB/alpha",
            "lockedPixelCount":sum(bool(v) for v in locked.get_flattened_data()),
            "editablePixelCount":sum(bool(v) for v in editable.get_flattened_data()),
            "lockedReferenceByteSha256":sha(masked_bytes(a,locked)),
            "shoulderGuidePoints":[[75,83],[108,83]],"shoulderGuideWidth":33,
            "shoulderGuidePolicy":"same canonical guide because its entire supporting region is byte-locked; separate band90:110 hull is a geometric proxy, not shoulder anatomy",
            "maxShoulderWidthDelta":4,"maxBodyEdgeDelta":3,
            "method":"explicit A-origin local integer pixel copies/hand edits only; no whole-person scaling, translation, interpolation, AI or head repair",
            "effects":"none preferred; no detached/soft accents or head overlays",
            "visualReviewRequired":True,"appIntegrationAllowed":False,
            "K2K3ModificationAllowed":False,"runtimeEligible":False}


def assess(candidate: Image.Image) -> dict:
    a = approved_inputs()[0][2]
    locked,editable = masks()
    # Invalid geometry is never silently converted.
    original,observed = masked_bytes(a,locked),masked_bytes(candidate,locked)
    changed = [(i%192,i//192) for i,(p,q) in enumerate(zip(a.get_flattened_data(),candidate.get_flattened_data())) if p != q]
    changed_set = set(changed)
    locked_changed = [(x,y) for x,y in changed if locked.getpixel((x,y))]
    info = metrics(candidate)
    source = metrics(a)
    body = info["bodyReferenceBbox"]
    edges = [body[0]-source["bodyReferenceBbox"][0],body[2]-source["bodyReferenceBbox"][2]] if body else None
    band_a = a.getchannel("A").crop((0,90,192,110)).getbbox()
    band_k = candidate.getchannel("A").crop((0,90,192,110)).getbbox()
    band_delta = (band_k[2]-band_k[0])-(band_a[2]-band_a[0]) if band_k else None
    head_a = a.crop((0,0,192,84))
    head_k = candidate.crop((0,0,192,84))
    head_box = head_k.getchannel("A").getbbox()
    checks = {"lockedRegionByteIdentical":original == observed,
              "headByteIdentical":head_a.tobytes() == head_k.tobytes(),
              "headBboxExact":head_box == HEAD,"baseline203":info["baselineY"] == 203,
              "bodyLeftWithin3":edges is not None and abs(edges[0]) <= 3,
              "bodyRightWithin3":edges is not None and abs(edges[1]) <= 3,
              "shoulderGuideLocked":a.crop((64,76,124,90)).tobytes() == candidate.crop((64,76,124,90)).tobytes(),
              "shoulderBandProxyWithin4":band_delta is not None and abs(band_delta) <= 4,
              "binaryAlpha":info["alphaValues"] == [0,255],"noHiddenRGB":not info["hiddenRgbPixels"],
              "noClipping":not info["touchesCellEdge"],"noIsolatedPixels":not info["isolatedSinglePixels"],
              "oneConnectedCharacter":len(info["connectedComponentSizes8"]) == 1}
    return {"status":"AWAITING_INDEPENDENT_PIXEL_REVIEW" if all(checks.values()) else "K1_QA_FAIL",
            "technicalPass":all(checks.values()),"checks":checks,
            "lockedByteComparison":{"referenceSha256":sha(original),"candidateSha256":sha(observed),
                                    "byteCount":len(original),"differentBytes":sum(p != q for p,q in zip(original,observed)),
                                    "changedLockedPixels":len(locked_changed)},
            "headBbox":list(head_box) if head_box else None,"headSize":[68,80] if checks["headBboxExact"] else None,
            "headCenter":[88,44] if checks["headBboxExact"] else None,
            "headCenterDelta":[0,0] if checks["headByteIdentical"] else "NOT_VERIFIED",
            "registrationX":96,"registrationOperation":"none; feet/neck/head anchored to A",
            "bodyEdgeDelta":edges,"shoulderGuideWidthDelta":0 if checks["shoulderGuideLocked"] else "NOT_VERIFIED",
            "shoulderBandHullWidthDelta":band_delta,"baselineDelta":info["baselineY"]-203 if body else None,
            "rgbaChangedPixels":len(changed),"rgbaChangedBbox":list(Image.frombytes("L",(192,208),bytes(255 if (i%192,i//192) in changed_set else 0 for i in range(192*208))).getbbox()) if changed else None,
            "measured":info,"visualApproval":"NOT_VERIFIED","localChainAllowed":False,"runtimeEligible":False}


def prepare_spec(output: Path = OUTPUT / "spec") -> dict:
    if output.exists():
        raise ValueError("refuse to overwrite locked specification")
    output.mkdir(parents=True)
    report = specification()
    locked,editable = masks()
    locked.save(output/"locked-mask.png")
    editable.save(output/"editable-mask.png")
    a = approved_inputs()[0][2]
    guide = Image.new("RGBA",(384,240),(35,35,35,255))
    guide.alpha_composite(a,(0,28))
    guide.alpha_composite(a,(192,28))
    tint = Image.new("RGBA",(192,208))
    tint.putdata([(255,90,110,65) if v else (90,230,150,65) for v in locked.get_flattened_data()])
    guide.alpha_composite(tint,(192,28))
    draw = ImageDraw.Draw(guide)
    draw.text((3,3),"A FROZEN",fill="white")
    draw.text((195,3),"RED locked / GREEN editable",fill="white")
    guide.save(output/"mask-guide.png")
    (output/"specification.json").write_text(json.dumps(report,indent=2)+"\n")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--spec-output",type=Path,default=OUTPUT/"spec")
    args = parser.parse_args()
    print(prepare_spec(args.spec_output)["status"])
