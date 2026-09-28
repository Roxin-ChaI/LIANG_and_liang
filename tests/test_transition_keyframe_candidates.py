import json
from pathlib import Path

from PIL import Image
import pytest

from tools.prepare_transition_keyframe_candidates import annotate_landmarks, prepare, source_regions
from tools.specify_transition_keyframes import approved_inputs


def fixture(tmp_path):
    # Throwaway copies ONLY test mechanics, never approval or candidate art.
    gu = approved_inputs()[0][2]
    image = Image.new("RGBA", (576, 208))
    for i in range(3):
        image.paste(gu, (i * 192, 0))
    source = tmp_path / "unit-fixture-only.png"
    image.save(source)
    return source


def test_only_three_new_inputs_five_keys_exact_approved_endpoints(tmp_path):
    report = prepare(fixture(tmp_path), tmp_path / "candidate")
    assert report["poseCount"] == 5 and report["newArtworkCount"] == 3
    assert not report["fullAnimationGenerated"] and not report["appIntegrated"]
    assert not report["runtimeEligible"] and report["manualApproval"] == "PENDING"
    assert [r["id"] for r in report["frames"]] == ["A", "K1", "K2", "K3", "B"]
    for letter, source, _ in approved_inputs():
        assert (tmp_path / "candidate/keys" / f"{letter}.png").read_bytes() == source.read_bytes()
    assert len(report["adjacentPairs"]) == 4
    assert all(r["baselineDelta"] == 0 for r in report["adjacentPairs"])
    assert len(list((tmp_path / "candidate/keys").glob("*.png"))) == 5
    with pytest.raises(ValueError, match="overwrite"):
        prepare(fixture(tmp_path), tmp_path / "candidate")


def test_do_not_accept_grid_overlaps_missing_art_or_opaque_background():
    with pytest.raises(ValueError, match="transparent RGBA"):
        source_regions(Image.new("RGB", (576, 208)))
    with pytest.raises(ValueError, match="transparent RGBA"):
        source_regions(Image.new("RGBA", (576, 208), (0, 255, 0, 255)))
    with pytest.raises(ValueError, match="THREE"):
        source_regions(Image.new("RGBA", (576, 208)))


def test_structure_cannot_claim_anatomical_or_visual_approval(tmp_path):
    report = prepare(fixture(tmp_path), tmp_path / "candidate")
    assert report["structuralPass"]
    assert "proxy only" in report["headMeasurement"]
    assert report["status"] == "AWAITING_INDEPENDENT_KEYFRAME_REVIEW"
    assert not report["runtimeEligible"]


def test_manual_anatomy_is_separate_from_head_band_and_cannot_grant_user_approval(tmp_path):
    root = tmp_path / "candidate"
    prepare(fixture(tmp_path), root)
    ids = ["A", "K1", "K2", "K3", "B"]
    notes = {"reviewer": "unit-test-only", "visualVerdict": "KEYFRAME_QA_FAIL",
             "frames": [{"id": key, "headApproxBbox": [54, 4, 122, 84],
                         "shoulderGuidePoints": [[75, 83], [108, 83]], "visualNotes": "test-only"} for key in ids],
             "adjacentPairs": [{"pair": f"{a}->{b}", "verdict": "fail", "reason": "test-only"} for a, b in zip(ids, ids[1:])]}
    path = tmp_path / "manual.json"
    path.write_text(json.dumps(notes))
    report = annotate_landmarks(root, path)
    assert report["frames"][0]["headApproxCenter"] == [88, 44]
    assert all(r["headCenterDelta"] == [0, 0] for r in report["adjacentPairs"])
    assert report["manualApproval"] == "PENDING" and not report["runtimeEligible"]
    notes["visualVerdict"] = "KEYFRAME_ART_APPROVED"
    path.write_text(json.dumps(notes))
    with pytest.raises(ValueError, match="cannot grant human"):
        annotate_landmarks(root, path)
    notes["visualVerdict"] = "AWAITING_MANUAL_KEYFRAME_APPROVAL"
    path.write_text(json.dumps(notes))
    with pytest.raises(ValueError, match="failed pair"):
        annotate_landmarks(root, path)


@pytest.mark.parametrize("suffix,source", [("", "gu-to-feng-three-keys.png"), ("-retry", "gu-to-feng-three-keys-retry.png")])
def test_retained_failed_art_remains_reproducible_and_not_runtime_eligible(tmp_path, suffix, source):
    root = Path(__file__).resolve().parents[1] / "assets/rework/v0.1.0/transition-keyframes"
    original = json.loads((root / f"gu-to-feng-candidate{suffix}/qa/validation.json").read_text())
    repeated = prepare(root / "sources" / source, tmp_path / "repeated")
    assert original["status"] == "KEYFRAME_QA_FAIL" and not original["runtimeEligible"]
    assert original["structuralPass"]  # Structural pass must not conceal visual failure.
    assert all(a["sha256"] == b["sha256"] for a, b in zip(original["frames"], repeated["frames"]))
    assert len(original["frames"]) == 5 and original["newArtworkCount"] == 3
