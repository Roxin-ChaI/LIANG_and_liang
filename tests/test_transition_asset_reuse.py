import json
from tools.specify_transition_endpoints import ROOT, sha


def test_reuse_assessment_does_not_emit_or_promote_unapproved_substitute_frames():
    report = json.loads((ROOT / "docs/asset-rework/v0.1.0/reuse/reuse-feasibility.json").read_text())
    assert report["status"] == "NEEDS_MANUAL_ART_REDESIGN"
    assert not report["packagingEligible"]
    assert not report["animationFramesGenerated"]
    assert not report["sourceFramesModified"]
    assert len(report["inputHashes"]) == 18
    for name, digest in report["inputHashes"].items():
        assert sha((ROOT / name).read_bytes()) == digest
    for case in report["cases"]:
        assert not case["exactWholePoseMatch"]
        assert case["sourceFrameCount"] == 18
        assert case["verticalTranslation"] == 0


def test_rgba_difference_counts_rgb_changes_even_when_alpha_is_unchanged():
    from PIL import Image
    from tools.assess_transition_asset_reuse import different_pixels
    a = Image.new("RGBA", (3, 3), (20, 20, 20, 255))
    b = a.copy()
    b.putpixel((1, 1), (40, 20, 20, 255))
    assert different_pixels(a, b) == 1
    b.putpixel((2, 2), (20, 20, 20, 0))
    assert different_pixels(a, b) == 2
