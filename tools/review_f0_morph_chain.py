"""Read-only, hash-bound static review of the six-pose morphology chain.

Evidence generation never edits a candidate or substitutes geometry for art QA.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from PIL import Image

from tools.f0_morph_bridge import HEAD_GUIDES, OUTPUT, hand_guides, pair, sources
from tools.manual_kf1_pixel_art import DEST as KF1_DIR, assess as assess_kf1, contact
from tools.manual_kf1_pixel_art import resolve_review as resolve_kf1
from tools.manual_kf2_pixel_art import DEST as KF2_DIR, assess as assess_kf2
from tools.manual_kf2_pixel_art import resolve_review as resolve_kf2
from tools.prepare_transition_animation_candidate import digest
from tools.transition_bridge_spec import K3_HEAD, OUTPUT as OLD_OUTPUT
from tools.transition_bridge_spec import ROOT, FROZEN, frozen_images, landmark, step_gate

DEST = OUTPUT / "full-chain-qa"
NAMES = ("K3", "KB1", "KB2", "KF1", "KF2", "F0")
KB1_SHA = "4d1b307e3e251352d3cc165c95f85009d445f797efd94bfeb28fe682a30cd837"
KF1_SHA = "c189516b94db095e71a83460c7f2e831ca44841a6c97564f48252445ade1407b"
KF2_SHA = "1917e459ee6554d29625649c15a87edd7f4029b42338a8645304cab5fa847676"
GUIDES = {"K3": K3_HEAD, "KB1": [57,4,119,78], **HEAD_GUIDES}


def read_json(path: Path) -> dict:
    return json.loads(path.read_text())


def rgba_digest(image: Image.Image) -> str:
    return hashlib.sha256(image.tobytes()).hexdigest()


def frames() -> tuple[dict, dict]:
    frozen = frozen_images()
    images = {"K3": frozen["K3"], **sources()}
    paths = {"K3": ROOT / FROZEN["K3"][0],
             "KB2": OLD_OUTPUT / "kb2/KB2.png",
             "F0": OUTPUT.parent / "manual-pixel-art/F0.png"}
    for name, path, expected in (
        ("KB1", OLD_OUTPUT / "kb1/KB1.png", KB1_SHA),
        ("KF1", KF1_DIR / "KF1.png", KF1_SHA),
        ("KF2", KF2_DIR / "KF2.png", KF2_SHA),
    ):
        if digest(path) != expected:
            raise ValueError(f"reviewed {name} changed")
        with Image.open(path) as image:
            images[name] = image.copy()
        paths[name] = path
    return images, paths


def historical_review(review: dict, left: Image.Image, right: Image.Image,
                      expected_verdict: str) -> dict:
    fresh = (review.get("sourceRgbaSha256") == rgba_digest(left)
             and review.get("candidateRgbaSha256") == rgba_digest(right))
    checks = review.get("checks", {})
    passed = (fresh and bool(review.get("reviewer")) and bool(checks)
              and all(v.get("status") == "PASS" for v in checks.values())
              and review.get("verdict") == expected_verdict)
    return {"fresh": fresh, "visualPass": passed, "scope": "historical static review",
            "review": review}


def verdict(pairs: dict) -> dict:
    passed = bool(pairs) and len(pairs) == 5 and all(
        p["numericPass"] and p["visualPass"] and p["reviewFresh"] for p in pairs.values())
    return {"status": "F0_ART_APPROVED" if passed else "MANUAL_BRIDGE_QA_FAIL",
            "F0ArtApproved": passed, "F0ToIdleAuditAllowed": passed,
            "runtimeIntegrationAllowed": False}


def assess() -> dict:
    images, paths = frames()
    marks = {n: landmark(images[n], GUIDES[n], approximate=True) for n in NAMES}
    hands = {n: hand_guides(images[n]) for n in NAMES}
    pairs = {}
    for index, (a, b) in enumerate(zip(NAMES, NAMES[1:])):
        if index < 2:
            geometry = step_gate(marks[a], marks[b])
            review = historical_review(read_json(OLD_OUTPUT / b.lower() / "qa/independent-review.json"),
                                       images[a], images[b], f"{a}_{b}_STATIC_PASS")
            geometry.update(visualPass=review["visualPass"], reviewFresh=review["fresh"],
                            visualEvidence=review["review"], budgetScope="previous approved bridge contract")
        else:
            geometry = pair(marks[a], marks[b], hands[a], hands[b])
            if index == 2:
                raw = read_json(KF1_DIR / "independent-review.json")
                resolution = resolve_kf1(assess_kf1(images[b]), raw)
                visual = resolution["visualPass"]
                fresh = resolution["independentReviewFresh"] and raw.get("candidatePngSha256") == digest(paths[b])
                evidence = raw
            else:
                raw = read_json(KF2_DIR / "independent-review.json")
                resolution = resolve_kf2(assess_kf2(images["KF2"]), raw)
                visual = resolution["visualPairPass"][f"{a}_{b}"]
                fresh = resolution["independentReviewFresh"] and raw.get("candidatePngSha256") == digest(paths["KF2"])
                evidence = raw["pairs"][f"{a}_{b}"]
            geometry.update(visualPass=visual, reviewFresh=fresh, visualEvidence=evidence,
                            budgetScope="KF1/KF2 manual morphology contract")
        pairs[f"{a}_{b}"] = geometry
    return {**verdict(pairs), "scope": "static source-pixel chain only; no App or F0 to Idle test",
            "frames": {n: {"path": str(paths[n]), "pngSha256": digest(paths[n]),
                           "rgbaSha256": rgba_digest(images[n])} for n in NAMES},
            "landmarks": marks, "handGuides": hands, "pairs": pairs,
            "guideWarning": "Head guides include some neck/collar pixels; body band includes arms, not anatomical shoulder width. Registration x=96 is a canvas anchor, not every silhouette midpoint.",
            "observations": {
                "arms": "Small outward hand steps remain attached; the final step changes forearm inclination rather than teleporting hands.",
                "expression": "KF2 retains relaxed Gu eyes; F0 introduces sharp Feng brows/eyes, mouth/jaw and brighter hair in one step: FAIL.",
                "clothing": "Upper blue tailoring develops, but KF2 slim trousers and fragmentary jacket become complete thick blue suit/pants at F0: FAIL.",
                "footprint": "All baselines are 203; F0 has a different sole/stance outline. Numeric registration cannot prove pose continuity.",
            },
            "nextAction": "Keep F0 identity and frozen predecessors. Further manual face/garment/leg progression requires renewed art scope, not weaker geometry gates or App integration."}


def write(output: Path = DEST) -> dict:
    if output.exists():
        raise ValueError("refuse to overwrite full-chain evidence")
    report = assess()
    images, _ = frames()
    output.mkdir(parents=True)
    sheet = contact([images[n] for n in NAMES], list(NAMES))
    sheet.save(output / "contact-sheet.png")
    sheet.resize((sheet.width*3, sheet.height*3), Image.Resampling.NEAREST).save(
        output / "contact-sheet-nearest3x.png")
    for a, b in zip(NAMES, NAMES[1:]):
        # Blending is solely a QA overlay, never candidate material.
        Image.blend(images[a], images[b], 0.5).save(output / f"{a}-{b}-overlay.png")
    (output / "chain-report.json").write_text(json.dumps(report, indent=2)+"\n")
    return report


if __name__ == "__main__":
    print(write()["status"])
