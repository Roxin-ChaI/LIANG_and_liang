"""Candidate guardrails; no automatic assertion of user art approval."""
import hashlib
import json
import numpy as np
from PIL import Image

from tools.prepare_feng_failed_r3 import OUT, FENG, GU, ROOT
from tools.build_animation_review import cell


def test_references_match_current_approved_sources():
    manifest = json.loads((OUT / "source-manifest.json").read_text())
    for name, digest in manifest["sources"].items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest
    idle = cell(Image.open(FENG).convert("RGBA"), 0, 0)
    assert Image.open(OUT / "canonical-idle.png").tobytes() == idle.tobytes()
    assert idle.size == (192, 208)
    assert idle.getbbox() == (44, 4, 148, 204)


def test_reference_does_not_claim_runtime_or_art_approval():
    manifest = json.loads((OUT / "source-manifest.json").read_text())
    assert manifest["userApproval"] == "PENDING"
    assert not manifest["runtimeIntegrated"]
    assert manifest["frameCount"] == 8
    assert Image.open(OUT / "gu-motion-reference.gif").n_frames == 8


def test_official_atlas_freeze():
    assert hashlib.sha256(FENG.read_bytes()).hexdigest() == (
        "d697e573268b66cb0f6a062480ec87c8c11712ca34b57f8c2fc0a97ed6e2164a")


def test_eight_frames_lock_body_and_original_endpoints():
    from tools.finish_feng_failed_r3 import masks
    idle = Image.open(OUT / "canonical-idle.png").convert("RGBA")
    p = np.array(idle)
    head, raised, lower = masks(idle)
    editable = head | raised | lower
    frames = [Image.open(OUT / f"failed-{i:02d}.png") for i in range(1, 9)]
    assert frames[0].tobytes() == frames[-1].tobytes() == idle.tobytes()
    for im in frames:
        q = np.array(im)
        assert im.mode == "RGBA" and im.size == (192, 208)
        assert np.array_equal(q[~editable], p[~editable])
        assert im.getbbox() == idle.getbbox()
        assert set(np.unique(q[:, :, 3])) == {0, 255}
        assert not q[q[:, :, 3] == 0, :3].any()
    for im in frames[2:7]:
        q = np.array(im)
        assert np.array_equal(q[raised], np.array(frames[1])[raised])
        assert np.array_equal(q[lower], np.array(frames[1])[lower])


def test_preview_preserves_frames_and_deliberate_pause():
    from tools.finish_feng_failed_r3 import DURATIONS
    gif = Image.open(OUT / "preview.gif")
    assert gif.n_frames == 8
    for i, duration in enumerate(DURATIONS):
        gif.seek(i)
        assert gif.info["duration"] == duration
    assert Image.open(OUT / "failed-04.png").tobytes() == Image.open(OUT / "failed-05.png").tobytes()


def test_self_review_can_fail_despite_structural_pass():
    report = json.loads((OUT / "validation.json").read_text())
    assert report["structuralChecksPassed"]
    assert report["status"] == "SELF_REVIEW_REJECTED_NOD_TOO_WEAK"
    assert not report["runtimeIntegrated"] and report["userApproval"] == "PENDING"
