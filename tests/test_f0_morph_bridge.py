from __future__ import annotations

from tools.f0_morph_bridge import HEAD_GUIDES, LIMITS, hand_guides, sources, specification


def test_three_head_steps_fit_local_motion_budget() -> None:
    boxes = list(HEAD_GUIDES.values())
    for left, right in zip(boxes, boxes[1:]):
        sizes = [(right[2]-right[0])-(left[2]-left[0]), (right[3]-right[1])-(left[3]-left[1])]
        assert all(abs(x) <= LIMITS["headSize"] for x in sizes)
        assert abs((right[1]+right[3]-left[1]-left[3])/2) <= LIMITS["headCenterY"]


def test_hand_trajectory_not_only_head_bbox() -> None:
    spec = specification()
    chain = [spec["endpointHandSkinGuides"]["KB2"],
             {side: {"center": center} for side, center in spec["targetHandCenters"]["KF1"].items()},
             {side: {"center": center} for side, center in spec["targetHandCenters"]["KF2"].items()},
             spec["endpointHandSkinGuides"]["F0"]]
    for left, right in zip(chain, chain[1:]):
        for side in ("left", "right"):
            dx,dy = [b-a for a,b in zip(left[side]["center"],right[side]["center"])]
            assert abs(dx) <= LIMITS["handCenterX"]
            assert abs(dy) <= LIMITS["handCenterY"]


def test_spec_does_not_grant_art_or_runtime_approval() -> None:
    spec = specification()
    assert spec["imageOutputs"] == 0
    assert not spec["sources"]["F0"]["artApproved"]
    assert not spec["runtimeIntegration"] and not spec["F0ToIdleAudit"]
    assert hand_guides(sources()["KB2"])["left"]["skinBbox"] == [76,139,84,154]
