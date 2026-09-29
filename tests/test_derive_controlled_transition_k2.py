import copy
import json

import pytest

from tools.controlled_transition_k2 import assess, masks, source
from PIL import Image

from tools.derive_controlled_transition_k2 import CANDIDATE, PLAN, STATIC_CHECKS, apply_plan, prepare, resolve_review
from tools.locked_transition_k1 import masked_bytes, sha


def candidate():
    return apply_plan(source(), json.loads(PLAN.read_text()))


def review(image):
    return {"reviewer": "TEST FIXTURE ONLY", "verdict": "K1_K2_STATIC_PASS",
            "reviewedRgbaSha256": sha(image.tobytes()), "checks": {key: "PASS" for key in STATIC_CHECKS}}


def test_local_candidate_is_deterministic_native_and_all_locked_bytes_match():
    k1, k2 = source(), candidate()
    assert k2.tobytes() == candidate().tobytes()
    assert k2.mode == "RGBA" and k2.size == (192, 208)
    locked, _ = masks()
    assert masked_bytes(k1, locked) == masked_bytes(k2, locked)
    report = assess(k2)
    assert report["technicalPass"]
    assert report["headSize"] == [68, 80] and report["headCenterDelta"] == [0, 0]
    # K1 right-edge maximum is on a different row than the4px upper-arm plateau.
    # Measure actual alpha hull, not the nominal symmetric movement instruction.
    assert report["bodyEdgeExpansion"] == [4, 3]
    assert report["shoulderCapBand"]["widthGrowth"] == 8
    assert report["baselineY"] == 203
    assert not report["localChainAllowed"]


def test_changed_pixels_are_entirely_native_cloth_donors_not_invented_colors():
    k1, k2 = source(), candidate()
    assert set(k2.get_flattened_data()) <= set(k1.get_flattened_data())
    assert k1.crop((0, 140, 192, 208)).tobytes() == k2.crop((0, 140, 192, 208)).tobytes()
    assert k1.crop((0, 0, 192, 84)).tobytes() == k2.crop((0, 0, 192, 84)).tobytes()


@pytest.mark.parametrize("mutation", ["wholeSide", "largeMove", "jumpProfile", "overlap", "substituteK1"])
def test_bounded_plan_rejects_scaling_substitution_and_bad_profiles(mutation):
    plan = copy.deepcopy(json.loads(PLAN.read_text()))
    k1 = source()
    if mutation == "wholeSide":
        plan["leftSourceColumns"] = [0, 84]
    elif mutation == "largeMove":
        plan["rowBands"][3]["outwardPixels"] = 5
    elif mutation == "jumpProfile":
        plan["rowBands"][0]["outwardPixels"] = 3
    elif mutation == "overlap":
        plan["rowBands"][1]["y"][0] = 87
    else:
        k1.putpixel((80, 25), (0, 0, 0, 255))
    with pytest.raises(ValueError):
        apply_plan(k1, plan)


def test_numeric_pass_cannot_open_chain_without_fresh_independent_review():
    k2 = candidate()
    assert resolve_review(k2, {})["status"] == "K2_STATIC_NOT_VERIFIED"
    stale = review(k2)
    stale["reviewedRgbaSha256"] = "stale"
    assert not resolve_review(k2, stale)["localChainAllowed"]
    incomplete = review(k2)
    incomplete["checks"].pop("shoulderGrowthGradual")
    assert not resolve_review(k2, incomplete)["localChainAllowed"]


def test_fresh_review_allows_only_local_static_chain_not_user_or_runtime_approval():
    k2 = candidate()
    report = resolve_review(k2, review(k2))
    assert report["status"] == "K1_K2_STATIC_PASS" and report["localChainAllowed"]
    assert report["userArtApproval"] == "PENDING" and not report["runtimeEligible"]


def test_nested_independent_review_status_retains_notes_but_requires_every_pass():
    k2 = candidate()
    report = review(k2)
    report["checks"] = {key: {"status": "PASS", "reason": "TEST FIXTURE"} for key in STATIC_CHECKS}
    assert resolve_review(k2, report)["localChainAllowed"]
    report["checks"]["bodyIntermediate"]["status"] = "UNKNOWN"
    assert not resolve_review(k2, report)["localChainAllowed"]


def test_reviewed_pixel_failure_cannot_be_overruled_by_static_pass_fixture():
    k2 = candidate()
    k2.putpixel((80, 25), (0, 0, 0, 255))
    assert resolve_review(k2, review(k2))["status"] == "K2_QA_FAIL"


def test_upper_hand_pixels_stay_locked_even_in_conservative_spec_edit_rectangle():
    k2 = candidate()
    k2.putpixel((75, 142), source().getpixel((76, 142)))
    assert not assess(k2)["checks"]["handsLowerBodyByteIdentical"]
    assert not resolve_review(k2, review(k2))["localChainAllowed"]


def test_emits_one_k2_only_with_native_rgba_and_refuses_overwrite(tmp_path):
    report = prepare(tmp_path/"candidate")
    assert report["technicalPass"] and report["newPoses"] == ["K2"]
    assert not (tmp_path/"candidate/K3.png").exists()
    assert report["lockedByteComparison"]["differentBytes"] == 0
    with pytest.raises(ValueError, match="overwrite"):
        prepare(tmp_path/"candidate")


def test_final_saved_candidate_matches_documented_plan_pixel_for_pixel():
    with Image.open(CANDIDATE/"K2.png") as final:
        assert final.tobytes() == candidate().tobytes()
    report = json.loads((CANDIDATE/"qa/landmark-report.json").read_text())
    assert report["candidateRgbaSha256"] == sha(candidate().tobytes())


def test_historical_first_draft_cannot_pass_stricter_hand_gate():
    with Image.open(CANDIDATE.parent/"candidate/K2.png") as draft:
        report = assess(draft.copy())
    assert not report["checks"]["handsLowerBodyByteIdentical"]
    assert not report["technicalPass"] and not report["localChainAllowed"]
