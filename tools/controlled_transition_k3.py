"""K2-origin K3 specification and conservative local-pixel QA, without App integration."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image, ImageDraw

from tools.controlled_transition_k2 import cap_bbox, transparent_holes
from tools.locked_transition_k1 import HEAD, masked_bytes, sha
from tools.prepare_transition_animation_candidate import digest, metrics
from tools.specify_transition_keyframes import approved_inputs

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "assets/rework/v0.1.0/transition-keyframes/k3-controlled"
K2 = ROOT / "assets/rework/v0.1.0/transition-keyframes/k2-controlled/candidate-locked-hands/K2.png"
K2_SHA = "565122ea1364eebd56a0d6d3b53934bef8d45d53cb1787eedf4ee1f812cdfcec"
B_SHA = "4ae8848d3a40e6c3d8507b7fda119d58462f3236b3202471239ee0b9c0ac506b"


def source() -> Image.Image:
    if digest(K2) != K2_SHA:
        raise ValueError("approved K2 changed; stop, do not adapt K3 to a changed source")
    with Image.open(K2) as image:
        if image.mode != "RGBA" or image.size != (192, 208):
            raise ValueError("approved native192x208 RGBA K2 required")
        return image.copy()


def endpoint_b() -> tuple[Path, Image.Image]:
    _, path, image = approved_inputs()[1]
    if digest(path) != B_SHA or image.mode != "RGBA" or image.size != (192, 208):
        raise ValueError("frozen approved B changed")
    return path, image


def masks() -> tuple[Image.Image, Image.Image]:
    editable = Image.new("L", (192, 208))
    draw = ImageDraw.Draw(editable)
    draw.rectangle((58, 84, 130, 139), fill=255)
    draw.rectangle((84, 84, 102, 100), fill=0)
    return editable.point(lambda value: 255-value), editable


def specification() -> dict:
    k2 = source()
    path, b = endpoint_b()
    locked, _ = masks()
    cap, body = cap_bbox(k2), metrics(k2)["bodyReferenceBbox"]
    return {
        "id": "K3_CONTROLLED_REGION_V1", "status": "SPECIFICATION_ONLY", "generatedPoses": 0,
        "source": str(K2.relative_to(ROOT)), "sourceSha256": K2_SHA,
        "sourceApproval": "K2_ART_APPROVED: explicit user statement in current K3 task; historical K2 QA files stay unchanged",
        "canvas": [192, 208], "registrationX": 96, "baselineY": 203,
        "K2HeadBbox": list(HEAD), "K2HeadSize": [68, 80], "K2HeadCenter": [88, 44],
        "headSizePermittedRange": [[63, 73], [75, 85]], "maxHeadCenterDeltaPx": [3, 3],
        "derivationStricterRule": "whole y0:84 RGBA unchanged; effective head size/center delta0; no face/hair/eyeglass repaint",
        "editableBbox": [58, 84, 131, 140],
        "lockedPolicy": "whole y0:84 including transparent bytes; neck/collar x84:103,y84:101; all y140:208 hands/cuffs/legs/feet; outside conservative edit rectangle",
        "maskConvention": "L255 selected; row-major RGBA includes transparent RGB/alpha",
        "lockedReferenceByteSha256": sha(masked_bytes(k2, locked)),
        "upperShoulderGuide": {"points": [[75, 83], [108, 83]], "width": 33, "policy": "locked guide y83, not the widened lower-cap anatomical width"},
        "maxAnatomicalShoulderGrowthPx": 14,
        "K2ShoulderCapBandBbox": cap, "K2ShoulderCapBandWidth": cap[2]-cap[0],
        "capBandGrowthTargetPx": [10, 14],
        "shoulderPolicy": "cap band84:100 alpha hull is a conservative proxy, not skeletal shoulder width; report it separately and require independent visual anatomy/pose review",
        "K2BodyBandBbox": body, "maxBodyEdgeExpansionPx": 7, "maxBodyWidthGrowthPx": 14,
        "maxBodyBandCenterDeltaPx": 1,
        "bodyPolicy": "another gradual bilateral upper-jacket/upper-arm step; no45px jump, whole-person fit or reshaping approved K2 to accommodate B",
        "BReference": {"source": str(path.relative_to(ROOT)), "sha256": B_SHA,
                       "bodyBandBbox": metrics(b)["bodyReferenceBbox"], "headApproxBbox": [64, 4, 113, 58],
                       "headApproxSize": [49, 54], "headApproxCenter": [88.5, 31],
                       "anatomicalUncertaintyPx": 3, "note": "manual historical guide, chin partly hand-occluded; not exact segmentation"},
        "endpointRisk": "K2-relative ±5px head budget cannot erase B's approximate19x26px head difference in one step; inspect K3->B separately, use B_TRANSITION_BRIDGE_REQUIRED for visible discontinuity; do not relax incoming budget",
        "method": "bounded native local integer copies with documented K2 cloth donors only; no global scale/translation, interpolation or AI",
        "effects": "none preferred; body change primary, no overlay hiding geometry",
        "independentStaticReviewRequired": True, "userK3ArtApproval": "PENDING",
        "appIntegrationAllowed": False, "fullAnimationAllowed": False, "runtimeEligible": False,
        "approvedInputsModificationAllowed": False,
    }


def assess(candidate: Image.Image) -> dict:
    k2 = source()
    locked, _ = masks()
    original, actual = masked_bytes(k2, locked), masked_bytes(candidate, locked)
    info, reference = metrics(candidate), metrics(k2)
    body, base = info["bodyReferenceBbox"], reference["bodyReferenceBbox"]
    edges = [base[0]-body[0], body[2]-base[2]] if body else None
    body_growth = sum(edges) if edges is not None else None
    cap, base_cap = cap_bbox(candidate), cap_bbox(k2)
    cap_growth = (cap[2]-cap[0])-(base_cap[2]-base_cap[0]) if cap else None
    head = candidate.getchannel("A").crop((0, 0, 192, 84)).getbbox()
    size = [head[2]-head[0], head[3]-head[1]] if head else None
    center = [(head[0]+head[2])/2, (head[1]+head[3])/2] if head else None
    delta = [center[0]-88, center[1]-44] if head else None
    diff = Image.new("L", (192, 208))
    differences = [255 if a != b else 0 for a, b in zip(k2.get_flattened_data(), candidate.get_flattened_data())]
    diff.putdata(differences)
    checks = {
        "lockedByteIdentical": original == actual,
        "headByteIdentical": k2.crop((0, 0, 192, 84)).tobytes() == candidate.crop((0, 0, 192, 84)).tobytes(),
        "handsLowerBodyByteIdentical": k2.crop((0, 140, 192, 208)).tobytes() == candidate.crop((0, 140, 192, 208)).tobytes(),
        "headSizeWithin5": bool(size and abs(size[0]-68) <= 5 and abs(size[1]-80) <= 5),
        "headCenterWithin3": bool(delta and all(abs(v) <= 3 for v in delta)),
        "baseline203": info["baselineY"] == 203,
        "bodyEdgesGradual": bool(edges is not None and all(0 <= v <= 7 for v in edges)),
        "bodyWidthGrowthWithin14": body_growth is not None and 0 < body_growth <= 14,
        "bodyCenterStable": bool(body and abs(info["bodyBandCenterX"]-reference["bodyBandCenterX"]) <= 1),
        "capGrowth10to14": cap_growth is not None and 10 <= cap_growth <= 14,
        "paletteFromK2": set(candidate.get_flattened_data()) <= set(k2.get_flattened_data()),
        "binaryAlpha": info["alphaValues"] == [0, 255], "noHiddenRGB": not info["hiddenRgbPixels"],
        "noClipping": not info["touchesCellEdge"], "noIsolatedPixels": not info["isolatedSinglePixels"],
        "oneConnectedCharacter": len(info["connectedComponentSizes8"]) == 1,
        "noNewTransparentHoles": transparent_holes(candidate) <= transparent_holes(k2),
    }
    return {
        "status": "AWAITING_INDEPENDENT_K3_REVIEW" if all(checks.values()) else "K3_QA_FAIL",
        "technicalPass": all(checks.values()), "checks": checks,
        "headBbox": list(head) if head else None, "headSize": size, "headCenter": center, "headCenterDelta": delta,
        "registrationX": 96, "registrationPolicy": "no transform; original head/neck/feet remain fixed",
        "baselineY": info["baselineY"], "bodyBbox": body, "bodyEdgeExpansion": edges,
        "bodyWidthGrowth": body_growth, "bodyBandCenterX": info["bodyBandCenterX"],
        "upperShoulderGuide": {"K2Width": 33, "K3Width": 33 if checks["headByteIdentical"] else "NOT_VERIFIED", "note": "y83 locked guide, not lower-cap anatomy"},
        "shoulderCapBand": {"K2Bbox": base_cap, "K3Bbox": cap, "widthGrowth": cap_growth},
        "lockedByteComparison": {"referenceSha256": sha(original), "candidateSha256": sha(actual), "byteCount": len(original), "differentBytes": sum(a != b for a, b in zip(original, actual))},
        "rgbaChangedPixels": sum(bool(value) for value in differences), "rgbaChangedBbox": list(diff.getbbox()) if diff.getbbox() else None,
        "measured": info, "localChainAllowed": False, "userK3ArtApproval": "PENDING", "runtimeEligible": False,
    }


def prepare_spec(output: Path = OUTPUT/"spec") -> dict:
    if output.exists():
        raise ValueError("refuse to overwrite K3 specification")
    report = specification()
    output.mkdir(parents=True)
    locked, editable = masks()
    locked.save(output/"locked-mask.png")
    editable.save(output/"editable-mask.png")
    k2, b = source(), endpoint_b()[1]
    guide = Image.new("RGBA", (576, 240), (35, 35, 35, 255))
    draw = ImageDraw.Draw(guide)
    for i, (label, image) in enumerate(zip(("K2 APPROVED / FROZEN", "K2 edit mask ONLY", "B APPROVED / FROZEN"), (k2, k2, b))):
        guide.alpha_composite(image, (i*192, 28))
        draw.text((i*192+3, 3), label, fill="white")
    tint = Image.new("RGBA", (192, 208))
    tint.putdata([(255, 90, 110, 65) if value else (90, 230, 150, 65) for value in locked.get_flattened_data()])
    guide.alpha_composite(tint, (192, 28))
    guide.save(output/"reference-mask-guide.png")
    (output/"specification.json").write_text(json.dumps(report, indent=2)+"\n")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--spec-output", type=Path, default=OUTPUT/"spec")
    args = parser.parse_args()
    print(prepare_spec(args.spec_output)["status"])
