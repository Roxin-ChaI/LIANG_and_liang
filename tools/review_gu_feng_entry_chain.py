"""Source-bound full static chain review; failed Entry remains a release stop."""
from __future__ import annotations

import json
from pathlib import Path

from PIL import Image

from tools.f0_v2_spec import OUTPUT, HEAD as F0_HEAD
from tools.feng_entry_spec import F0_PATH,F0_SHA,B_SHA
from tools.manual_feng_entry_e1_e2 import OUT as E12
from tools.manual_feng_entry_e3 import OUT as E3_OUT, E3_HEAD
from tools.gate_feng_entry_e1_e2 import audit as early_audit, resolve as early_resolve, REVIEW as EARLY_REVIEW
from tools.gate_feng_entry_e3 import audit as late_audit, resolve as late_resolve, REVIEW as LATE_REVIEW
from tools.gate_f0_v2 import audit as morph_audit, resolve as morph_resolve, REVIEW as MORPH_REVIEW
from tools.manual_kf1_pixel_art import contact
from tools.prepare_transition_animation_candidate import digest,metrics
from tools.review_f0_morph_chain import assess as previous_chain
from tools.transition_bridge_spec import FROZEN, ROOT, frozen_images, landmark, B_HEAD
from tools.locked_transition_k1 import HEAD as GU_HEAD
from tools.f0_morph_bridge import HEAD_GUIDES

OUT=OUTPUT/"feng-entry/full-chain-qa"
NAMES=("A","K1","K2","K3","KB1","KB2","KF1","KF2","F0-v2","E1","E2","E3","Idle B")
GUD={"A":GU_HEAD,"K1":GU_HEAD,"K2":GU_HEAD,"K3":GU_HEAD,
     "KB1":[57,4,119,78],"KB2":HEAD_GUIDES["KB2"],
     "KF1":HEAD_GUIDES["KF1"],"KF2":HEAD_GUIDES["KF2"],
     "F0-v2":F0_HEAD,"E1":F0_HEAD,"E2":F0_HEAD,"E3":E3_HEAD,"Idle B":B_HEAD}
DERIVED={
    "KB1":("assets/rework/v0.1.0/transition-keyframes/k3-b-bridge/kb1/KB1.png","4d1b307e3e251352d3cc165c95f85009d445f797efd94bfeb28fe682a30cd837"),
    "KB2":("assets/rework/v0.1.0/transition-keyframes/k3-b-bridge/kb2/KB2.png","622c81f99cde42f5846044a391424e7f4a8afa326d2c5e235470b2cacb618b19"),
    "KF1":("assets/rework/v0.1.0/transition-keyframes/feng-f0/morph-bridge/kf1/KF1.png","c189516b94db095e71a83460c7f2e831ca44841a6c97564f48252445ade1407b"),
    "KF2":("assets/rework/v0.1.0/transition-keyframes/feng-f0/morph-bridge/kf2/KF2.png","1917e459ee6554d29625649c15a87edd7f4029b42338a8645304cab5fa847676"),
    "F0-v2":(str(F0_PATH.relative_to(ROOT)),F0_SHA),
    "E1":(str((E12/"E1.png").relative_to(ROOT)),"bd9c0bbd6c9672e67322ea9d0581d8f3985fcc933ac8801c011a6d11623c9b8c"),
    "E2":(str((E12/"E2.png").relative_to(ROOT)),"387b3ac21644c5bf8a33c4cbef8e05e4fa574622cbb12d0347ad1a9b6577901d"),
    "E3":(str((E3_OUT/"E3.png").relative_to(ROOT)),"028468cb2ff10c6486ba1defa18d3401b0bc0acb648376da962462f4a879286b"),
}


def frames()->tuple[dict,dict]:
    frozen=frozen_images()
    images={"A":frozen["A"],"K1":frozen["K1"],"K2":frozen["K2"],
            "K3":frozen["K3"],"Idle B":frozen["B"]}
    paths={name:ROOT/FROZEN[name][0] for name in ("A","K1","K2","K3")}
    paths["Idle B"]=ROOT/FROZEN["B"][0]
    if digest(paths["Idle B"])!=B_SHA:raise ValueError("approved Idle B changed")
    for name,(relative,expected) in DERIVED.items():
        path=ROOT/relative
        if digest(path)!=expected:raise ValueError(f"reviewed {name} changed")
        with Image.open(path) as image:
            if image.mode!="RGBA" or image.size!=(192,208):raise ValueError(f"native {name} required")
            images[name]=image.copy()
        paths[name]=path
    return images,paths


def verdict(pairs:dict)->dict:
    morph=all(pairs[f"{a}_{b}"]["visualPass"] for a,b in zip(NAMES[:9],NAMES[1:9]))
    entry=all(pairs[f"{a}_{b}"]["visualPass"] for a,b in zip(NAMES[8:],NAMES[9:]))
    final=morph and entry and len(pairs)==12
    return {"morphStaticPass":morph,"entryStaticPass":entry,
            "status":"GU_TO_FENG_STATIC_CHAIN_APPROVED" if final else "VISUAL_QA_FAIL",
            "fullChainApproved":final,"runtimeIntegrationAllowed":False}


def assess()->dict:
    images,paths=frames()
    old=previous_chain()
    morph=morph_resolve(morph_audit(),json.loads(MORPH_REVIEW.read_text()))
    early=early_resolve(early_audit(),json.loads(EARLY_REVIEW.read_text()))
    late=late_resolve(late_audit(),json.loads(LATE_REVIEW.read_text()))
    if not morph["morphApproved"] or not early["E3Allowed"] or not late["reviewFresh"]:
        raise ValueError("stale previous art gates")
    marks={n:landmark(images[n],list(GUD[n]),approximate=True) for n in NAMES}
    framechecks={n:{"baseline203":marks[n]["baselineY"]==203,
                    "notClipped":not metrics(images[n])["touchesCellEdge"],
                    "nativeRGBA":images[n].mode=="RGBA" and images[n].size==(192,208)} for n in NAMES}
    pairs={}
    for index,(a,b) in enumerate(zip(NAMES,NAMES[1:])):
        key=f"{a}_{b}"
        if index<3:
            # These selected and frozen A/K1/K2/K3 links are user-approved in
            # the current task. Historical one-stage fail reports predate the
            # later replacement candidates; do not import those stale FAILs.
            visual=True;source="current user-approved keyframe baseline; frozen SHA checked"
        elif index<7:
            p=old["pairs"][key]
            visual=bool(p["visualPass"] and p["reviewFresh"])
            source="hash-bound prior independent bridge review"
        elif index==7:
            visual=bool(morph["morphApproved"])
            source="F0-v2 static Morph gate"
        elif index in (8,9):
            visual=bool(early["visualPairPass"][key.replace("F0-v2","F0")])
            source="E1/E2 static art gate"
        else:
            visual=bool(late["visualPairPass"][key.replace("Idle B","B")])
            source="E3/Idle static art gate"
        pairs[key]={"visualPass":visual,"source":source,
                    "headSizeDelta":[v-u for u,v in zip(marks[a]["headSize"],marks[b]["headSize"])],
                    "headCenterDelta":[v-u for u,v in zip(marks[a]["headCenter"],marks[b]["headCenter"])],
                    "bodyBandWidthDelta":marks[b]["bodyWidth"]-marks[a]["bodyWidth"],
                    "baselineDelta":marks[b]["baselineY"]-marks[a]["baselineY"]}
    failed=[key for key,value in pairs.items() if not value["visualPass"]]
    return {**verdict(pairs),"frames":{n:{"path":str(paths[n]),"sha256":digest(paths[n])} for n in NAMES},
            "frameChecks":framechecks,"landmarks":marks,"pairs":pairs,
            "blockingPairs":failed,"knownIssue":"Last cut changes face/hair, finger/arm, full suit and trouser volume together; y150 leg widths E3 13/13 vs B 21/25.",
            "scope":"static visual evidence only; no App runtime playback or human final approval"}


def write(output:Path=OUT)->dict:
    if output.exists():raise ValueError("refuse to overwrite full-chain QA")
    report=assess()
    images,_=frames()
    output.mkdir(parents=True)
    sheet=contact([images[n] for n in NAMES],list(NAMES))
    sheet.save(output/"contact-sheet.png")
    sheet.resize((sheet.width*3,sheet.height*3),Image.Resampling.NEAREST).save(output/"contact-sheet-nearest3x.png")
    for a,b in zip(NAMES,NAMES[1:]):
        Image.blend(images[a],images[b],0.5).save(output/f"{a}-{b}-overlay.png")
    (output/"chain-report.json").write_text(json.dumps(report,indent=2)+"\n")
    return report


if __name__=="__main__":
    print(write()["status"])
