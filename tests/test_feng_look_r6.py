"""R6 structural safeguards, not a substitute for user art approval."""
import hashlib
import json
import pytest

import numpy as np
from PIL import Image

from tools.finish_feng_look_r6 import OUT,ROOT,components


def test_body_hand_cuff_elbow_and_suit_unchanged():
    p=np.array(Image.open(OUT/"canonical-idle.png"))
    protected=np.array(Image.open(OUT/"protected-mask.png"))>0
    for i in range(1,5):
        q=np.array(Image.open(OUT/f"cardinal-{i:02d}.png"))
        assert np.array_equal(p[61:],q[61:])
        assert np.array_equal(p[protected],q[protected])
        assert np.array_equal(p[49:61,85:88],q[49:61,85:88])


def test_canvas_registration_alpha_and_connectivity():
    for i in range(1,5):
        im=Image.open(OUT/f"cardinal-{i:02d}.png");p=np.array(im)
        assert im.mode=="RGBA" and im.size==(192,208)
        assert im.getbbox()==(44,4,148,204)
        assert set(np.unique(p[:,:,3]))=={0,255}
        assert not p[p[:,:,3]==0,:3].any()
        assert len(components(im))==1


def test_generated_face_uses_only_canonical_head_palette():
    p=np.array(Image.open(OUT/"canonical-idle.png"))
    colors=set(map(tuple,p.reshape(-1,4)))|{(0,0,0,0)}
    for i in range(1,5):
        q=np.array(Image.open(OUT/f"cardinal-{i:02d}.png"))
        assert set(map(tuple,q.reshape(-1,4))) <= colors


def test_review_has_four_distinct_poses_and_honest_status():
    report=json.loads((OUT/"validation.json").read_text())
    assert report["userApproval"]=="APPROVED"
    assert not report["runtimeIntegrated"]
    assert not report["complete16DirectionAnimation"]
    assert report["headOnlyNormalization"]["uniformScale"] is False
    assert [f["direction"] for f in report["frames"]]==[0,90,180,270]
    assert report["structuralChecksPassed"]
    assert len({Image.open(OUT/f"cardinal-{i:02d}.png").tobytes() for i in range(1,5)})==4


def test_gif_previews_have_every_pose():
    for name,duration in [("cardinals-preview.gif",700),("head-and-hand.gif",700),("gu-reference-preview.gif",850)]:
        gif=Image.open(OUT/name)
        assert gif.n_frames==4
        for i in range(4):gif.seek(i);assert gif.info["duration"]==duration


def test_official_feng_atlas_unchanged():
    assert hashlib.sha256((ROOT/"assets/builds/feng/spritesheet.webp").read_bytes()).hexdigest()=="d697e573268b66cb0f6a062480ec87c8c11712ca34b57f8c2fc0a97ed6e2164a"


def test_approved_cardinals_match_frozen_hashes():
    record=json.loads((OUT/"review-status.json").read_text())
    assert record["generatorLocked"] and record["userApproval"]=="APPROVED"
    assert len(record["sha256"])==4
    for name,expected in record["sha256"].items():
        assert hashlib.sha256((OUT/name).read_bytes()).hexdigest()==expected


def test_reconfirmation_preserves_original_approval_scope():
    record=json.loads((OUT/"review-status.json").read_text())
    report=json.loads((OUT/"validation.json").read_text())
    assert record["reviewDate"]=="2026-10-20"
    assert record["reconfirmedDate"]=="2026-10-21"
    assert record["reconfirmationFeedback"]=="Feng Look 审核通过"
    assert report["approvalReconfirmedDate"]==record["reconfirmedDate"]
    assert record["directions"]==[0,90,180,270]
    assert not record["runtimeIntegrated"]
    assert not record["complete16DirectionAnimation"]


def test_every_writer_refuses_to_overwrite_approved_art():
    from tools.finish_feng_look_r6 import extract,composite_trial,clean_head_candidates,review
    from tools.prepare_feng_look_r6 import build
    for fn,args in [(build,()),(extract,()),(composite_trial,([],)),(clean_head_candidates,()),(review,([],))]:
        with pytest.raises(RuntimeError,match="frozen"):
            fn(*args)
