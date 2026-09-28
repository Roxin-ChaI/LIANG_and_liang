"""Temporary fixture sheets test extraction, not visual approval or new artwork."""
import hashlib
import json

from PIL import Image
import pytest

from tools.prepare_transition_animation_candidate import ENDPOINT_ROOT, diagnose_grid, harden_alpha, metrics, prepare, register


def fixture_sheet(tmp_path, columns):
    # Repeated existing approved pixels are ONLY a throwaway unit-test input.
    with Image.open(ENDPOINT_ROOT / "A-gu-to-feng-entry.png") as source:
        sprite = source.copy()
    sheet = Image.new("RGBA", (192 * columns, 416))
    for i in range(columns * 2):
        sheet.paste(sprite, ((i % columns) * 192, (i // columns) * 208))
    path = tmp_path / "synthetic-unit-test-only.png"
    sheet.save(path)
    return path


@pytest.mark.parametrize("direction,count,columns,entry,exit", [
    ("gu_to_feng", 10, 5, "A-gu-to-feng-entry.png", "B-gu-to-feng-exit.png"),
    ("feng_to_gu", 8, 4, "C-feng-to-gu-entry.png", "D-feng-to-gu-exit.png"),
])
def test_counts_exact_boundary_files_and_no_automatic_visual_approval(tmp_path, direction, count, columns, entry, exit):
    source = fixture_sheet(tmp_path, columns)
    original = hashlib.sha256(source.read_bytes()).hexdigest()
    output = tmp_path / "candidate"
    report = prepare(source, direction, output)
    files = sorted((output / "frames").glob("*.png"))
    assert len(files) == count
    assert files[0].read_bytes() == (ENDPOINT_ROOT / entry).read_bytes()
    assert files[-1].read_bytes() == (ENDPOINT_ROOT / exit).read_bytes()
    assert report["structuralPass"]
    assert not report["runtimeEligible"] and not report["idleApproved"] and not report["runningApproved"]
    assert report["status"] == "CANDIDATE_REQUIRES_INDEPENDENT_VISUAL_QA"
    assert len(report["adjacentPairs"]) == count - 1
    assert all(f["baselineY"] == 203 for f in report["frames"])
    assert original == hashlib.sha256(source.read_bytes()).hexdigest()
    with pytest.raises(ValueError, match="overwrite"):
        prepare(source, direction, output)


def test_alpha_hardening_preserves_visible_rgb_without_color_interpolation():
    image = Image.new("RGBA", (2, 2))
    image.putdata([(20, 30, 40, 200), (99, 88, 77, 127), (1, 2, 3, 0), (4, 5, 6, 255)])
    result, changes = harden_alpha(image)
    assert changes == 2
    assert list(result.get_flattened_data()) == [(20, 30, 40, 255), (0, 0, 0, 0), (0, 0, 0, 0), (4, 5, 6, 255)]


def test_integer_registration_not_anatomical_resizing():
    with Image.open(ENDPOINT_ROOT / "A-gu-to-feng-entry.png") as source:
        canonical = source.copy()
    moved = Image.new("RGBA", canonical.size)
    moved.paste(canonical, (2, -2))
    result, shift = register(moved)
    assert shift == [-2, 2]
    assert result.tobytes() == canonical.tobytes()
    assert metrics(result)["bodyBandCenterX"] == 95.5


def test_no_background_keying_or_opaque_sheet_acceptance(tmp_path):
    source = tmp_path / "opaque.png"
    Image.new("RGBA", (960, 416), (0, 255, 0, 255)).save(source)
    with pytest.raises(ValueError, match="transparent background"):
        prepare(source, "gu_to_feng", tmp_path / "output")


def test_isolated_pixel_is_reported_not_silently_removed():
    with Image.open(ENDPOINT_ROOT / "A-gu-to-feng-entry.png") as source:
        sprite = source.copy()
    sprite.putpixel((180, 180), (200, 20, 20, 255))
    assert metrics(sprite)["isolatedSinglePixels"] == 1


def test_user_approval_does_not_approve_future_animation():
    approval = json.loads((ENDPOINT_ROOT / "approval.json").read_text())
    assert approval["status"] == "ENDPOINT_ART_APPROVED"
    assert not approval["runningApproved"] and not approval["fullAnimationApproved"]


def test_rejected_grid_diagnosis_never_emits_playable_frames(tmp_path):
    source = fixture_sheet(tmp_path, 4)
    output = tmp_path / "diagnostic"
    report = diagnose_grid(source, "feng_to_gu", output)
    assert report["status"] == "REJECTED_GRID_DIAGNOSTIC_ONLY"
    assert not report["runtimeEligible"] and report["playableFramesEmitted"] == 0
    assert len(report["cells"]) == 8
    assert not (output / "frames").exists()
    assert (output / "rejected-grid-contact-sheet.png").exists()
    with pytest.raises(ValueError, match="overwrite"):
        diagnose_grid(source, "feng_to_gu", output)


def test_retained_forward_candidate_is_reproducible_but_rejected(tmp_path):
    root = ENDPOINT_ROOT.parent / "transition-full"
    output = root / "gu-to-feng"
    report = prepare(root / "sources/gu-to-feng-generated.png", "gu_to_feng", tmp_path / "re-extraction")
    assert not report["structuralPass"]
    assert report["frames"][2]["isolatedSinglePixels"] == 1
    assert report["frames"][0]["headReferenceBbox"][1] == 4
    assert report["frames"][1]["headReferenceBbox"][1] == 11
    review = json.loads((output / "qa/independent-review.json").read_text())
    validation = json.loads((output / "qa/validation.json").read_text())
    assert review["status"] == validation["visualVerdict"] == "VISUAL_QA_FAIL"
    assert not validation["structuralPass"] and not validation["runtimeEligible"]
    for item in report["frames"]:
        assert item["pngSha256"] == hashlib.sha256((output / item["file"]).read_bytes()).hexdigest()


def test_redraw_structural_pass_cannot_override_failed_visual_gate(tmp_path):
    root = ENDPOINT_ROOT.parent / "transition-full"
    output = root / "gu-to-feng-retry"
    report = prepare(root / "sources/gu-to-feng-generated-retry.png", "gu_to_feng", tmp_path / "retry")
    assert report["structuralPass"]
    assert report["frames"][8]["alphaBbox"] == [36, 8, 156, 204]
    assert report["frames"][9]["alphaBbox"] == [44, 4, 148, 204]
    review = json.loads((output / "qa/independent-review.json").read_text())
    validation = json.loads((output / "qa/validation.json").read_text())
    assert validation["structuralPass"] and validation["visualVerdict"] == "VISUAL_QA_FAIL"
    assert review["idleActualAppGate"] == "BLOCKED" and not review["runtimeEligible"]
    assert any(item["severity"] == "P1" for item in review["observed"])
    for item in report["frames"]:
        assert item["pngSha256"] == hashlib.sha256((output / item["file"]).read_bytes()).hexdigest()
