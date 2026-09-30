"""Do not approve a Feng Entry endpoint from geometry when the last cut fails."""
from __future__ import annotations

import json
from pathlib import Path

from PIL import Image

from tools.feng_entry_spec import B_SHA, anchors
from tools.manual_feng_entry_e3 import OUT, assess, source_frames
from tools.manual_feng_entry_e1_e2 import OUT as E1_E2_OUT
from tools.prepare_transition_animation_candidate import digest
from tools.audit_f0_v2_entry import foot_guides

REVIEW=OUT/"visual-review.json"
REQUIRED=("faceHair","headPosition","leftArmAndFinger","rightFist","stance","pantsVolume","suitStructure","alpha")


def widths(image:Image.Image)->dict:
    return {str(y):[sum(image.getpixel((x,y))[3]>0 for x in range(a,b))
                    for a,b in ((45,96),(97,148))] for y in (150,160,170,180)}


def audit()->dict:
    frames=source_frames()
    with Image.open(OUT/"E3.png") as image:e3=image.copy()
    report=json.loads(json.dumps(assess(e3)))
    if report != json.loads((OUT/"landmarks.json").read_text()):raise ValueError("stale E3 metrics")
    images={"E2":frames["E2"],"E3":e3,"B":frames["B"]}
    return {"technicalPass":report["technicalPass"],"E3":report,
            "sourceE2Sha256":digest(E1_E2_OUT/"E2.png"),
            "E3Sha256":digest(OUT/"E3.png"),"targetBSha256":B_SHA,
            "footGuides":{n:foot_guides(i) for n,i in images.items()},
            "opaqueLegWidthsByRow":{n:widths(i) for n,i in images.items()},
            "entryApproved":False,"fullChainAllowed":False}


def resolve(report:dict,review:dict)->dict:
    fresh=all(review.get(k)==report[k] for k in ("sourceE2Sha256","E3Sha256","targetBSha256"))
    visual={p:(review.get("pairs",{}).get(p,{}).get("verdict")=="PASS"
               and all(review["pairs"][p].get("checks",{}).get(c)=="PASS" for c in REQUIRED))
            for p in ("E2_E3","E3_B")}
    passed=bool(fresh and report["technicalPass"] and review.get("reviewer") and all(visual.values()))
    return {**report,"status":"FENG_ENTRY_ART_APPROVED" if passed else "ENTRY_QA_FAIL",
            "reviewFresh":fresh,"visualPairPass":visual,"entryApproved":passed,
            "fullChainAllowed":passed,"runtimeIntegrationAllowed":False,
            "scope":"static E3/Idle gate; no human approval or runtime playback"}


def write(output:Path=OUT)->dict:
    r=resolve(audit(),json.loads(REVIEW.read_text()))
    (output/"gate.json").write_text(json.dumps(r,indent=2)+"\n")
    return r


if __name__=="__main__":
    print(write()["status"])
