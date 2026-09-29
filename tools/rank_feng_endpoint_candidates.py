"""Extract three unmodified Feng atlas cells for a visual F0 ranking gate."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image, ImageDraw

from tools.audit_b_endpoint_compatibility import KB2
from tools.audit_feng_atlas_neutral import FENG_ATLAS, FENG_ATLAS_SHA, QA as INVENTORY_QA, geometry
from tools.f0_transition_endpoint_spec import OUT, specification
from tools.prepare_transition_animation_candidate import digest
from tools.transition_bridge_spec import B_HEAD, landmark

QA = OUT / "atlas-candidate-ranking"
# Independent visual review selected the relative nearest, not approved F0s.
SHORTLIST = (("F0-A", 8, 4, "review"),
             ("F0-B", 1, 6, "running-right"),
             ("F0-C", 3, 0, "waving"))
# Approximate manually inspected hair/face guides. Hand overlap makes them
# unsuitable as an anatomical segmentation or an approval criterion.
HEAD_GUIDES = {"F0-A": [64, 4, 114, 59],
               "F0-B": [72, 5, 124, 61],
               "F0-C": [64, 5, 114, 60]}


def collect() -> tuple[dict, list[Image.Image]]:
    specification()
    if digest(FENG_ATLAS) != FENG_ATLAS_SHA:
        raise ValueError("formal Feng atlas changed")
    inventory = json.loads((INVENTORY_QA / "inventory.json").read_text())
    if inventory["atlasSha256"] != FENG_ATLAS_SHA or len(inventory["records"]) != 88:
        raise ValueError("missing or stale full atlas inventory")
    with Image.open(FENG_ATLAS) as image:
        atlas = image.copy()
    with Image.open(KB2) as image:
        kb2 = image.copy()
    b = atlas.crop((0, 0, 192, 208))
    cells = [kb2]
    records = []
    for label, row, col, state in SHORTLIST:
        cell = atlas.crop((col * 192, row * 208, (col + 1) * 192, (row + 1) * 208))
        data = geometry(cell)
        logged = inventory["records"][row * 8 + col]
        if not logged["nonempty"] or logged["rgbaSha256"] != data["rgbaSha256"]:
            raise ValueError("shortlisted cell missing or altered")
        guide = landmark(cell, HEAD_GUIDES[label], approximate=True)
        records.append({"candidate": label, "row": row, "frame": col, "state": state,
                        "headBboxGuideApprox": guide["headBbox"],
                        "headSizeGuideApprox": guide["headSize"],
                        "headCenterGuideApprox": guide["headCenter"],
                        "headGuideUncertaintyPx": 3,
                        "bodyBbox": data["bodyBbox"],
                        "bodyBandCenterX": data["bodyBandCenterX"],
                        "baselineY": data["baselineY"], "registrationX": 96,
                        "alphaBbox": data["alphaBbox"], "rgbaSha256": data["rgbaSha256"],
                        "armPose": "INDEPENDENT_VISUAL_REVIEW_REQUIRED",
                        "legStance": "INDEPENDENT_VISUAL_REVIEW_REQUIRED",
                        "KB2ToCandidate": "INDEPENDENT_VISUAL_REVIEW_REQUIRED",
                        "candidateToFormalFengIdle": "INDEPENDENT_VISUAL_REVIEW_REQUIRED"})
        cells.append(cell)
    cells.append(b)
    return {"status": "THREE_CANDIDATES_EXTRACTED_RANKING_PENDING", "sourceAtlasSha256": FENG_ATLAS_SHA,
            "shortlistCount": len(SHORTLIST), "shortlist": records,
            "KB2": landmark(kb2, [60, 4, 116, 72]),
            "formalFengIdle": landmark(b, B_HEAD, approximate=True),
            "guideWarning": "Head guides are visual approximations ±3px; raised hands and collars can obscure the face. Body-band bbox includes limbs, not isolated shoulders.",
            "candidateSourceCellsModified": False, "approvedF0": None}, cells


def prepare(output: Path = QA) -> dict:
    if output.exists():
        raise ValueError("refuse to overwrite shortlisted candidate QA")
    report, cells = collect()
    output.mkdir(parents=True)
    sheet = Image.new("RGBA", (192 * 5, 232), (31, 31, 31, 255))
    draw = ImageDraw.Draw(sheet)
    labels = ["KB2"] + [f"{name} {state} {row}/{col}" for name, row, col, state in SHORTLIST] + ["B / Feng Idle"]
    for col, (label, image) in enumerate(zip(labels, cells)):
        sheet.alpha_composite(image, (col * 192, 20))
        draw.text((col * 192 + 2, 2), label, fill="white")
    sheet.save(output / "three-candidates-contact.png")
    sheet.resize((2880, 696), Image.Resampling.NEAREST).save(output / "three-candidates-nearest3x.png")
    (output / "candidate-technical.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


def resolve(report: dict, review: dict) -> dict:
    source = {item["candidate"]: item for item in report["shortlist"]}
    verdicts = review.get("rankedCandidates", [])
    fresh = (review.get("sourceAtlasSha256") == report["sourceAtlasSha256"]
             and len(verdicts) == len(source)
             and {item.get("candidate") for item in verdicts} == set(source)
             and all(item.get("rgbaSha256") == source[item["candidate"]]["rgbaSha256"]
                     and (item.get("row"), item.get("frame")) ==
                     (source[item["candidate"]]["row"], source[item["candidate"]]["frame"])
                     for item in verdicts))
    qualified = [item["candidate"] for item in verdicts if item.get("qualified") is True]
    found = fresh and bool(review.get("reviewer")) and bool(qualified) and review.get("verdict") == "EXISTING_FENG_ENDPOINT_CANDIDATE_FOUND"
    no_existing = fresh and bool(review.get("reviewer")) and not qualified and review.get("verdict") == "NO_EXISTING_FENG_ENDPOINT"
    status = ("EXISTING_FENG_ENDPOINT_CANDIDATE_FOUND" if found else
              "NO_EXISTING_FENG_ENDPOINT" if no_existing else "VISUAL_RANKING_NOT_VERIFIED")
    return {"status": status, "independentReviewFresh": fresh,
            "qualifiedCandidates": qualified if found else [],
            "selectedStaticChainAllowed": found, "newBridgeAllowed": found,
            "formalAtlasModified": False, "F0AssetWritten": False}


def finalize(output: Path = QA) -> dict:
    actual, _ = collect()
    stored = json.loads((output / "candidate-technical.json").read_text())
    if stored != actual:
        raise ValueError("stale or altered candidate technical report")
    review = json.loads((output / "independent-review.json").read_text())
    result = resolve(actual, review)
    (output / "final-verdict.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=QA)
    parser.add_argument("--review", action="store_true")
    args = parser.parse_args()
    print((finalize(args.output) if args.review else prepare(args.output))["status"])
