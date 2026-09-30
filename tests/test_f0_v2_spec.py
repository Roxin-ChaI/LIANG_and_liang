from tools.f0_v2_spec import FACE_SOURCE, FACE_TARGET, HEAD, sources, spec


def test_expression_is_translated_without_changing_its_pixels_or_scale():
    assert [FACE_SOURCE[2]-FACE_SOURCE[0], FACE_SOURCE[3]-FACE_SOURCE[1]] == [43, 28]
    assert [FACE_TARGET[2]-FACE_TARGET[0], FACE_TARGET[3]-FACE_TARGET[1]] == [43, 28]
    assert [b-a for a,b in zip(FACE_SOURCE, FACE_TARGET)] == [0, -2, 0, -2]


def test_morph_target_fits_one_bounded_step_without_pose_conflation():
    report = spec()
    old = report["sourceLandmark"]
    assert [HEAD[2]-HEAD[0], HEAD[3]-HEAD[1]] == [50, 55]
    assert old["headSize"] == [52, 59]
    assert report["entry"]["onlyAfter"] == "F0_MORPH_ENDPOINT_APPROVED"
    assert not report["geometryAloneApprovesArt"]
    assert not report["newBridgeFramesAllowed"]


def test_frozen_sources_and_spec_do_not_write_or_approve_art():
    images = sources()
    assert images["KF2"].size == images["B"].size == (192, 208)
    report = spec()
    assert report["generatedCandidates"] == 0
    assert not report["approvedInputsEditable"] and not report["runtimeIntegrationAllowed"]
