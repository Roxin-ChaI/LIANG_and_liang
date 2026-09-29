import copy
import json

from PIL import Image
import pytest

from tools.controlled_transition_k3 import assess, masks, source
from tools.derive_controlled_transition_k3 import CANDIDATE, PLAN, STATIC_CHECKS, apply_plan, prepare, resolve_review
from tools.locked_transition_k1 import masked_bytes, sha


def candidate():
    return apply_plan(source(),json.loads(PLAN.read_text()))


def review(image):
    return {"reviewer": "TEST FIXTURE ONLY", "verdict": "K2_K3_STATIC_PASS",
            "reviewedRgbaSha256": sha(image.tobytes()), "checks": {key: "PASS" for key in STATIC_CHECKS}}


def test_native_deterministic_derivation_preserves_locked_bytes_and_grows_gradually():
    k2,k3 = source(),candidate()
    assert k3.mode == "RGBA" and k3.size == (192,208)
    assert k3.tobytes() == candidate().tobytes()
    locked,_ = masks()
    assert masked_bytes(k2,locked) == masked_bytes(k3,locked)
    report = assess(k3)
    assert report["technicalPass"]
    assert report["headSize"] == [68,80] and report["headCenterDelta"] == [0,0]
    assert report["bodyEdgeExpansion"] == [5,5]
    assert report["bodyWidthGrowth"] == 10
    assert report["shoulderCapBand"]["widthGrowth"] == 10
    assert report["baselineY"] == 203
    assert not report["localChainAllowed"] and not report["runtimeEligible"]


def test_original_palette_and_all_head_hands_lower_body_pixels_remain_exact():
    k2,k3 = source(),candidate()
    assert set(k3.get_flattened_data()) <= set(k2.get_flattened_data())
    for box in ((0,0,192,84),(0,140,192,208),(84,84,103,101)):
        assert k2.crop(box).tobytes() == k3.crop(box).tobytes()


@pytest.mark.parametrize("mutation", ["wholeSide","largeMove","profileJump","overlap","outOfOrder","missingRows","substituteK2","claimAI"])
def test_bad_plans_fail_without_scaling_approved_source_or_relaxing_identity(mutation):
    plan = copy.deepcopy(json.loads(PLAN.read_text()))
    k2 = source()
    if mutation == "wholeSide":
        plan["leftSourceColumns"] = [0,84]
    elif mutation == "largeMove":
        plan["rowBands"][4]["outwardPixels"] = 7
    elif mutation == "profileJump":
        plan["rowBands"][0]["outwardPixels"] = 3
    elif mutation == "overlap":
        plan["rowBands"][1]["y"][0] = 86
    elif mutation == "outOfOrder":
        plan["rowBands"][1],plan["rowBands"][2] = plan["rowBands"][2],plan["rowBands"][1]
    elif mutation == "missingRows":
        plan["rowBands"].pop()
    elif mutation == "substituteK2":
        k2.putpixel((80,25),(0,0,0,255))
    else:
        plan["aiGeneration"] = True
    with pytest.raises(ValueError):
        apply_plan(k2,plan)


def test_incomplete_or_stale_review_cannot_open_b_chain_audit():
    k3 = candidate()
    assert resolve_review(k3,{})["status"] == "K3_STATIC_NOT_VERIFIED"
    stale = review(k3)
    stale["reviewedRgbaSha256"] = "stale"
    assert not resolve_review(k3,stale)["localChainAllowed"]
    missing = review(k3)
    missing["checks"].pop("bodyPoseProgressive")
    assert not resolve_review(k3,missing)["localChainAllowed"]


def test_complete_review_only_opens_static_chain_not_final_art_or_runtime():
    k3 = candidate()
    evidence = review(k3)
    evidence["checks"] = {key: {"status": "PASS","reason": "TEST FIXTURE"} for key in STATIC_CHECKS}
    report = resolve_review(k3,evidence)
    assert report["status"] == "K2_K3_STATIC_PASS" and report["localChainAllowed"]
    assert report["userK3ArtApproval"] == "PENDING" and not report["runtimeEligible"]
    evidence["checks"]["bodyPoseProgressive"]["status"] = "UNKNOWN"
    assert not resolve_review(k3,evidence)["localChainAllowed"]


def test_head_byte_failure_cannot_be_overruled_by_review_fixture():
    k3 = candidate()
    k3.putpixel((80,25),(0,0,0,255))
    assert resolve_review(k3,review(k3))["status"] == "K3_QA_FAIL"


def test_outputs_one_native_k3_and_no_bridge_or_full_animation(tmp_path):
    report = prepare(tmp_path/"candidate")
    assert report["newPoses"] == ["K3"] and report["technicalPass"]
    assert not (tmp_path/"candidate/B.png").exists()
    assert not (tmp_path/"candidate/frames").exists()
    with pytest.raises(ValueError,match="overwrite"):
        prepare(tmp_path/"candidate")


def test_saved_final_candidate_matches_exact_plan_and_report():
    k3 = candidate()
    with Image.open(CANDIDATE/"K3.png") as final:
        assert final.tobytes() == k3.tobytes()
    report = json.loads((CANDIDATE/"qa/landmark-report.json").read_text())
    assert report["candidateRgbaSha256"] == sha(k3.tobytes())
