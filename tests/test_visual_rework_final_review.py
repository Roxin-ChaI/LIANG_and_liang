import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FINAL = ROOT / "docs/visual-rework/v0.1.0/final"


def read(name):
    return json.loads((FINAL / name).read_text())


def test_final_window_coverage_and_gu_baseline_at_both_device_scales():
    report = read("window-metrics.json")
    assert report["guWorkBaselinePass"]
    counts = {"idle": 6, "running-right": 8, "running-left": 8, "waving": 4,
              "jumping": 5, "failed": 8, "waiting": 6, "running": 6, "review": 6}
    for form, record in report["forms"].items():
        for scale in (record, record["1x"]):
            assert scale["lookCount"] == 16
            assert not any(scale["missingFrames"].values())
            for state, count in counts.items():
                assert scale["rows"][state]["capturedFrames"] == list(range(count))
            if form == "gu":
                feet = set(scale["rows"]["idle"]["baselinesCssPx"])
                for state in ("waving", "failed", "waiting", "running", "review"):
                    assert set(scale["rows"][state]["baselinesCssPx"]) == feet
        assert len({(pair["from"], pair["to"]) for pair in record["statePairs"]}) == 81
        order = list(counts)
        assert all(pair["row"] == order.index(pair["to"]) for pair in record["statePairs"])
        assert not any(pair["empty"] or pair["touchesWindowEdge"] for pair in record["statePairs"])
        assert len(record["finiteHandoffs"]) == 4
        assert all(item["row"] == 0 for item in record["finiteHandoffs"])


def test_final_full_transition_frames_and_running_recovery():
    report = read("transitions/transition-timeline.json")
    assert len(report["scenarios"]) == 6
    for case in report["scenarios"]:
        assert case["frameCount"] == (10 if case["source"] == "gu" else 8)
        assert len(case["frameTimestamps"]) == case["frameCount"]
        assert case["lastFrameToCompletionMs"] >= 139
        if case["mode"] == "running":
            assert case["completion"]["underlyingState"] == "running"
            assert case["normalRendererAfterCompletion"]["row"] == 7


def test_final_verdict_cannot_ignore_asset_p1_or_live_race_failure():
    review = read("independent-visual-review.json")
    assert review["verdict"] == "VISUAL_QA_FAIL"
    assert not review["release_candidate_approved"]
    pending = {issue["id"] for issue in review["issues"] if issue["remaining_p1"]}
    assert {"V-04", "V-05"} <= pending
    failure = read("races/race-failure.json")
    assert failure["status"] == "LIVE_RACE_FAIL"
    assert failure["lastPublishedFrame"] == 4
    assert failure["framePaintObserved"] is False
    assert failure["completionObserved"] is False
    # The earlier queue regression did finish both sequences in this same run;
    # it must not erase the later competing-state stall.
    assert [e["transitionId"] for e in failure["completedEarlierOperations"]] == ["gu_to_feng", "feng_to_gu"]
