"""K1-origin K2 contract: native local pixel edits, locked identity, no whole-image fit."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image, ImageDraw

from tools.locked_transition_k1 import HEAD, masked_bytes, sha
from tools.prepare_transition_animation_candidate import digest, metrics

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "assets/rework/v0.1.0/transition-keyframes/k2-controlled"
K1 = ROOT / "assets/rework/v0.1.0/transition-keyframes/k1-locked/candidate/K1.png"
K1_SHA = "3fe2510fce45d2e7fb63e2018f79fe69ef9f05c470634903fa580700acc9e246"
CAP_BAND = (0, 84, 192, 100)


def source() -> Image.Image:
    if digest(K1) != K1_SHA:
        raise ValueError("approved K1 changed; stop, do not adapt the contract")
    with Image.open(K1) as image:
        if image.mode != "RGBA" or image.size != (192, 208):
            raise ValueError("approved native192x208 RGBA required")
        return image.copy()


def masks() -> tuple[Image.Image, Image.Image]:
    editable = Image.new("L", (192, 208))
    draw = ImageDraw.Draw(editable)
    draw.rectangle((63, 84, 128, 145), fill=255)
    # All y0:84 (including transparent RGB/alpha), neck/collar and lower body stay exact.
    draw.rectangle((84, 84, 102, 100), fill=0)
    return editable.point(lambda value: 255-value), editable


def cap_bbox(image: Image.Image) -> list[int] | None:
    box = image.getchannel("A").crop(CAP_BAND).getbbox()
    return [box[0], box[1]+84, box[2], box[3]+84] if box else None


def transparent_holes(image: Image.Image) -> int:
    """4-connected transparent pixels not reachable from the canvas border."""
    alpha = image.getchannel("A")
    clear = {(x, y) for y in range(208) for x in range(192) if not alpha.getpixel((x, y))}
    outside = {(x, y) for x, y in clear if x in (0, 191) or y in (0, 207)}
    pending = list(outside)
    while pending:
        x, y = pending.pop()
        for point in ((x-1, y), (x+1, y), (x, y-1), (x, y+1)):
            if point in clear and point not in outside:
                outside.add(point)
                pending.append(point)
    return len(clear-outside)


def specification() -> dict:
    k1 = source()
    locked, _ = masks()
    cap = cap_bbox(k1)
    return {
        "id": "K2_CONTROLLED_REGION_V1", "status": "SPECIFICATION_ONLY",
        "source": str(K1.relative_to(ROOT)), "sourceSha256": K1_SHA,
        "sourceApproval": "K1_ART_APPROVED: explicit user approval in this task; prior QA records unchanged",
        "canvas": [192, 208], "registrationX": 96, "baselineY": 203,
        "K1HeadBbox": list(HEAD), "K1HeadSize": [68, 80], "K1HeadCenter": [88, 44],
        "headSizePermittedRange": [[64, 72], [76, 84]], "maxHeadCenterDeltaPx": [3, 3],
        "controlledDerivationStricterRule": "reuse whole y0:84 RGBA byte-identically; effective head delta0",
        "lockedPolicy": "whole y0:84; neck/collar x84:103,y84:101; outside x63:129,y84:146; all lower body/hands/feet y146:208",
        "lockedReferenceByteSha256": sha(masked_bytes(k1, locked)),
        "editableBbox": [63, 84, 129, 146],
        "maskConvention": "L255 selected, row-major RGBA including transparent RGB/alpha",
        "K1ShoulderAnatomicalGuide": {"points": [[75, 83], [108, 83]], "width": 33},
        "maxAnatomicalShoulderGrowthPx": 12,
        "shoulderMeasurementPolicy": "upper guide y83 remains locked; alpha hull of band84:100 is a separate cap/upper-arm proxy, never an anatomical substitute; independent visual review required",
        "K1ShoulderCapBandBbox": cap, "K1ShoulderCapBandWidth": cap[2]-cap[0],
        "maxCapHullGrowthPx": 12, "minCapHullGrowthPx": 2,
        "maxBodyEdgeExpansionPx": 6, "maxBodyBandCenterDeltaPx": 1,
        "bodyPolicy": "gradual bilateral upper-jacket/arm thickening only; fixed lower body; not inflated to fit existing K3",
        "effects": "none; character change must be visible without energy overlays",
        "method": "explicit bounded integer pixel translations plus documented K1 RGBA cloth donors; no interpolation, whole-person scaling, AI generation, new head or face",
        "independentStaticReviewRequired": True, "userArtApproval": "PENDING",
        "K3BModificationAllowed": False, "appIntegrationAllowed": False, "runtimeEligible": False,
    }


def assess(candidate: Image.Image) -> dict:
    k1 = source()
    locked, _ = masks()
    original, actual = masked_bytes(k1, locked), masked_bytes(candidate, locked)
    info, reference = metrics(candidate), metrics(k1)
    body, base = info["bodyReferenceBbox"], reference["bodyReferenceBbox"]
    edges = [base[0]-body[0], body[2]-base[2]] if body else None
    cap, base_cap = cap_bbox(candidate), cap_bbox(k1)
    cap_growth = (cap[2]-cap[0])-(base_cap[2]-base_cap[0]) if cap else None
    head = candidate.getchannel("A").crop((0, 0, 192, 84)).getbbox()
    head_size = [head[2]-head[0], head[3]-head[1]] if head else None
    head_center = [(head[0]+head[2])/2, (head[1]+head[3])/2] if head else None
    head_delta = [head_center[0]-88, head_center[1]-44] if head else None
    changed = [(i%192, i//192) for i, (a, b) in enumerate(zip(k1.get_flattened_data(), candidate.get_flattened_data())) if a != b]
    difference = Image.new("L", (192, 208))
    difference.putdata([255 if a != b else 0 for a, b in zip(k1.get_flattened_data(), candidate.get_flattened_data())])
    checks = {
        "lockedByteIdentical": original == actual,
        "headByteIdentical": k1.crop((0, 0, 192, 84)).tobytes() == candidate.crop((0, 0, 192, 84)).tobytes(),
        "handsLowerBodyByteIdentical": k1.crop((0, 140, 192, 208)).tobytes() == candidate.crop((0, 140, 192, 208)).tobytes(),
        "headSizeWithin4": bool(head_size and abs(head_size[0]-68) <= 4 and abs(head_size[1]-80) <= 4),
        "headCenterWithin3": bool(head_delta and all(abs(v) <= 3 for v in head_delta)),
        "baseline203": info["baselineY"] == 203,
        "bodyEdgesGradual": bool(edges is not None and all(0 <= v <= 6 for v in edges)),
        "bodyCenterStable": bool(body and abs(info["bodyBandCenterX"]-reference["bodyBandCenterX"]) <= 1),
        "capGrowthWithin12": cap_growth is not None and 2 <= cap_growth <= 12,
        "paletteFromK1": set(candidate.get_flattened_data()) <= set(k1.get_flattened_data()),
        "binaryAlpha": info["alphaValues"] == [0, 255], "noHiddenRGB": not info["hiddenRgbPixels"],
        "noClipping": not info["touchesCellEdge"], "noIsolatedPixels": not info["isolatedSinglePixels"],
        "oneConnectedCharacter": len(info["connectedComponentSizes8"]) == 1,
        "noNewTransparentHoles": transparent_holes(candidate) <= transparent_holes(k1),
    }
    return {
        "status": "AWAITING_INDEPENDENT_K2_REVIEW" if all(checks.values()) else "K2_QA_FAIL",
        "technicalPass": all(checks.values()), "checks": checks,
        "headBbox": list(head) if head else None, "headSize": head_size,
        "headCenter": head_center, "headCenterDelta": head_delta,
        "registrationX": 96, "registrationPolicy": "no registration transform; original head/neck/feet held fixed",
        "baselineY": info["baselineY"], "bodyBbox": body, "bodyEdgeExpansion": edges,
        "bodyBandCenterX": info["bodyBandCenterX"],
        "upperShoulderGuide": {"K1Width": 33, "K2Width": 33 if checks["headByteIdentical"] else "NOT_VERIFIED", "note": "y83 guide locked; not a measurement of the lower cap expansion"},
        "shoulderCapBand": {"K1Bbox": base_cap, "K2Bbox": cap, "widthGrowth": cap_growth},
        "lockedByteComparison": {"referenceSha256": sha(original), "candidateSha256": sha(actual), "byteCount": len(original), "differentBytes": sum(a != b for a, b in zip(original, actual))},
        "rgbaChangedPixels": len(changed), "rgbaChangedBbox": list(difference.getbbox()) if changed else None,
        "measured": info, "userArtApproval": "PENDING", "localChainAllowed": False, "runtimeEligible": False,
    }


def prepare_spec(output: Path = OUTPUT / "spec") -> dict:
    if output.exists():
        raise ValueError("refuse to overwrite K2 specification")
    report = specification()
    output.mkdir(parents=True)
    locked, editable = masks()
    locked.save(output/"locked-mask.png")
    editable.save(output/"editable-mask.png")
    guide = Image.new("RGBA", (384, 240), (35, 35, 35, 255))
    k1 = source()
    guide.alpha_composite(k1, (0, 28))
    guide.alpha_composite(k1, (192, 28))
    tint = Image.new("RGBA", (192, 208))
    tint.putdata([(255, 90, 110, 65) if v else (90, 230, 150, 65) for v in locked.get_flattened_data()])
    guide.alpha_composite(tint, (192, 28))
    draw = ImageDraw.Draw(guide)
    draw.text((3, 3), "K1 APPROVED / NO EDIT", fill="white")
    draw.text((195, 3), "RED locked / GREEN editable", fill="white")
    guide.save(output/"mask-guide.png")
    (output/"specification.json").write_text(json.dumps(report, indent=2)+"\n")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--spec-output", type=Path, default=OUTPUT/"spec")
    args = parser.parse_args()
    print(prepare_spec(args.spec_output)["status"])
