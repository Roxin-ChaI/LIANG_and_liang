import pytest
from PIL import Image

from tools.transition_bridge_spec import (
    B_HEAD, K3_HEAD, capacity, frozen_images, landmark, prepare_spec, specification, step_gate,
)


def pair():
    images = frozen_images()
    return landmark(images["K3"], K3_HEAD), landmark(images["B"], B_HEAD, approximate=True)


def test_spec_pins_all_five_approved_inputs_and_generates_no_art():
    report = specification()
    assert set(report["frozenFiles"]) == {"A","K1","K2","K3","B"}
    assert "K1/K2/K3" in report["approvalProvenance"]
    assert report["generatedPoses"] == 0
    assert not report["runtimeEligible"] and not report["fullAnimationAllowed"]
    assert report["limits"] == {"headSize":6,"headCenterX":3,"headCenterY":4,"bodyWidth":15}


def test_nominal_gap_and_two_bridge_capacity_are_not_hidden():
    left,right = pair()
    assert step_gate(left,right)["headSizeDelta"] == [-19,-26]
    assert step_gate(left,right)["headCenterDelta"] == [0.5,-13]
    assert step_gate(left,right)["bodyWidthDelta"] == 35
    for bridges in (1,2):
        report = capacity(left,right,bridges)
        assert not report["numericCapacitySufficient"]
        assert report["nominalMinimumBridges"] == 4
        assert report["headGuideUncertaintyPx"] == 3
    assert capacity(left,right,4)["numericCapacitySufficient"]


@pytest.mark.parametrize("bridges", [-1,1.5,True])
def test_capacity_rejects_invalid_count(bridges):
    with pytest.raises(ValueError):
        capacity(*pair(),bridges)


@pytest.mark.parametrize("field,value,check", [
    ("headSize",[61,74],"headSizeAtMost6"),
    ("headCenter",[91.5,44],"headCenterXAtMost3"),
    ("headCenter",[88,39.5],"headCenterYAtMost4"),
    ("bodyWidth",85,"bodyGrowth0to15"),
    ("baselineY",202,"baseline203"),
    ("registrationX",95,"registration96"),
])
def test_each_exceeded_threshold_fails_without_visual_approval(field,value,check):
    left,_ = pair()
    right = {**left,field:value}
    report = step_gate(left,right)
    assert not report["checks"][check] and not report["numericPass"]
    assert report["staticVerdict"] == "NOT_VERIFIED"


def test_budget_edge_pass_is_not_face_or_pose_approval():
    left,_ = pair()
    right = {**left,"headSize":[62,74],"headCenter":[91,40],"bodyWidth":84}
    report = step_gate(left,right)
    assert report["numericPass"]
    assert report["faceIdentity"] == report["armPose"] == "MANUAL_VISUAL_QA"
    assert report["staticVerdict"] == "NOT_VERIFIED"


def test_prepare_only_writes_contract_json_and_cannot_overwrite(tmp_path):
    target = tmp_path/"spec"
    prepare_spec(target)
    assert [p.name for p in target.iterdir()] == ["specification.json"]
    with pytest.raises(ValueError,match="overwrite"):
        prepare_spec(target)


def test_no_silent_canvas_or_mode_conversion():
    for image in (Image.new("RGB",(192,208)),Image.new("RGBA",(208,224))):
        with pytest.raises(ValueError,match="native"):
            landmark(image,K3_HEAD)
