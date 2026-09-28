import hashlib
import json
from pathlib import Path

from PIL import Image
import pytest

from tools.prepare_manual_transition_endpoints import ENDPOINTS, ROOT, canonical, compare, pixel_overlay, prepare


def test_four_boundary_drafts_are_exact_existing_canonical_pixels(tmp_path):
    inputs = {form: canonical(form)[0] for form in ("gu", "feng")}
    before = {form: hashlib.sha256(file.read_bytes()).hexdigest() for form, file in inputs.items()}
    output = tmp_path / "endpoints"
    report = prepare(output)
    assert report["humanApproval"] == "PENDING"
    assert report["status"] == "AWAITING_MANUAL_ENDPOINT_APPROVAL"
    assert not report["runtimeEligible"] and not report["animationGenerated"]
    assert report["intermediateFramesGenerated"] == 0
    assert len(list(output.glob("*.png"))) == len(ENDPOINTS) == 4
    for item in report["endpoints"]:
        with Image.open(output / item["file"]) as actual:
            _, expected = canonical(item["form"])
            assert actual.mode == "RGBA" and actual.size == (192, 208)
            assert actual.tobytes() == expected.tobytes()
        assert item["technicalPass"] and item["rgbaDifferentPixels"] == 0
        assert item["baselineY"] == 203 and item["registrationAnchorX"] == 96
        assert item["headPositionDelta"] == item["bodyBboxDelta"] == [0, 0, 0, 0]
        assert item["alphaValues"] == [0, 255] and item["hiddenRgbPixels"] == 0
        assert item["humanApproval"] == "PENDING"
    assert before == {form: hashlib.sha256(file.read_bytes()).hexdigest() for form, file in inputs.items()}
    with pytest.raises(ValueError, match="overwrite"):
        prepare(output)


def test_registration_proxy_is_not_used_to_recenter_approved_gu():
    _, gu = canonical("gu")
    report = compare(gu, gu)
    assert report["measuredBodyBandCenterX"] == 95.5
    assert report["registrationAnchorX"] == 96
    moved = Image.new("RGBA", gu.size)
    moved.paste(gu, (1, 0))
    assert not compare(moved, gu)["technicalPass"]


def test_overlay_detects_rgb_change_even_with_identical_alpha():
    _, gu = canonical("gu")
    changed = gu.copy()
    point = next((x, y) for y in range(208) for x in range(192) if gu.getpixel((x, y))[3])
    r, g, b, alpha = gu.getpixel(point)
    changed.putpixel(point, ((r + 1) % 256, g, b, alpha))
    assert compare(changed, gu)["rgbaDifferentPixels"] == 1
    assert pixel_overlay(gu, changed).getpixel(point) == (255, 220, 0, 255)


def test_delivered_package_cannot_claim_human_approval_or_full_animation():
    output = ROOT / "assets/rework/v0.1.0/manual-transition-endpoints"
    report = json.loads((output / "qa/validation.json").read_text())
    assert report["status"] == "AWAITING_MANUAL_ENDPOINT_APPROVAL"
    assert report["humanApproval"] == "PENDING" and not report["runtimeEligible"]
    assert report["intermediateFramesGenerated"] == 0
    for item in report["endpoints"]:
        assert item["pngSha256"] == hashlib.sha256((output / item["file"]).read_bytes()).hexdigest()
        assert item["sourceSha256"] == hashlib.sha256((ROOT / item["canonicalSource"]).read_bytes()).hexdigest()


def test_current_user_approval_is_hash_bound_and_idle_only():
    output = ROOT / "assets/rework/v0.1.0/manual-transition-endpoints"
    approval = json.loads((output / "approval.json").read_text())
    assert approval["status"] == "ENDPOINT_ART_APPROVED"
    assert approval["scope"] == "Idle canonical endpoints only"
    assert not approval["runningApproved"] and not approval["fullAnimationApproved"]
    assert len(approval["approvedFiles"]) == 4
    for filename, expected in approval["approvedFiles"].items():
        assert hashlib.sha256((output / filename).read_bytes()).hexdigest() == expected
