import copy
import json

import pytest

from tools import audit_transition_bridge as audit


def fixture(report):
    return {"reviewer":"TEST FIXTURE / NOT REAL VISUAL QA", "KB1_B":"FAIL",
            "kb1RgbaSha256":report["KB1"]["rgbaSha256"], "bRgbaSha256":report["B"]["rgbaSha256"],
            "faceIdentity":"FAIL","armPoseContinuity":"FAIL"}


def test_measured_residual_requires_second_bridge_without_touching_sources(tmp_path):
    output = tmp_path/"gate"
    report = audit.prepare(output)
    assert report["pair"]["headSizeDelta"] == [-13,-20]
    assert report["pair"]["headCenterDelta"] == [0.5,-10]
    assert report["pair"]["bodyWidthDelta"] == 23
    assert not report["pair"]["numericPass"]
    assert report["newPosesGenerated"] == 0
    assert not report["BModified"] and not report["KB1ModifiedForB"]
    assert (output/"full-chain-contact-sheet.png").exists()
    with pytest.raises(ValueError,match="overwrite"):
        audit.prepare(output)


@pytest.mark.parametrize("review", [{},{"reviewer":"fixture","candidateRgbaSha256":"stale"},
                                   {"reviewer":"fixture","verdict":"KB1_QA_FAIL"}])
def test_missing_stale_or_failed_incoming_review_stops_before_output(tmp_path,review):
    path = tmp_path/"review.json"
    path.write_text(json.dumps(review))
    with pytest.raises(ValueError,match="STATIC_PASS"):
        audit.prepare(tmp_path/"gate",path)
    assert not (tmp_path/"gate").exists()


def test_missing_or_stale_outgoing_review_cannot_authorize_kb2(tmp_path):
    report = audit.prepare(tmp_path/"gate")
    assert audit.resolve(report,{})["status"] == "ENDPOINT_NOT_VERIFIED"
    stale = {**fixture(report),"bRgbaSha256":"wrong"}
    assert not audit.resolve(report,stale)["KB2Allowed"]
    resolved = audit.resolve(report,fixture(report))
    assert resolved["status"] == "KB2_REQUIRED" and resolved["KB2Allowed"]
    assert not resolved["B_BRIDGE_ART_APPROVED"] and not resolved["fullAnimationAllowed"]


def test_review_cannot_override_exceeded_numeric_budgets(tmp_path):
    report = audit.prepare(tmp_path/"gate")
    review = {**fixture(report),"KB1_B":"PASS","faceIdentity":"PASS","armPoseContinuity":"PASS"}
    assert audit.resolve(report,review)["status"] != "BRIDGE_COMPLETE"
    assert not audit.resolve(report,review)["KB2Allowed"]


def test_only_all_numeric_and_visual_pass_can_complete_fixture():
    frozen,kb1,plan = audit.kb1_inputs()
    report = audit.measure(frozen,kb1,plan)
    # Fixture exercises the success branch, not the actual oversized endpoint.
    report["pair"]["numericPass"] = True
    review = {**fixture(report),"KB1_B":"PASS","faceIdentity":"PASS","armPoseContinuity":"PASS"}
    assert audit.resolve(report,review)["status"] == "BRIDGE_COMPLETE"
    assert not audit.resolve(report,review)["runtimeEligible"]


def test_finalization_recomputes_pixels_and_rejects_altered_report(tmp_path):
    output = tmp_path/"gate"
    report = audit.prepare(output)
    path = tmp_path/"review.json"
    path.write_text(json.dumps(fixture(report)))
    forged = copy.deepcopy(report)
    forged["pair"]["numericPass"] = True
    (output/"landmark-report.json").write_text(json.dumps(forged))
    with pytest.raises(ValueError,match="altered"):
        audit.finalize(output,path)
    assert not (output/"final-verdict.json").exists()


def test_changed_kb1_cannot_be_gated(monkeypatch):
    original = audit.digest
    monkeypatch.setattr(audit,"digest",lambda path: "changed" if path.name == "KB1.png" else original(path))
    with pytest.raises(ValueError,match="KB1 candidate changed"):
        audit.kb1_inputs()
