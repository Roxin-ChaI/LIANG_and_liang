import json
from tools.compile_visual_findings import ROOT


def test_live_deferred_reverse_displays_both_complete_sequences():
    report = json.loads((ROOT / "docs/visual-rework/v0.1.0/p2/race-summary.json").read_text())
    case = report["cancelledTransition"]
    assert case["queuedRequests"]
    completions = case["completions"]
    assert [event["transitionId"] for event in completions] == ["gu_to_feng", "feng_to_gu"]
    for transition, count in (("gu_to_feng", 10), ("feng_to_gu", 8)):
        frames = [event["transitionFrame"] for event in case["fullOperationEvents"]
                  if event.get("type") == "renderer" and event.get("transitionId") == transition]
        assert list(dict.fromkeys(frames)) == list(range(count))
    assert case["lastRenderer"]["row"] == 7
    assert case["lastRenderer"]["state"] == "running"
    # No normal-atlas flash while the queued two-operation sequence is active.
    assert not any(event.get("type") == "renderer" and event.get("visualMode") == "NORMAL"
                   and event["observedAt"] < completions[-1]["observedAt"]
                   for event in case["fullOperationEvents"])


def test_live_latest_work_state_survives_duplicate_and_hover_burst():
    report = json.loads((ROOT / "docs/visual-rework/v0.1.0/p2/race-summary.json").read_text())
    case = report["competingStates"]
    assert case["completion"]["operationToken"] == case["operationToken"]
    assert case["completion"]["underlyingState"] == "review"
    assert case["lastRenderer"]["row"] == 8


def test_unreworked_feng_frames_are_not_misreported_as_asset_fixes():
    # Preserve the artistic limitation explicitly; no player timing change can
    # create breathing or failure poses absent from the approved PNG pixels.
    from PIL import Image
    with Image.open(ROOT / "assets/builds/feng/spritesheet.webp") as atlas:
        def frame(row, column):
            return atlas.crop((column * 192, row * 208, (column + 1) * 192, (row + 1) * 208)).tobytes()
        assert frame(0, 0) == frame(0, 1)
        assert frame(0, 4) == frame(0, 5)
        for left, right in ((0, 1), (3, 4), (6, 7)):
            assert frame(5, left) == frame(5, right)


def test_ungated_monotonic_diagnostics_keep_paint_and_dwell_separate():
    from tools.summarize_transition_timing import summarize
    report = json.loads((ROOT / "docs/visual-rework/v0.1.0/p2/timing-diagnostics.json").read_text())
    assert report["status"] == "DIAGNOSED_NOT_FIXED"
    for case, count in zip(report["cases"], (10, 8)):
        assert case["ackCount"] == case["timerCount"] == count
        assert case["configuredDwellMs"] == [140]
        assert case["ackToTimerFireMs"][0] >= 139  # minor timer-resolution tolerance
        assert case["publishToPaintAckMs"][0] > 0
    synthetic = summarize({"ungatedTimings": [{"transitionId": "gu_to_feng",
        "frameTimestamps": {}, "observedIntervalsMs": [], "dwellDiagnostics": []}]})
    assert synthetic["cases"][0]["ackToTimerFireMs"] is None
