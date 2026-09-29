import json
from collections import deque

import pytest

from tools.derive_locked_transition_k1 import PLAN, STATIC_CHECKS, apply_plan, prepare, resolve_static_review
from tools.locked_transition_k1 import assess, masked_bytes, masks, sha
from tools.specify_transition_keyframes import approved_inputs


def test_local_plan_is_deterministic_and_head_neck_feet_are_exact_original():
    a = approved_inputs()[0][2]
    plan = json.loads(PLAN.read_text())
    k,operations = apply_plan(a,plan)
    second,_ = apply_plan(a,plan)
    assert k.tobytes() == second.tobytes() and k.tobytes() != a.tobytes()
    locked,_ = masks()
    assert masked_bytes(a,locked) == masked_bytes(k,locked)
    assert a.crop((0,0,192,90)).tobytes() == k.crop((0,0,192,90)).tobytes()
    assert a.crop((0,180,192,208)).tobytes() == k.crop((0,180,192,208)).tobytes()
    assert set(k.get_flattened_data()) <= set(a.get_flattened_data())
    assert assess(k)["technicalPass"]
    assert len(operations) == 2


@pytest.mark.parametrize("op", [
    {"sourceBox":[54,4,122,84],"integerDelta":[1,0]},
    {"sourceBox":[83,95,86,98],"integerDelta":[1,0]},
    {"sourceBox":[69,130,80,145],"integerDelta":[2,0]},
    {"sourceBox":[69,130,80,145],"integerDelta":[0.5,0]}
])
def test_invalid_or_locked_local_edits_stop_not_repair(op):
    with pytest.raises(ValueError):
        apply_plan(approved_inputs()[0][2],{"operations":[op]})


def test_prepare_emits_only_k1_with_required_byte_and_visual_evidence(tmp_path):
    report = prepare(tmp_path/"candidate")
    assert report["lockedByteComparison"]["differentBytes"] == 0
    assert report["headSize"] == [68,80]
    assert report["bodyEdgeDelta"] == [0,-1]
    assert report["shoulderGuideWidthDelta"] == 0
    assert report["baselineDelta"] == 0
    assert report["status"] == "AWAITING_INDEPENDENT_PIXEL_REVIEW"
    assert not report["AIUsed"] and not report["localChainAllowed"]
    assert not (tmp_path/"candidate/K2.png").exists()
    for name in ("difference-mask.png","overlay.png","contact-sheet.png","locked-region-byte-comparison.json","landmark-report.json"):
        assert (tmp_path/"candidate/qa"/name).exists()
    with pytest.raises(ValueError,match="overwrite"):
        prepare(tmp_path/"candidate")


def test_local_arm_pixel_moves_create_no_enclosed_transparent_seams():
    a = approved_inputs()[0][2]
    k,_ = apply_plan(a,json.loads(PLAN.read_text()))
    for image in (a,k):
        transparent = {(x,y) for y in range(208) for x in range(192) if not image.getpixel((x,y))[3]}
        reached = {p for p in transparent if p[0] in (0,191) or p[1] in (0,207)}
        queue = deque(reached)
        while queue:
            x,y = queue.popleft()
            for point in ((x-1,y),(x+1,y),(x,y-1),(x,y+1)):
                if point in transparent and point not in reached:
                    reached.add(point)
                    queue.append(point)
        assert transparent == reached


def test_independent_static_review_opens_audit_only_never_user_or_runtime_approval():
    k,_ = apply_plan(approved_inputs()[0][2],json.loads(PLAN.read_text()))
    review = {"reviewer":"unit-fixture-only","verdict":"A_K1_STATIC_PASS","reviewedRgbaSha256":sha(k.tobytes()),
              "checks":{key:{"status":"pass"} for key in STATIC_CHECKS}}
    result = resolve_static_review(k,review)
    assert result["localChainAllowed"] and result["status"] == "A_K1_STATIC_PASS"
    assert result["userArtApproval"] == "PENDING" and not result["runtimeEligible"]
    assert result["chargeIntent"] == "unknown"
    review["reviewedRgbaSha256"] = "stale"
    assert not resolve_static_review(k,review)["localChainAllowed"]
    review["reviewedRgbaSha256"] = sha(k.tobytes())
    review["checks"]["seamsAndHoles"]["status"] = "unknown"
    assert not resolve_static_review(k,review)["localChainAllowed"]
    review["checks"]["seamsAndHoles"]["status"] = "fail"
    assert resolve_static_review(k,review)["status"] == "K1_QA_FAIL"
