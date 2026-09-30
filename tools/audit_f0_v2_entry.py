"""Audit the neutral Morph endpoint against Feng Idle; generate no entry art."""
from __future__ import annotations

import json
from pathlib import Path

from PIL import Image

from tools.f0_v2_spec import OUTPUT, HEAD, sources
from tools.gate_f0_v2 import audit as morph_audit, resolve, REVIEW
from tools.manual_f0_v2 import DEST
from tools.manual_kf1_pixel_art import contact
from tools.prepare_transition_animation_candidate import digest
from tools.transition_bridge_spec import B_HEAD, FROZEN, ROOT, landmark

OUT = OUTPUT / "entry-audit"


def require_morph_pass() -> dict:
    report = resolve(morph_audit(),json.loads(REVIEW.read_text()))
    if not report["entryAuditAllowed"]:
        raise ValueError("fresh F0 Morph PASS required for Entry audit")
    return report


def foot_guides(image: Image.Image) -> dict:
    result = {}
    for name,x0,x1 in (("left",0,96),("right",96,192)):
        b = image.getchannel("A").crop((x0,192,x1,208)).getbbox()
        if b is None:
            raise ValueError("missing foot guide")
        box = [b[0]+x0,b[1]+192,b[2]+x0,b[3]+192]
        result[name] = {"bbox":box,"centerX":(box[0]+box[2])/2}
    return result


def audit() -> dict:
    approved = require_morph_pass()
    b = sources()["B"]
    with Image.open(DEST / "F0-v2.png") as image:
        f0 = image.copy()
    marks = {"F0-v2":landmark(f0,HEAD,approximate=True),"B":landmark(b,B_HEAD,approximate=True)}
    feet = {"F0-v2":foot_guides(f0),"B":foot_guides(b)}
    return {
        "status":"ENTRY_VISUAL_REVIEW_REQUIRED", "morphStatus":approved["status"],
        "sourceSha256":digest(DEST / "F0-v2.png"),"targetSha256":digest(ROOT / FROZEN["B"][0]),
        "landmarks":marks,"footGuides":feet,
        "delta":{"headSize":[b-a for a,b in zip(marks["F0-v2"]["headSize"],marks["B"]["headSize"])],
                 "headCenter":[b-a for a,b in zip(marks["F0-v2"]["headCenter"],marks["B"]["headCenter"])],
                 "bodyBandWidth":marks["B"]["bodyWidth"]-marks["F0-v2"]["bodyWidth"],
                 "feetCenterX":{side:feet["B"][side]["centerX"]-feet["F0-v2"][side]["centerX"] for side in ("left","right")}},
        "guideWarning":"Body band includes raised arms; head includes a partly hand-occluded chin in B. Numbers cannot prove limb-volume equivalence under different poses.",
        "entryPlan":{
            "plannedPoseCount":4,"generatedPoses":0,"isPartOfMorphBudget":False,
            "E1":"Begin raising viewer-left forearm from the low pose; slight brow engagement. Keep skull/shoulders and foot registration stable; prepare weight transfer.",
            "E2":"Forearm reaches mid chest; progressively focus eyes. One foot begins the outward step; jacket folds follow the moving elbow.",
            "E3":"Fingertips approach the chin, expression nears B. The other foot completes the wider stance; trouser contours follow leg rotation rather than inflating volume.",
            "E4":"Settle into the exact frozen B pose, completing the fingertip contact, fist and suit detailing. No final-frame body rescale or newly replaced face.",
            "constraints":["Each adjacent step needs actual manual visual QA", "Head size/center remain near the already Feng endpoint", "Track hand trajectory and planted/supporting feet", "Do not hide another body-form change inside Entry", "Do not use speed changes to conceal a bad connection"],
        },
        "runtimeIntegrationAllowed":False,"entryArtApproved":False,"humanApproval":"PENDING",
    }


def resolve_entry(report: dict, review: dict) -> dict:
    fresh = (review.get("sourceSha256") == report["sourceSha256"]
             and review.get("targetSha256") == report["targetSha256"])
    required = ("expression","armTrajectory","stance","suitDetails","formProportions")
    channels = review.get("checks",{})
    complete = bool(review.get("reviewer")) and all(channels.get(k,{}).get("status") in ("PASS","FAIL","NOT_PROVEN") for k in required)
    direct = fresh and complete and all(channels[k]["status"] == "PASS" for k in required)
    status = ("F0_TO_IDLE_PASS" if direct else "FENG_ENTRY_ANIMATION_REQUIRED") if fresh and complete else "ENTRY_AUDIT_NOT_VERIFIED"
    return {**report,"status":status,"reviewFresh":fresh,"directConnectionPass":direct,
            "visualReview":review,"entryArtApproved":False}


def write(output: Path = OUT) -> dict:
    report = audit()
    review_path = output / "visual-review.json"
    if review_path.exists():
        report = resolve_entry(report,json.loads(review_path.read_text()))
    output.mkdir(parents=True,exist_ok=True)
    with Image.open(DEST / "F0-v2.png") as image:
        f0 = image.copy()
    b = sources()["B"]
    sheet = contact([sources()["KF2"],f0,b],["KF2","F0-v2 / Morph done","B / Feng Idle"])
    sheet.save(output / "contact-sheet.png")
    sheet.resize((sheet.width*3,sheet.height*3),Image.Resampling.NEAREST).save(output / "contact-sheet-nearest3x.png")
    Image.blend(f0,b,0.5).save(output / "F0-v2-B-overlay.png")
    (output / "entry-audit.json").write_text(json.dumps(report,indent=2)+"\n")
    return report


if __name__ == "__main__":
    print(write()["status"])
