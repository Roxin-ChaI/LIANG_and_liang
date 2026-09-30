"""Static, source-bound specification for the four Feng entrance poses."""
from __future__ import annotations

import json
from pathlib import Path

from PIL import Image

from tools.audit_f0_v2_entry import audit as entry_audit, require_morph_pass
from tools.f0_v2_spec import OUTPUT, sources
from tools.manual_f0_v2 import DEST as F0_DIR
from tools.prepare_transition_animation_candidate import digest
from tools.transition_bridge_spec import FROZEN, ROOT as PROJECT_ROOT

ROOT = OUTPUT / "feng-entry"
F0_PATH = F0_DIR / "F0-v2.png"
F0_SHA = "aac220fa47dd2a14a66928d98327fdec1a0d1a1d2cf43ac671fbd6342dc271f9"
B_SHA = "4ae8848d3a40e6c3d8507b7fda119d58462f3236b3202471239ee0b9c0ac506b"


def anchors() -> dict[str, Image.Image]:
    require_morph_pass()
    if digest(F0_PATH) != F0_SHA:
        raise ValueError("F0-v2 Morph anchor changed")
    with Image.open(F0_PATH) as image:
        f0 = image.copy()
    b = sources()["B"]
    if digest(PROJECT_ROOT / FROZEN["B"][0]) != B_SHA:
        raise ValueError("formal Feng Idle anchor changed")
    if any(i.size != (192,208) or i.mode != "RGBA" for i in (f0,b)):
        raise ValueError("native RGBA anchors required")
    return {"F0-v2":f0,"Idle B":b}


def specification() -> dict:
    prior = entry_audit()
    return {
        "status":"SPECIFICATION_ONLY","createdFrames":0,"canvas":[192,208],
        "baselineY":203,"registrationX":96,"sourceSha256":F0_SHA,"targetSha256":B_SHA,
        "entrySequence":["F0-v2","E1","E2","E3","Idle B"],
        "entryFrameCount":4,"F0ExcludedFromFrameCount":True,
        "headGuide":{"F0-v2":[63,4,113,59],"Idle B":[64,4,113,58],
                     "maxSizeDeltaEachStep":2,"maxCenterMovementEachStep":2,
                     "caveat":"B's chin is partly occluded by a finger; head guide is approximate"},
        "motions":{
            "E1":{"face":"first slight brow/eye focus; preserve both glasses and facial outline",
                  "leftHand":"begin upward movement from low hand; elbow remains attached",
                  "rightHand":"retain low hand","feet":"both feet near F0, weight prepares to transfer",
                  "suit":"small elbow and lapel fold response only"},
            "E2":{"face":"intermediate gaze, neither relaxed F0 nor abrupt full B",
                  "leftHand":"rise to mid chest with a readable elbow path",
                  "rightHand":"begin fist curl without abrupt relocation",
                  "feet":"one foot begins outward step, other remains support",
                  "suit":"sleeve, waist and lapel folds follow pose"},
            "E3":{"face":"near B expression but still same identity and head size",
                  "leftHand":"fingertips approach lip, no final teleport",
                  "rightHand":"near B fist position",
                  "feet":"both feet near final wide stance, consistent baseline",
                  "suit":"near-final tailored folds, stable torso volume"},
            "Idle B":{"face":"exact approved Feng Idle expression",
                      "leftHand":"finger completes lip contact", "feet":"exact approved wide stance",
                      "source":"approved B pixels exactly, never modified"}
        },
        "trajectoryGuides":{"leftFootCenterX":[82.5,82.5,74,68,65.5],
                            "rightFootCenterX":[109,109,116,125,127.5],
                            "leftSkinHandCenterApprox":[[69,143],[72,123],[78,100],[83,75],"target hand near lips"],
                            "guideOnly":True},
        "gates":{"perAdjacent":["head size and center stable", "same face and glasses",
                              "continuous left arm/elbow/hand trajectory", "continuous right fist and hand position",
                              "one foot supports each outward step", "trouser/thigh/calf volume reads as pose, not body morph",
                              "garment folds follow limb motion", "RGBA alpha binary, no clipping or holes"],
                 "E1E2StopOnFail":True,"E3RequiresE1E2Pass":True,
                 "fullStaticReviewRequired":True,"geometryAloneCannotApprove":True},
        "preservation":{"frozenKeyframesEditable":False,"F0Editable":False,
                        "formalAtlasEditable":False,"runtimeIntegration":False},
        "sourceEntryAuditStatus":prior["status"],
        "artApproval":"PENDING",
    }


def write(output: Path = ROOT / "spec") -> dict:
    anchors()
    report = specification()
    output.mkdir(parents=True,exist_ok=False)
    (output/"specification.json").write_text(json.dumps(report,indent=2)+"\n")
    return report


if __name__ == "__main__":
    print(write()["status"])
