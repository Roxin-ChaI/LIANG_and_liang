"""Read-only K1->controlled K2->unchanged K3; requires fresh K1/K2 static PASS."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image, ImageDraw

from tools.controlled_transition_k2 import OUTPUT, ROOT, source, cap_bbox
from tools.derive_controlled_transition_k2 import CANDIDATE, resolve_review
from tools.locked_transition_k1 import sha
from tools.prepare_manual_transition_endpoints import pixel_overlay
from tools.prepare_transition_animation_candidate import digest, metrics

K2_SHA = "565122ea1364eebd56a0d6d3b53934bef8d45d53cb1787eedf4ee1f812cdfcec"
K3 = ROOT / "assets/rework/v0.1.0/transition-keyframes/gu-to-feng-candidate-retry/keys/K3.png"
K3_SHA = "bf2ce6f91fd6a545ffaec47b82227b55e9ae7d19d69ffcbd2e9e6a322f934314"


def pair_metrics(k2: Image.Image, k3: Image.Image) -> dict:
    a, b = metrics(k2), metrics(k3)
    cap_a, cap_b = cap_bbox(k2), cap_bbox(k3)
    return {
        "headSize": {"K2": [68, 80], "K3Approx": [52, 58], "deltaApprox": [-16, -22]},
        "headCenter": {"K2": [88, 44], "K3Approx": [90, 33], "deltaApprox": [2, -11]},
        "historicalK3AnatomicalAnnotationUncertaintyPx": 3,
        "upperShoulderGuide": {"K2LockedWidth": 33, "K3ApproxWidth": 70, "deltaApprox": 37,
                               "warning": "different anatomical guide heights: K2y83 locked; K3y65:67 historical annotation. Not alpha-hull width or a new exact segmentation."},
        "shoulderCapBand": {"K2Bbox": cap_a, "K3Bbox": cap_b,
                            "widthDelta": (cap_b[2]-cap_b[0])-(cap_a[2]-cap_a[0]),
                            "warning": "same exact band84:100 alpha hull, not anatomical shoulder width"},
        "bodyBandBbox": {"K2": a["bodyReferenceBbox"], "K3": b["bodyReferenceBbox"],
                         "delta": [v-u for u, v in zip(a["bodyReferenceBbox"], b["bodyReferenceBbox"])]},
        "baselineDelta": b["baselineY"]-a["baselineY"],
        "numericEvidenceOnly": True, "visualVerdict": "AWAITING_INDEPENDENT_REVIEW",
    }


def resolve_chain(report: dict, review: dict) -> dict:
    hashes_match = (review.get("reviewedK2RgbaSha256") == report["K2RgbaSha256"]
                    and review.get("reviewedK3RgbaSha256") == report["K3RgbaSha256"])
    observed = review.get("K1_K2") == "PASS" and review.get("K2_K3") == "FAIL"
    blocked = (report["K1_K2"] == "K1_K2_STATIC_PASS" and hashes_match and observed
               and review.get("verdict") == "K3_REWORK_REQUIRED" and bool(review.get("reviewer")))
    return {"status": "K3_REWORK_REQUIRED" if blocked else "CHAIN_NOT_VERIFIED",
            "K1_K2": report["K1_K2"], "K2_K3": "STATIC_FAIL" if blocked else "NOT_VERIFIED",
            "userK2ArtApproval": "PENDING", "runtimeEligible": False,
            "scope": "static only, no App or complete animation approval",
            "K2ModifiedForK3": False, "K3Modified": False}


def prepare(output: Path = OUTPUT / "chain-qa", review_path: Path | None = None) -> dict:
    if output.exists():
        raise ValueError("refuse to overwrite chain evidence")
    k1 = source()
    if digest(CANDIDATE/"K2.png") != K2_SHA:
        raise ValueError("new K2 changed; stop, do not reshape it for K3")
    with Image.open(CANDIDATE/"K2.png") as image:
        k2 = image.copy()
    review_file = review_path or CANDIDATE/"qa/independent-review.json"
    prerequisite = resolve_review(k2, json.loads(review_file.read_text()))
    if not prerequisite["localChainAllowed"]:
        raise ValueError("fresh K1_K2_STATIC_PASS required before conditional K3 audit")
    if digest(K3) != K3_SHA:
        raise ValueError("existing K3 changed; stop without regenerating it")
    with Image.open(K3) as image:
        if image.mode != "RGBA" or image.size != (192, 208):
            raise ValueError("native existing K3 geometry changed")
        k3 = image.copy()
    output.mkdir(parents=True)
    sheet = Image.new("RGBA", (576, 240), (35, 35, 35, 255))
    draw = ImageDraw.Draw(sheet)
    for i, (label, image) in enumerate(zip(("K1 APPROVED / FROZEN", "K2 CONTROLLED / STATIC PASS", "K3 EXISTING / NO EDIT"), (k1, k2, k3))):
        sheet.alpha_composite(image, (i*192, 28))
        draw.text((i*192+3, 3), label, fill="white")
        draw.line((i*192, 231, i*192+191, 231), fill=(255, 185, 45, 255))
    sheet.save(output/"contact-sheet.png")
    sheet.resize((1728, 720), Image.Resampling.NEAREST).save(output/"contact-sheet-nearest3x.png")
    for name, left, right in (("K1-K2", k1, k2), ("K2-K3", k2, k3)):
        panel = Image.new("RGBA", (576, 240), (35, 35, 35, 255))
        pd = ImageDraw.Draw(panel)
        for i, (label, image) in enumerate(zip((name+" LEFT", name+" RIGHT", "RGBA diff overlay"), (left, right, pixel_overlay(left, right)))):
            panel.alpha_composite(image, (i*192, 28))
            pd.text((i*192+3, 3), label, fill="white")
        panel.save(output/f"{name}-overlay-contact.png")
    report = {"status": "AWAITING_INDEPENDENT_CHAIN_REVIEW", "K1_K2": "K1_K2_STATIC_PASS",
              "K2_K3": pair_metrics(k2, k3), "K2Sha256": K2_SHA, "K3Sha256": K3_SHA,
              "K2RgbaSha256": sha(k2.tobytes()), "K3RgbaSha256": sha(k3.tobytes()),
              "K3Source": str(K3.relative_to(ROOT)), "newPosesGenerated": 0,
              "K1Modified": False, "K2ModifiedForK3": False, "K3Modified": False,
              "userK2ArtApproval": "PENDING", "runtimeEligible": False}
    (output/"landmark-report.json").write_text(json.dumps(report, indent=2)+"\n")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUTPUT/"chain-qa")
    parser.add_argument("--review", type=Path)
    args = parser.parse_args()
    if args.review:
        report = json.loads((args.output/"landmark-report.json").read_text())
        final = resolve_chain(report, json.loads(args.review.read_text()))
        (args.output/"final-verdict.json").write_text(json.dumps(final, indent=2)+"\n")
        print(final["status"])
    else:
        print(prepare(args.output)["status"])
