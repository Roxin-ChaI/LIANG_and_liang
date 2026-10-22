"""Structural checks do not grant human art approval."""
import json
import pytest
from PIL import Image

from tools.prepare_gu_drag_suspended import OUT, ROOT, GU, prepare, sha, assert_unapproved
from tools.build_animation_review import cell


def test_references_are_exact_idle_pixels():
    canonical = cell(Image.open(GU).convert("RGBA"), 0, 0)
    assert Image.open(OUT / "canonical-idle.png").tobytes() == canonical.tobytes()
    assert canonical.getbbox() == (54, 4, 122, 204)
    enlarged = Image.open(OUT / "idle-reference-4x.png")
    assert enlarged.resize((192, 208), Image.Resampling.NEAREST).tobytes() == canonical.tobytes()


def test_source_hashes_unchanged_and_scope_is_only_gu_right():
    manifest = json.loads((OUT / "source-manifest.json").read_text())
    for name, digest in manifest["sources"].items():
        assert sha(ROOT / name) == digest
    assert manifest["scope"] == "gu-running-right-only"
    assert manifest["frameCount"] == 8
    assert manifest["userApproval"] == "PENDING"
    assert not manifest["runtimeIntegrated"]
    assert "feng-look-intermediates" in manifest["deferred"]


def test_approval_freeze_guard(tmp_path):
    (tmp_path / "review-status.json").write_text('{"generatorLocked":true}')
    with pytest.raises(RuntimeError, match="frozen"):
        assert_unapproved(tmp_path)


def test_first_body_draft_is_explicitly_rejected():
    report = json.loads((OUT / "base-self-review.json").read_text())
    assert report["status"] == "SELF_REVIEW_REJECTED_ARM_LENGTH_AND_WAIST"
    assert not report["runtimeIntegrated"]
    idle = Image.open(OUT / "canonical-idle.png")
    draft = Image.open(OUT / "suspended-base.png")
    assert draft.crop((0,0,192,88)).tobytes() == idle.crop((0,0,192,88)).tobytes()


def test_revised_pose_reuses_original_upper_body_and_is_airborne():
    from tools.build_gu_drag_suspended import R2
    from tools.finish_feng_look_r6 import components
    import numpy as np
    idle = np.array(Image.open(OUT / "canonical-idle.png"))
    pose = Image.open(R2 / "suspended-base.png")
    p = np.array(pose)
    assert np.array_equal(idle[:160], p[:160])
    assert pose.getbbox() == (54,4,122,194)
    assert len(components(pose)) == 1
    assert set(np.unique(p[:,:,3])) == {0,255}
    assert not p[p[:,:,3] == 0,:3].any()
    assert pose.getbbox()[3]-1 < 203


def final_frames():
    from tools.build_gu_drag_suspended import R2
    return [Image.open(R2/f"right-{i:02d}.png").convert("RGBA") for i in range(1,9)]


def test_eight_real_frames_and_exact_strip_order():
    from tools.build_gu_drag_suspended import R2
    frames=final_frames()
    assert len({im.tobytes() for im in frames}) == 8
    strip=Image.open(R2/"gu-running-right.png")
    assert strip.mode=="RGBA" and strip.size==(1536,208)
    for i,frame in enumerate(frames):
        assert frame.size==(192,208)
        assert strip.crop((i*192,0,(i+1)*192,208)).tobytes()==frame.tobytes()


def test_head_fixed_while_torso_hands_and_feet_move_together():
    import numpy as np
    from tools.build_gu_drag_suspended import R2,row_offsets
    base=np.array(Image.open(R2/"suspended-base.png"))
    idle=np.array(Image.open(OUT/"canonical-idle.png"))
    for i,frame in enumerate(final_frames()):
        p=np.array(frame)
        assert np.array_equal(p[:88],idle[:88])
        for y,dx in enumerate(row_offsets(i)):
            x=np.where(base[y,:,3]>0)[0]
            assert np.array_equal(p[y,x+dx],base[y,x])
            assert int((p[y,:,3]>0).sum())==len(x)
        assert row_offsets(i)[130] < 0
        assert row_offsets(i)[150] < 0
        assert row_offsets(i)[193] < 0
    for y in [110,130,150,180,193]:
        assert len({int(row_offsets(i)[y]) for i in range(8)})>=2


def test_alpha_palette_connectedness_no_clipping_or_ground_contact():
    import numpy as np
    from tools.build_gu_drag_suspended import R2
    from tools.finish_feng_look_r6 import components
    base=np.array(Image.open(R2/"suspended-base.png"))
    colors={tuple(c) for c in base[base[:,:,3]>0]}
    for frame in final_frames():
        p=np.array(frame)
        assert set(np.unique(p[:,:,3]))=={0,255}
        assert not p[p[:,:,3]==0,:3].any()
        assert {tuple(c) for c in p[p[:,:,3]>0]}==colors
        assert len(components(frame))==1
        box=frame.getbbox()
        assert box[0]>=4 and box[1]>=4 and box[2]<=188
        assert box[3]==194
        assert not p[194:].any()


def test_offsets_and_loop_cannot_introduce_large_discontinuities():
    import numpy as np
    from tools.build_gu_drag_suspended import row_offsets
    for i in range(8):
        current=row_offsets(i)
        adjacent=row_offsets((i+1)%8)
        assert int(np.abs(np.diff(current)).max())<=1
        assert int(np.abs(adjacent-current).max())<=3
        assert not current[:88].any()


def test_preview_order_frame_count_and_actual_drag_cadence():
    from tools.build_gu_drag_suspended import R2,DURATIONS
    assert DURATIONS==[120]*8
    for name,durations in [("preview.gif",DURATIONS),("preview-native.gif",DURATIONS),
                           ("idle-comparison.gif",DURATIONS),("preview-slow.gif",[500]*8)]:
        im=Image.open(R2/name)
        assert im.n_frames==8
        assert im.info["loop"]==0
        for i,duration in enumerate(durations):
            im.seek(i)
            assert im.info["duration"]==duration


def test_user_approval_is_scoped_and_does_not_claim_runtime_verification():
    from tools.build_gu_drag_suspended import R2
    validation=json.loads((R2/"validation.json").read_text())
    review=json.loads((R2/"review-status.json").read_text())
    assert validation["checksPassed"]
    assert validation["uniqueFrames"]==8
    assert review["status"]==validation["status"]=="GU_DRAG_RIGHT_ART_APPROVED"
    assert review["userApproval"]==validation["userApproval"]=="APPROVED"
    assert review["reviewDate"]==validation["reviewDate"]=="2026-10-22"
    assert review["userFeedback"]=="可以,当前审核通过"
    assert review["generatorLocked"]
    assert "excludes rejected draft" in review["approvedScope"]
    assert not review["runtimeIntegrated"] and not validation["runtimeIntegrated"]
    assert validation["dynamicBrowserReview"].startswith("NOT_VERIFIED")


def test_approved_frames_strip_and_review_gifs_are_frozen():
    from tools.build_gu_drag_suspended import R2
    record=json.loads((R2/"review-status.json").read_text())
    expected={f"right-{i:02d}.png" for i in range(1,9)} | {
        "gu-running-right.png","preview.gif","preview-slow.gif",
        "preview-native.gif","idle-comparison.gif"}
    assert set(record["sha256"])==expected
    for name,digest in record["sha256"].items():
        assert sha(R2/name)==digest


def test_approved_candidate_writers_abort_without_touching_files():
    from tools.build_gu_drag_suspended import R2,normalize_r2,animate
    before={str(p.relative_to(OUT)):sha(p) for p in OUT.rglob("*") if p.is_file()}
    for writer in [prepare,normalize_r2,animate]:
        with pytest.raises(RuntimeError,match="frozen"):
            writer()
    after={str(p.relative_to(OUT)):sha(p) for p in OUT.rglob("*") if p.is_file()}
    assert after==before
