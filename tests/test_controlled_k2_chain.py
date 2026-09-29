import json

import pytest

from tools.audit_controlled_k2_chain import K2_SHA, K3_SHA, prepare, resolve_chain
from tools.derive_controlled_transition_k2 import CANDIDATE


def test_chain_is_read_only_and_gated_by_actual_independent_k2_review(tmp_path):
    report = prepare(tmp_path/"chain")
    assert report["K1_K2"] == "K1_K2_STATIC_PASS"
    assert report["K2Sha256"] == K2_SHA and report["K3Sha256"] == K3_SHA
    assert report["K2_K3"]["headSize"]["deltaApprox"] == [-16, -22]
    assert report["K2_K3"]["headCenter"]["deltaApprox"] == [2, -11]
    assert report["K2_K3"]["bodyBandBbox"]["delta"] == [-20, 0, 25, 0]
    # This fixed shoulder-cap band excludes the wider lower hand/stance extrema.
    assert report["K2_K3"]["shoulderCapBand"]["widthDelta"] == 42
    assert report["newPosesGenerated"] == 0 and not report["K3Modified"]
    assert not (tmp_path/"chain/K3.png").exists()
    assert not report["runtimeEligible"]
    with pytest.raises(ValueError, match="overwrite"):
        prepare(tmp_path/"chain")


@pytest.mark.parametrize("review", [{}, {"verdict": "K1_K2_STATIC_PASS", "reviewer": "fixture", "reviewedRgbaSha256": "stale"}])
def test_chain_cannot_be_opened_by_missing_or_stale_review(tmp_path, review):
    path = tmp_path/"review.json"
    path.write_text(json.dumps(review))
    with pytest.raises(ValueError, match="STATIC_PASS"):
        prepare(tmp_path/"chain", path)
    assert not (tmp_path/"chain").exists()


def test_unknown_visual_failure_and_stale_chain_hash_never_become_rework_verdict(tmp_path):
    report = prepare(tmp_path/"chain")
    assert resolve_chain(report, {})["status"] == "CHAIN_NOT_VERIFIED"
    review = {"reviewer": "TEST FIXTURE", "verdict": "K3_REWORK_REQUIRED", "K1_K2": "PASS", "K2_K3": "FAIL",
              "reviewedK2RgbaSha256": report["K2RgbaSha256"], "reviewedK3RgbaSha256": "stale"}
    assert resolve_chain(report, review)["status"] == "CHAIN_NOT_VERIFIED"
    review["reviewedK3RgbaSha256"] = report["K3RgbaSha256"]
    verdict = resolve_chain(report, review)
    assert verdict["status"] == "K3_REWORK_REQUIRED"
    assert verdict["userK2ArtApproval"] == "PENDING" and not verdict["runtimeEligible"]


def test_actual_k2_review_is_pixel_bound_not_a_synthetic_runtime_claim():
    review = json.loads((CANDIDATE/"qa/independent-review.json").read_text())
    assert review["reviewer"] == "controlled_k2_visual"
    assert review["reviewedRgbaSha256"] == "3462ff0391745732801c58d2538f50c78a66b0bc39d66beabef8efc7d5b30e98"
    assert "No K3 review" in review["scope"]
