import copy
import json

import pytest
from PIL import Image

from tools.derive_transition_bridge import PLAN, VISUAL_CHECKS, apply_step, assess, prepare, resolve_review
from tools.locked_transition_k1 import sha
from tools.transition_bridge_spec import frozen_images


def inputs():
    return frozen_images()["K3"],json.loads(PLAN.read_text())


def test_local_step_is_reproducible_and_bounded_not_global_fit():
    source,plan = inputs()
    image = apply_step(source,plan)
    assert image.tobytes() == apply_step(source,plan).tobytes()
    report = assess(source,image,plan)
    assert report["technicalPass"], report["checks"]
    assert report["pair"]["headSizeDelta"] == [-6,-6]
    assert report["pair"]["headCenterDelta"] == [0,-3]
    assert report["pair"]["bodyWidthDelta"] == 12
    assert not report["localChainAllowed"]
    assert source.crop((0,164,192,208)).tobytes() == image.crop((0,164,192,208)).tobytes()


@pytest.mark.parametrize("field,value", [("headResampler","BILINEAR"),("globalScaling",True),
                                         ("headTargetBbox",[56,4,120,76]),("source","B"),
                                         ("sourceRgbaSha256","stale"),("armShift",[5,-8])])
def test_forbidden_or_stale_plan_rejected(field,value):
    source,plan = inputs()
    plan[field] = value
    with pytest.raises(ValueError):
        apply_step(source,plan)


def test_resize_never_silently_fits_full_sprite():
    source,plan = inputs()
    with pytest.raises(ValueError,match="native"):
        apply_step(source.resize((384,416),Image.Resampling.NEAREST),plan)


def test_undocumented_face_or_foot_pixel_edit_fails():
    source,plan = inputs()
    for xy in ((88,50),(90,203)):
        image = apply_step(source,plan)
        image.putpixel(xy,(255,0,0,255))
        report = assess(source,image,plan)
        assert not report["checks"]["exactDocumentedLocalDerivation"]
        assert not report["technicalPass"]


def review_fixture(source,image):
    return {"reviewer":"TEST FIXTURE / NOT REAL VISUAL QA", "verdict":"K3_KB1_STATIC_PASS",
            "sourceRgbaSha256":sha(source.tobytes()),"candidateRgbaSha256":sha(image.tobytes()),
            "checks":{key:"PASS" for key in VISUAL_CHECKS}}


def test_no_visual_review_cannot_approve_numeric_pass():
    source,plan = inputs()
    image = apply_step(source,plan)
    assert not resolve_review(source,image,plan,{})["localChainAllowed"]
    review = review_fixture(source,image)
    assert resolve_review(source,image,plan,review)["localChainAllowed"]
    assert resolve_review(source,image,plan,review)["artApproval"] == "PENDING_USER"
    for field in ("sourceRgbaSha256","candidateRgbaSha256"):
        stale = {**review,field:"wrong"}
        assert not resolve_review(source,image,plan,stale)["localChainAllowed"]
    incomplete = copy.deepcopy(review)
    del incomplete["checks"]["faceIdentity"]
    assert not resolve_review(source,image,plan,incomplete)["localChainAllowed"]


def test_one_candidate_only_and_refuse_overwrite(tmp_path):
    target = tmp_path/"kb1"
    report = prepare(target)
    assert report["newPoses"] == ["KB1"]
    assert not (target/"KB2.png").exists()
    assert (target/"qa/contact-sheet.png").is_file()
    with pytest.raises(ValueError,match="overwrite"):
        prepare(target)
