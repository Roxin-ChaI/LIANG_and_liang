"""Separate numeric Morph checks from recorded static semantic review."""
from __future__ import annotations

import json
from pathlib import Path

from PIL import Image, ImageDraw

from tools.f0_v2_spec import OUTPUT, SOURCE, sources
from tools.manual_f0_v2 import DEST, assess
from tools.prepare_transition_animation_candidate import digest

REVIEW = OUTPUT / "morph-gate/visual-review.json"
CHECKS = ("headContinuity", "completedFengForm", "face", "arms", "pants", "jacketStructure", "pixelIntegrity")


def audit() -> dict:
    with Image.open(DEST / "F0-v2.png") as image:
        report = json.loads(json.dumps(assess(image.copy())))
    stored = json.loads((DEST / "landmark-report.json").read_text())
    if stored != report:
        raise ValueError("candidate metrics no longer match stored evidence")
    return {**report, "sourceSha256":digest(SOURCE), "candidateSha256":digest(DEST / "F0-v2.png")}


def resolve(report: dict, review: dict) -> dict:
    fresh = (review.get("sourceSha256") == report["sourceSha256"]
             and review.get("candidateSha256") == report["candidateSha256"])
    semantic = {name:review.get("checks",{}).get(name,{}).get("status") == "PASS" for name in CHECKS}
    passed = bool(report["technicalPass"] and fresh and review.get("reviewer")
                  and review.get("scope") == "static Morph only" and review.get("verdict") == "PASS"
                  and all(semantic.values()))
    return {**report, "status":"F0_MORPH_ENDPOINT_APPROVED" if passed else "F0_V2_QA_FAIL",
            "reviewFresh":fresh, "semanticChecks":semantic,"morphApproved":passed,
            "entryAuditAllowed":passed,"humanApproval":"PENDING",
            "approvalScope":"project static Morph gate; not human approval, entry approval or runtime validation",
            "runtimeIntegrationAllowed":False}


def write(output: Path = OUTPUT / "morph-gate") -> dict:
    report = resolve(audit(),json.loads(REVIEW.read_text()))
    output.mkdir(parents=True,exist_ok=True)
    source = sources()["KF2"]
    with Image.open(DEST / "F0-v2.png") as image:
        candidate = image.copy()
    # Enlargements are exact nearest-neighbor views; they never become art.
    regions = [("face/head",(56,0,120,65)),("arms / suit",(40,59,151,155)),("pants / feet",(70,130,124,208))]
    sheet = Image.new("RGBA",(672,960),(28,28,32,255))
    draw = ImageDraw.Draw(sheet)
    y = 0
    for name,box in regions:
        draw.text((4,y+3),f"{name}: KF2 | F0-v2",fill="white")
        for n,frame in enumerate((source,candidate)):
            crop = frame.crop(box)
            sheet.alpha_composite(crop.resize((crop.width*3,crop.height*3),Image.Resampling.NEAREST),(n*336,y+20))
        y += (box[3]-box[1])*3+30
    sheet.crop((0,0,672,y)).save(output/"semantic-contact-sheet.png")
    (output/"gate.json").write_text(json.dumps(report,indent=2)+"\n")
    return report


if __name__ == "__main__":
    print(write()["status"])
