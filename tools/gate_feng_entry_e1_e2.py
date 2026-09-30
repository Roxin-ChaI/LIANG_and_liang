"""Fresh static art gate for F0-v2→E1→E2; never approves E3 by geometry."""
from __future__ import annotations

import json
from pathlib import Path

from PIL import Image

from tools.feng_entry_spec import F0_SHA, F0_PATH
from tools.manual_feng_entry_e1_e2 import OUT, assess, construct
from tools.prepare_transition_animation_candidate import digest

REVIEW = OUT / "visual-review.json"
REQUIRED = ("identity", "head", "armTrajectory", "fist", "expression", "stance", "legVolume", "suit", "alpha")


def audit() -> dict:
    if digest(F0_PATH) != F0_SHA: raise ValueError("F0 changed")
    stored=json.loads((OUT/"landmarks.json").read_text())
    reports={}
    for name in ("E1","E2"):
        with Image.open(OUT/f"{name}.png") as image:
            report=json.loads(json.dumps(assess(name,image.copy())))
        if report != stored[name]: raise ValueError(f"stale {name} metrics")
        reports[name]=report
    hand_centers={name:[[(b[0]+b[2])/2,(b[1]+b[3])/2] for b in (reports[name]["hands"]["left"],reports[name]["hands"]["right"])] for name in reports}
    return {"sourceSha256":F0_SHA,"E1Sha256":digest(OUT/"E1.png"),"E2Sha256":digest(OUT/"E2.png"),
            "reports":reports,"handCenters":hand_centers,"E3Allowed":False}


def resolve(report: dict, review: dict) -> dict:
    fresh=(report["sourceSha256"]==review.get("sourceSha256")
           and report["E1Sha256"]==review.get("E1Sha256")
           and report["E2Sha256"]==review.get("E2Sha256"))
    visual={key:(review.get("pairs",{}).get(key,{}).get("verdict")=="PASS"
                 and all(review["pairs"][key].get("checks",{}).get(channel)=="PASS" for channel in REQUIRED))
            for key in ("F0_E1","E1_E2")}
    technical=all(r["technicalPass"] for r in report["reports"].values())
    passed=bool(fresh and technical and review.get("reviewer") and all(visual.values()))
    return {**report,"status":"ENTRY_E1_E2_STATIC_PASS" if passed else "ENTRY_QA_FAIL",
            "visualPairPass":visual,"reviewFresh":fresh,"E3Allowed":passed,
            "artApprovalScope":"project static E1/E2 gate only; no human final approval, E3 or runtime"}


def write(output: Path=OUT) -> dict:
    report=resolve(audit(),json.loads(REVIEW.read_text()))
    (output/"gate.json").write_text(json.dumps(report,indent=2)+"\n")
    return report


if __name__=="__main__":
    print(write()["status"])
