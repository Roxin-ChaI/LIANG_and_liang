import json

from tools.specify_transition_keyframes import OUTPUT, prepare, specification


def test_spec_only_three_new_poses_no_animation_or_approval():
    report = specification()
    assert report["sequence"] == ["A", "K1", "K2", "K3", "B"]
    assert report["newPoseCount"] == 3 and report["generatedArtworkCount"] == 0
    assert report["manualApprovalRequired"]
    assert not report["fullAnimationAllowed"] and not report["appIntegrationAllowed"]
    assert not report["runtimeEligible"]


def test_head_center_is_not_forced_to_registration_anchor():
    report = specification()
    assert [r["headApproxCenter"][0] for r in report["endpoints"]] == [88, 88.5]
    assert all(r["registrationX"] == 96 and r["baselineY"] == 203 for r in report["endpoints"])
    assert report["endpoints"][1]["headCapBbox0to55"] == [64, 4, 113, 55]
    assert "not anatomy" in report["landmarkConvention"]


def test_motion_budget_monotonic_without_synthesizing_art():
    poses = specification()["poses"]
    assert [r["progress"] for r in poses] == [.1, .5, .9]
    assert [r["headApproxBboxTarget"][3] for r in poses] == [81, 71, 61]
    assert all(r["hairTopYRange"] == [3, 6] for r in poses)
    assert poses[0]["shoulderGuideWidthRange"][1] < poses[1]["shoulderGuideWidthRange"][0] < poses[2]["shoulderGuideWidthRange"][0]


def test_guides_are_qa_only_no_pose_pngs_emitted_and_retained_spec_matches(tmp_path):
    report = prepare(tmp_path / "spec")
    assert not (tmp_path / "spec/frames").exists()
    assert sorted(p.name for p in (tmp_path / "spec").glob("*.png")) == ["canonical-landmark-guide.png", "layout-guide.png"]
    assert report == json.loads((OUTPUT / "specification.json").read_text())
