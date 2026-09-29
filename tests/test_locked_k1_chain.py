import json

from PIL import Image
import pytest

from tools.audit_locked_k1_chain import K2, K2_SHA, compare, prepare
from tools.locked_transition_k1 import OUTPUT
from tools.prepare_transition_animation_candidate import digest


def test_actual_local_chain_compares_unchanged_k2_without_new_pose_generation(tmp_path):
    before = K2.read_bytes()
    result = prepare(tmp_path/"audit")
    assert result["A_K1"] == "A_K1_STATIC_PASS"
    assert result["K1_K2"]["shoulderGuideWidth"]["deltaApprox"] == 29
    assert result["K1_K2"]["bodyBandBbox"]["delta"] == [-16,0,18,0]
    assert result["K1_K2"]["headCenter"]["deltaApprox"] == [7.5,-9.5]
    assert result["K1_K2"]["baselineDelta"] == 0
    assert not result["runtimeEligible"] and result["newPosesGenerated"] == 0
    assert K2.read_bytes() == before and digest(K2) == K2_SHA
    assert not (tmp_path/"audit/K2.png").exists()


def test_static_prerequisite_failure_never_emits_chain_evidence(tmp_path):
    review = json.loads((OUTPUT/"candidate/qa/independent-review.json").read_text())
    review["checks"]["AtoK1Continuity"]["status"] = "fail"
    file = tmp_path/"unit-failed-review.json"
    file.write_text(json.dumps(review))
    with pytest.raises(ValueError,match="A_K1_STATIC_PASS"):
        prepare(tmp_path/"audit",file)
    assert not (tmp_path/"audit").exists()


def test_existing_k2_anatomy_estimates_are_not_silently_relabelled_as_exact():
    with Image.open(OUTPUT/"candidate/K1.png") as k1, Image.open(K2) as k2:
        report = compare(k1,k2)
    assert report["historicalK2AnnotationUncertaintyPx"] == 3
    assert "deltaApprox" in report["headSize"]
    assert "automatic visual FAIL" in report["warning"]


def test_retained_visual_verdict_never_claims_human_or_runtime_approval():
    final = json.loads((OUTPUT/"chain-qa/final-verdict.json").read_text())
    independent = json.loads((OUTPUT/"chain-qa/independent-review.json").read_text())
    assert final["status"] == independent["K1_K2_static_verdict"] == "K2_REWORK_REQUIRED"
    assert final["A_K1"] == independent["A_K1_static_verdict"] == "A_K1_STATIC_PASS"
    assert final["K1UserArtApproval"] == "PENDING"
    assert not final["runtimeEligible"] and not final["fullAnimationApproved"]
    assert not final["K1ModifiedToAccommodateK2"] and not final["K2K3Modified"]
