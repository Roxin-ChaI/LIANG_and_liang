import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "docs/asset-rework/v0.1.0/integrated"


def read(name):
    return json.loads((EVIDENCE / name).read_text())


def test_actual_window_frames_timers_and_state_restoration():
    operations = []
    for name in ("transitions-ack.json", "race-1-ack.json", "race-2-ack.json", "ungated-ack.json"):
        report = read(name)
        assert report["status"] == "PAINT_DWELL_COMPLETION_PASS"
        assert not report["errors"]
        assert not report["visualArtworkApproved"]
        operations.extend(report["operations"])
    assert len(operations) == 24
    assert sum(len(o["orderedPaintedFrames"]) for o in operations) == 216
    assert all(o["frame4PaintObserved"] and o["completionCount"] == 1 for o in operations)
    scenes = read("transitions/transition-timeline.json")["scenarios"]
    assert len(scenes) == 6
    for scene in scenes:
        assert scene["frameCount"] == (10 if scene["source"] == "gu" else 8)
        assert scene["normalRendererAfterCompletion"]["row"] == {"idle": 0, "running": 7, "hover": 4}[scene["mode"]]
        assert scene["lastFrameToCompletionMs"] >= 139
        for index in range(scene["frameCount"]):
            assert (EVIDENCE / "transitions/frames" / f"{scene['label']}-{index:02d}.png").is_file()


def test_player_pass_cannot_erase_art_blocker_or_historical_evidence_limit():
    report = read("review.json")
    assert report["verdict"] == "VISUAL_QA_FAIL"
    assert report["assetGate"] == "NEEDS_MANUAL_ART_REDESIGN"
    assert report["newTransitionAnimationFilesGenerated"] == report["transitionAnimationFilesModified"] == 0
    assert report["newArtworkIntegratedTest"] == "NOT_TESTED / BLOCKED_ART"
    assert not report["releaseCandidateApproved"]
    assert not report["incumbentAppReplaced"] and not report["tagCreated"]
    assert "NOT_PROVEN" in report["exactHistoricalStallRootCause"]
    assert read("independent-visual-review.json")["verdict"] == "VISUAL_QA_FAIL"
