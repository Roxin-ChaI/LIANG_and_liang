import json

from PIL import Image
import pytest

from tools.validate_transition_k1 import SPEC, assess, constraints, numeric_checks
from tools.specify_transition_keyframes import approved_inputs


def annotation():
    return {"headBbox": [54, 4, 122, 84], "shoulderPoints": [[75, 83], [108, 83]],
            "uncertaintyPx": 1, "independentReviewer": "unit-test-only-not-real-art-approval",
            **{key: "pass" for key in constraints()["visualChecks"]}}


def test_specification_has_exact_user_limits_and_no_generation():
    assert constraints() == json.loads(SPEC.read_text())
    assert constraints()["headWidthRange"] == [65, 69]
    assert constraints()["headHeightRange"] == [77, 81]
    assert not constraints()["candidateGenerated"] and not constraints()["runtimeEligible"]


@pytest.mark.parametrize("head,shoulder,body,baseline,field", [
    ([56,4,120,84],33,[69,70,122,204],203,"headWidth"),
    ([53,4,123,84],33,[69,70,122,204],203,"headWidth"),
    ([54,6,122,82],33,[69,70,122,204],203,"headHeight"),
    ([54,3,122,85],33,[69,70,122,204],203,"headHeight"),
    ([57,4,125,84],33,[69,70,122,204],203,"headCenterX"),
    ([54,7,122,87],33,[69,70,122,204],203,"headCenterY"),
    ([54,4,122,84],38,[69,70,122,204],203,"shoulderWidth"),
    ([54,4,122,84],33,[65,70,122,204],203,"bodyLeft"),
    ([54,4,122,84],33,[69,70,126,204],203,"bodyRight"),
    ([54,4,122,84],33,[69,70,122,203],202,"baseline"),
])
def test_each_out_of_range_is_a_hard_failure(head, shoulder, body, baseline, field):
    report = numeric_checks(head, shoulder, body, baseline)
    assert not report["pass"] and not report["checks"][field]


@pytest.mark.parametrize("head", [[56,5,121,82], [54,3,123,84]])
def test_inclusive_head_ranges_are_accepted_by_numeric_gate(head):
    assert numeric_checks(head,37,[66,70,125,204],203)["pass"]


def test_uncertain_visuals_cannot_pass_even_when_all_metrics_pass():
    canonical = approved_inputs()[0][2]
    assert assess(canonical)["status"] == "AWAITING_INDEPENDENT_K1_REVIEW"
    notes = annotation()
    notes["faceIdentity"] = "unknown"
    assert assess(canonical, notes)["status"] == "K1_VISUAL_NOT_VERIFIED"
    notes["faceIdentity"] = "fail"
    assert assess(canonical, notes)["status"] == "K1_QA_FAIL"
    notes = annotation()
    notes["uncertaintyPx"] = 3
    assert assess(canonical, notes)["status"] == "K1_VISUAL_NOT_VERIFIED"


def test_valid_evidence_only_opens_local_chain_not_global_approval_or_runtime():
    report = assess(approved_inputs()[0][2], annotation())
    assert report["status"] == "A_K1_PASS" and report["localChainAllowed"]
    assert not report["runtimeEligible"] and report["resizeOperations"] == 0
    assert "K1_APPROVED" not in report.values()
    with pytest.raises(ValueError, match="no whole-character resizing"):
        assess(Image.new("RGBA", (384,416)))


def test_old_k1_fails_new_limits_without_modifying_it():
    root = SPEC.parents[1] / "gu-to-feng-candidate-retry"
    with Image.open(root / "keys/K1.png") as image:
        notes = annotation()
        notes["headBbox"] = [63,5,120,73]
        notes["shoulderPoints"] = [[75,73],[110,73]]
        report = assess(image, notes)
    assert report["status"] == "K1_QA_FAIL" and not report["localChainAllowed"]
    assert not report["numeric"]["checks"]["headWidth"]
    assert not report["numeric"]["checks"]["headHeight"]


def test_empty_candidate_fails_without_anatomical_measurements_or_crash():
    report = assess(Image.new("RGBA",(192,208)),annotation())
    assert report["status"] == "K1_QA_FAIL" and report["numeric"] is None
    assert not report["localChainAllowed"]
