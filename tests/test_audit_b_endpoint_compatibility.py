import copy
import json

import pytest

from tools import audit_b_endpoint_compatibility as audit


def review(report):
    return {"reviewer":"TEST FIXTURE / NOT VISUAL QA","reviewedBRgbaSha256":report["hashes"]["B"],
            "reviewedKB2RgbaSha256":report["hashes"]["KB2"],
            "headIsCanonicalDesign":"CONFIRMED","identityContinuityFeasibleWithTwoMoreFrames":"LIKELY",
            "chinHandIdleEndpointSuitability":"SUITABLE","verdict":"B_ENDPOINT_COMPATIBLE"}


def test_b_is_actual_formal_feng_not_a_bad_crop_or_scale():
    report = audit.evidence()
    assert report["technicalPass"]
    assert all(report["checks"].values())
    assert report["BFullAlphaBbox"] == [44,4,148,204]
    assert report["BVisibleMarginPx"] == {"left":44,"top":4,"right":44,"bottom":4}
    assert report["headSizeGuToBApproxDelta"] == [-19,-26]
    assert report["coordinateErrorCause"] == "EXCLUDED_IF_CHECKS_PASS"
    assert report["BIsUsableTransitionEndpoint"] == "NOT_YET_PROVEN_BY_CANONICAL_EQUALITY"


def test_no_art_autoapproval_from_canonical_equality():
    report = audit.evidence()
    assert audit.resolve(report,{})["status"] == "B_ENDPOINT_NOT_VERIFIED"
    candidate = review(report)
    assert audit.resolve(report,candidate)["KB3Allowed"]
    assert not audit.resolve(report,{**candidate,"reviewedBRgbaSha256":"stale"})["KB3Allowed"]
    assert audit.resolve(report,{**candidate,"verdict":"B_ENDPOINT_REWORK_REQUIRED"})["status"] == "B_ENDPOINT_REWORK_REQUIRED"
    assert not audit.resolve(report,{**candidate,"headIsCanonicalDesign":"UNKNOWN"})["KB3Allowed"]
    assert not audit.resolve(report,{**candidate,"chinHandIdleEndpointSuitability":"NOT_PROVEN"})["KB3Allowed"]
    assert not audit.resolve(report,{**candidate,"identityContinuityFeasibleWithTwoMoreFrames":"NOT_PROVEN"})["KB3Allowed"]


def test_actual_independent_art_rejection_stops_kb3():
    report = audit.evidence()
    review_path = audit.QA/"independent-review.json"
    actual_review = json.loads(review_path.read_text())
    result = audit.resolve(report,actual_review)
    assert result["status"] == "B_ENDPOINT_REWORK_REQUIRED"
    assert result["independentReviewFresh"]
    assert not result["KB3Allowed"]
    assert not (audit.OUTPUT/"kb3").exists()


def test_prepare_is_read_only_and_refuses_overwrite(tmp_path):
    output = tmp_path/"audit"
    report = audit.prepare(output)
    assert report["newArtGenerated"] == 0
    assert sorted(p.name for p in output.iterdir()) == ["endpoint-compatibility-contact.png","endpoint-compatibility-nearest3x.png","technical-report.json"]
    with pytest.raises(ValueError,match="overwrite"):
        audit.prepare(output)


def test_finalization_rechecks_actual_pixels_not_cached_report(tmp_path):
    output = tmp_path/"audit"
    report = audit.prepare(output)
    review_file = tmp_path/"review.json"
    review_file.write_text(json.dumps(review(report)))
    forged = copy.deepcopy(report)
    forged["checks"]["BHasCanvasSafetyMargin"] = False
    (output/"technical-report.json").write_text(json.dumps(forged))
    with pytest.raises(ValueError,match="altered"):
        audit.finalize(output,review_file)
    assert not (output/"final-verdict.json").exists()


def test_changed_formal_atlas_stops_gate(monkeypatch):
    original = audit.digest
    monkeypatch.setattr(audit,"digest",lambda path: "wrong" if path==audit.FENG_ATLAS else original(path))
    with pytest.raises(ValueError,match="formal Feng atlas changed"):
        audit.inputs()
