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
