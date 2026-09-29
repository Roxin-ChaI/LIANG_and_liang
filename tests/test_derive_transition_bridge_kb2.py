import json

import pytest
from PIL import Image

from tools import derive_transition_bridge_kb2 as kb2
from tools.derive_transition_bridge import VISUAL_CHECKS
from tools.locked_transition_k1 import sha


def inputs():
    _,source,_ = kb2.authorized_inputs()
    return source,json.loads(kb2.PLAN.read_text())


def test_second_bridge_is_bounded_repeatable_and_keeps_feet():
    source,plan = inputs()
    image = kb2.apply_step(source,plan)
    assert kb2.apply_step(source,plan).tobytes() == image.tobytes()
    report = kb2.assess(source,image,plan)
    assert report["technicalPass"], report["checks"]
    assert report["pair"]["headSizeDelta"] == [-6,-6]
    assert report["pair"]["headCenterDelta"] == [0,-3]
    assert report["pair"]["bodyWidthDelta"] == 12
    assert not report["localChainAllowed"] and report["userArtApproval"] == "PENDING"


@pytest.mark.parametrize("review", [{},{"reviewer":"fixture","KB1_B":"PASS"},
                                   {"reviewer":"fixture","KB1_B":"FAIL","bRgbaSha256":"stale"}])
def test_missing_or_stale_condition_does_not_authorize_second_bridge(tmp_path,review):
    path = tmp_path/"review.json"
    path.write_text(json.dumps(review))
    with pytest.raises(ValueError,match="KB2_REQUIRED"):
        kb2.authorized_inputs(path)


@pytest.mark.parametrize("field,value", [("headTargetBbox",[60,4,116,68]),("headResampler","BICUBIC"),
                                         ("globalScaling",True),("armShift",[12,-30]),("sourceRgbaSha256","wrong")])
def test_new_head_budget_cannot_be_relaxed_to_fit_b(field,value):
    source,plan = inputs()
    plan[field] = value
    with pytest.raises(ValueError):
        kb2.apply_step(source,plan)


def test_face_change_or_whole_person_fit_fails():
    source,plan = inputs()
    with pytest.raises(ValueError,match="native"):
        kb2.apply_step(source.resize((384,416),Image.Resampling.NEAREST),plan)
    image = kb2.apply_step(source,plan)
    image.putpixel((88,30),(255,0,0,255))
    assert not kb2.assess(source,image,plan)["technicalPass"]


def fixture(source,image):
    return {"reviewer":"TEST FIXTURE / NOT VISUAL QA","verdict":"KB1_KB2_STATIC_PASS",
            "sourceRgbaSha256":sha(source.tobytes()),"candidateRgbaSha256":sha(image.tobytes()),
            "checks":{key:"PASS" for key in VISUAL_CHECKS}}


def test_numeric_pass_needs_fresh_complete_independent_review():
    source,plan = inputs()
    image = kb2.apply_step(source,plan)
    assert not kb2.resolve_review(source,image,plan,{})["localChainAllowed"]
    review = fixture(source,image)
    assert kb2.resolve_review(source,image,plan,review)["localChainAllowed"]
    stale = {**review,"candidateRgbaSha256":"wrong"}
    assert not kb2.resolve_review(source,image,plan,stale)["localChainAllowed"]
    review["checks"]["clothSeams"] = "FAIL"
    assert not kb2.resolve_review(source,image,plan,review)["localChainAllowed"]


def test_prepare_one_kb2_no_unauthorized_kb3_and_no_overwrite(tmp_path):
    output = tmp_path/"kb2"
    report = kb2.prepare(output)
    assert report["newPoses"] == ["KB2"]
    assert not (output/"KB3.png").exists()
    with pytest.raises(ValueError,match="overwrite"):
        kb2.prepare(output)
