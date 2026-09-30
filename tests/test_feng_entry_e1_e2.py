import json
from copy import deepcopy

from tools.manual_feng_entry_e1_e2 import construct, assess, OUT
from tools.gate_feng_entry_e1_e2 import audit, resolve, REVIEW


def test_both_local_frames_keep_original_head_and_grounding():
    for name in ("E1","E2"):
        candidate, recipe=construct(name)
        r=assess(name,candidate)
        assert r["technicalPass"],r["checks"]
        assert r["landmark"]["headSize"]==[50,55]
        assert r["landmark"]["baselineY"]==203
        assert not recipe["wholeCharacterRotation"] and not recipe["colorInterpolation"]


def test_step_trajectory_moves_one_planted_foot_only():
    e1,e2=(assess(n,construct(n)[0]) for n in ("E1","E2"))
    assert e1["feet"]["left"]["centerX"]==82.5
    assert e2["feet"]["left"]["centerX"]==74.5
    assert e1["feet"]["right"]==e2["feet"]["right"]
    assert e1["hands"]["left"][1]>e2["hands"]["left"][1]
    assert e2["hands"]["right"][3]-e2["hands"]["right"][1]<e1["hands"]["right"][3]-e1["hands"]["right"][1]


def test_visual_fail_or_stale_frame_stops_e3():
    report=audit()
    review=json.loads(REVIEW.read_text())
    assert resolve(report,review)["E3Allowed"]
    stale=deepcopy(review);stale["E1Sha256"]="stale"
    assert not resolve(report,stale)["E3Allowed"]
    bad=deepcopy(review);bad["pairs"]["F0_E1"]["checks"]["armTrajectory"]="FAIL"
    assert resolve(report,bad)["status"]=="ENTRY_QA_FAIL"
