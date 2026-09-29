import copy
import json

import pytest

from tools import derive_transition_bridge_kb2 as kb2


def report():
    return json.loads((kb2.OUTPUT/"full-chain-qa/landmark-report.json").read_text())


def fixture(data):
    return {"reviewer":"TEST FIXTURE / NOT VISUAL QA", "KB2_B":"FAIL","faceIdentity":"PASS","armPoseContinuity":"FAIL",
            "kb2RgbaSha256":data["landmarks"]["KB2"]["rgbaSha256"],"bRgbaSha256":data["landmarks"]["B"]["rgbaSha256"]}


def test_all_seven_actual_landmarks_and_unhidden_residual(tmp_path):
    measured = kb2.full_chain_measure(tmp_path/"chain")
    assert list(measured["landmarks"]) == ["A","K1","K2","K3","KB1","KB2","B"]
    pair = measured["pairs"]["KB2_B"]
    assert pair["headSizeDelta"] == [-7,-14]
    assert pair["headCenterDelta"] == [0.5,-7]
    assert pair["bodyWidthDelta"] == 11
    assert not pair["numericPass"]
    assert pair["headEndpointUncertaintyPx"] == 3
    assert measured["pairs"]["A_K1"]["effectiveGatePass"]
    assert not measured["pairs"]["A_K1"]["newBridgeBudgetApplies"]
    assert all(measured["pairs"][name]["effectiveGatePass"] for name in ("K3_KB1","KB1_KB2"))
    assert measured["bridgeFramesGenerated"] == 2 and measured["additionalFramesGenerated"] == 0
    assert not (tmp_path/"chain/KB3.png").exists()


@pytest.mark.parametrize("review", [{},{"reviewer":"fixture","verdict":"KB2_QA_FAIL"},
                                   {"reviewer":"fixture","verdict":"KB1_KB2_STATIC_PASS","candidateRgbaSha256":"stale"}])
def test_no_full_chain_audit_after_missing_or_failed_kb2_review(tmp_path,review):
    path = tmp_path/"review.json"
    path.write_text(json.dumps(review))
    with pytest.raises(ValueError,match="STATIC_PASS"):
        kb2.full_chain_measure(tmp_path/"chain",path)
    assert not (tmp_path/"chain").exists()


def test_final_failure_never_claims_art_approval_or_permission_to_fill():
    data = report()
    resolved = kb2.resolve_final(data,fixture(data))
    assert resolved["status"] == "B_BRIDGE_QA_FAIL_MORE_ART_SCOPE_REQUIRED"
    assert resolved["actualBridgeFrames"] == 2
    assert resolved["nominalAdditionalBridgeLowerBound"] == 2
    assert not resolved["B_BRIDGE_ART_APPROVED"] and not resolved["twoBridgesSufficient"]
    assert not resolved["fullAnimationAllowed"] and not resolved["additionalBridgeFramesAuthorized"]


def test_false_visual_pass_cannot_override_final_numeric_failure():
    data = report()
    review = {**fixture(data),"KB2_B":"PASS","armPoseContinuity":"PASS"}
    resolved = kb2.resolve_final(data,review)
    assert not resolved["wholeChainStaticPass"] and not resolved["B_BRIDGE_ART_APPROVED"]


def test_stale_final_review_never_approves_chain():
    data = report()
    review = {**fixture(data),"kb2RgbaSha256":"wrong"}
    assert kb2.resolve_final(data,review)["status"] == "B_BRIDGE_NOT_VERIFIED"


@pytest.mark.parametrize("field", ["earlyLandmark","outgoingBudget"])
def test_finalization_rechecks_whole_chain_not_only_tail(field):
    data = report()
    forged = copy.deepcopy(data)
    if field == "earlyLandmark":
        forged["landmarks"]["A"]["headSize"] = [40,50]
    else:
        forged["pairs"]["KB2_B"]["numericPass"] = True
    with pytest.raises(ValueError,match="altered"):
        kb2.resolve_final(forged,fixture(data))
