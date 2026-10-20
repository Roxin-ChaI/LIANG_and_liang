"""Validate the candidate without equating raster invariants to art approval."""
import json
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from tools.review_feng_failed_r3_nod import OUT, BASE
from tools.finish_feng_failed_r3 import masks, DURATIONS
from tools.finish_feng_look_r6 import components


@pytest.fixture
def frames():
    return [Image.open(OUT/f"failed-{i:02d}.png").convert("RGBA") for i in range(1,9)]


def test_head_size_alpha_baseline_and_connectivity(frames):
    idle = Image.open(BASE/"canonical-idle.png").convert("RGBA")
    p = np.array(idle)
    head, raised, lower = masks(idle)
    for im in frames:
        q = np.array(im)
        assert im.size == (192,208)
        assert im.getbbox() == (44,4,148,204)
        assert set(np.unique(q[:,:,3])) == {0,255}
        assert not q[q[:,:,3]==0,:3].any()
        assert len(components(im)) == 1
        mask = Image.fromarray(((q[:,:,3]>0)&head).astype(np.uint8)*255)
        assert mask.getbbox() == (64,4,113,61)
        assert np.array_equal(q[~(head|raised|lower)],p[~(head|raised|lower)])


def test_original_endpoint_and_fixed_wrist_fist(frames):
    p = np.array(Image.open(BASE/"canonical-idle.png").convert("RGBA"))
    _, raised, lower = masks(Image.fromarray(p))
    assert np.array_equal(np.array(frames[0]),p)
    assert np.array_equal(np.array(frames[-1]),p)
    hold = np.array(frames[1])
    for im in frames[1:7]:
        q = np.array(im)
        assert np.array_equal(q[raised],hold[raised])
        assert np.array_equal(q[lower],hold[lower])
        assert np.array_equal(q[77:130],p[77:130])
        assert np.array_equal(q[130:136,126:147],p[130:136,126:147])


def test_generated_local_palette_is_from_idle(frames):
    idle = Image.open(BASE/"canonical-idle.png").convert("RGBA")
    colors = set(map(tuple,np.array(idle).reshape(-1,4)))
    for im in frames:
        assert set(map(tuple,np.array(im).reshape(-1,4))) <= colors


def test_strip_and_gif_preserve_each_frame(frames):
    strip = Image.open(OUT/"feng-failed.png")
    assert strip.mode == "RGBA" and strip.size == (1536,208)
    for i, im in enumerate(frames):
        assert strip.crop((192*i,0,192*(i+1),208)).tobytes() == im.tobytes()
    for name, lengths in [("preview.gif",DURATIONS),("preview-slow.gif",[600]*8),
                          ("reference-comparison.gif",DURATIONS)]:
        gif = Image.open(OUT/name)
        assert gif.n_frames == 8
        for i, duration in enumerate(lengths):
            gif.seek(i)
            assert gif.info["duration"] == duration


def test_honest_review_gate_and_no_runtime_integration():
    report = json.loads((OUT/"validation.json").read_text())
    assert report["structuralChecksPassed"]
    assert report["status"] == "CANDIDATE_READY_FOR_USER_REVIEW"
    assert report["userApproval"] == "PENDING"
    assert not report["runtimeIntegrated"]
    assert report["imagegenUsed"] and report["headSilhouetteLocked"]
    assert report["selfReview"]["limitations"]


def test_first_trial_is_preserved_and_rejected():
    report = json.loads((BASE/"validation.json").read_text())
    assert report["status"] == "SELF_REVIEW_REJECTED_NOD_TOO_WEAK"
    assert report["structuralChecksPassed"]
    assert OUT != BASE
