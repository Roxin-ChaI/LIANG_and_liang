from tools.feng_entry_spec import anchors, specification


def test_entry_is_four_frames_after_f0_and_ends_at_frozen_idle():
    report = specification()
    assert report["entrySequence"] == ["F0-v2","E1","E2","E3","Idle B"]
    assert report["entryFrameCount"] == 4 and report["F0ExcludedFromFrameCount"]
    assert report["baselineY"] == 203 and report["registrationX"] == 96
    assert not report["preservation"]["formalAtlasEditable"]


def test_foot_trajectory_spreads_without_instant_two_leg_jump():
    report = specification()
    t = report["trajectoryGuides"]
    assert t["leftFootCenterX"][0:2] == [82.5,82.5]
    assert t["rightFootCenterX"][0:2] == [109,109]
    assert t["leftFootCenterX"][-1] == 65.5
    assert t["rightFootCenterX"][-1] == 127.5


def test_sources_and_gate_remain_only_static():
    assert set(anchors()) == {"F0-v2","Idle B"}
    report = specification()
    assert report["createdFrames"] == 0
    assert report["gates"]["E1E2StopOnFail"] and report["gates"]["E3RequiresE1E2Pass"]
    assert not report["preservation"]["runtimeIntegration"]
