import json
from PIL import Image

from tools.specify_transition_endpoints import ROOT, build, sha


def test_endpoint_references_are_exact_atlas_pixels_and_baseline(tmp_path):
    report = build(tmp_path)
    assert report["status"] == "SPECIFICATION_ONLY"
    assert report["animationFilesGenerated"] is False
    assert report["logicalAnchor"] == {"x": 96, "baselineY": 203}
    assert len(report["stateMatchedReferences"]) == 14
    for pose in report["stateMatchedReferences"]:
        with Image.open(ROOT / pose["atlas"]) as atlas, Image.open(tmp_path / pose["referenceFile"]) as cell:
            frame, row = pose["frame"], pose["row"]
            source = atlas.crop((frame * 192, row * 208, (frame + 1) * 192, (row + 1) * 208)).convert("RGBA")
            assert cell.size == (192, 208)
            assert cell.tobytes() == source.tobytes()
            assert sha(cell.tobytes()) == pose["pixelSha256"]
            assert cell.getchannel("A").getbbox()[3] - 1 == 203


def test_endpoint_spec_does_not_force_one_different_pose_to_match_both_states():
    report = json.loads((ROOT / "docs/asset-rework/v0.1.0/endpoints/endpoint-specification.json").read_text())
    gu = [pose for pose in report["stateMatchedReferences"] if pose["form"] == "gu"]
    idle = next(pose for pose in gu if pose["state"] == "idle")
    running = next(pose for pose in gu if pose["state"] == "running")
    assert idle["pixelSha256"] != running["pixelSha256"]
    assert [pose["frame"] for pose in gu if pose["state"] == "running"] == list(range(6))
    assert report["directions"]["gu_to_feng"]["frameCount"] == 10
    assert report["directions"]["feng_to_gu"]["frameCount"] == 8
