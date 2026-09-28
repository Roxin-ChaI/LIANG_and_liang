import json
from PIL import Image

from tools.diagnose_transition_handoff import ROOT, anchors, rigid_alignment


def test_rigid_alignment_reports_incompatible_body_part_centers():
    canonical = {name: {"centerX": 96} for name in ("head", "shoulders", "shoes")}
    endpoint = {"head": {"centerX": 88}, "shoulders": {"centerX": 99}, "shoes": {"centerX": 99}}
    result = rigid_alignment(canonical, endpoint)
    assert result["rigidAnchorPass"] is False
    assert result["maximumResidual"] > 2


def test_entry_evidence_does_not_turn_geometry_pass_into_pose_pass():
    report = json.loads((ROOT / "docs/visual-rework/v0.1.0/entry/gu_to_feng-feasibility.json").read_text())
    assert report["appliedToRuntime"] is False
    idle, running = report["cases"]
    assert idle["alignment"]["rigidAnchorPass"] is True
    assert idle["status"] == "MANUAL_VISUAL_QA"
    assert running["alignment"]["rigidAnchorPass"] is False
    assert running["alignment"]["maximumResidual"] == 4.5


def test_exit_geometry_pass_cannot_substitute_for_visual_pose_review():
    report = json.loads((ROOT / "docs/visual-rework/v0.1.0/exit/feng_to_gu-feasibility.json").read_text())
    assert report["endpointFrame"] == 7
    assert report["appliedToRuntime"] is False
    assert all(case["status"] == "MANUAL_VISUAL_QA" for case in report["cases"])


def test_actual_reverse_transition_keeps_all_frames_and_restores_running():
    report = json.loads((ROOT / "docs/visual-rework/v0.1.0/exit/runtime/transition-timeline.json").read_text())
    case = next(case for case in report["scenarios"] if case["mode"] == "running")
    assert case["frameCount"] == 8
    assert case["completion"]["underlyingState"] == "running"
    assert case["normalRendererAfterCompletion"]["row"] == 7
    assert case["normalRendererAfterCompletion"]["state"] == "running"
    assert case["lastFrameToCompletionMs"] >= 140
