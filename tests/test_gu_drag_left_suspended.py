"""Separate deterministic left-derivation checks from user visual approval."""
import json

import numpy as np
import pytest
from PIL import Image

from tools.build_gu_drag_left_suspended import (
    OUT, RIGHT, RIGHT_ROOT, ROOT, assert_unapproved, derive_left, verify_right_source, build,
)
from tools.build_gu_drag_suspended import row_offsets
from tools.prepare_gu_drag_suspended import sha
from tools.finish_feng_look_r6 import components


def read_right(i):
    return Image.open(RIGHT/f"right-{i+1:02d}.png").convert("RGBA")


def test_requires_approved_frozen_right_source():
    record=verify_right_source()
    assert record["reviewDate"]=="2026-10-22"
    assert len(record["sha256"])==13


def test_rejects_unapproved_and_incomplete_sources(tmp_path):
    p=tmp_path/"review-status.json"
    p.write_text('{"userApproval":"PENDING"}')
    with pytest.raises(ValueError,match="not approved"):
        verify_right_source(tmp_path)
    p.write_text(json.dumps({"status":"GU_DRAG_RIGHT_ART_APPROVED",
        "userApproval":"APPROVED","generatorLocked":True,"sha256":{}}))
    with pytest.raises(ValueError,match="incomplete"):
        verify_right_source(tmp_path)


def test_identity_is_not_mirrored_and_head_stays_idle_exact():
    idle=Image.open(RIGHT_ROOT/"canonical-idle.png").convert("RGBA")
    for i in range(8):
        left=derive_left(read_right(i),i)
        assert left.crop((0,0,192,88)).tobytes()==idle.crop((0,0,192,88)).tobytes()
        assert left.tobytes()!=read_right(i).transpose(Image.Transpose.FLIP_LEFT_RIGHT).tobytes()


def test_reverses_displacement_not_frame_order_or_pixel_order():
    base=np.array(Image.open(RIGHT/"suspended-base.png"))
    for i in range(8):
        left=np.array(derive_left(read_right(i),i))
        right=np.array(read_right(i))
        offsets=row_offsets(i)
        for y,dx in enumerate(offsets):
            source_x=np.flatnonzero(base[y,:,3])
            assert np.array_equal(left[y,source_x-dx],base[y,source_x])
            assert np.array_equal(right[y,source_x+dx],base[y,source_x])
            assert int((left[y,:,3]>0).sum())==len(source_x)
        assert all(-offsets[y] > 0 for y in [130,150,193])


def test_rejects_clipping_instead_of_discarding_pixels():
    frame=Image.new("RGBA",(192,208))
    frame.putpixel((191,193),(5,6,7,255))
    with pytest.raises(ValueError,match="clip"):
        derive_left(frame,2)


def test_rejects_bad_mode_size_alpha_and_index():
    with pytest.raises(ValueError,match="0..7"):
        derive_left(read_right(0),8)
    with pytest.raises(ValueError,match="192x208"):
        derive_left(Image.new("RGB",(192,208)),0)
    frame=read_right(0).copy();frame.putpixel((0,0),(0,0,0,128))
    with pytest.raises(ValueError,match="binary alpha"):
        derive_left(frame,0)


def test_approved_candidate_cannot_be_overwritten(tmp_path):
    (tmp_path/"review-status.json").write_text('{"generatorLocked":true}')
    with pytest.raises(RuntimeError,match="frozen"):
        assert_unapproved(tmp_path)
    before={p.name:sha(p) for p in tmp_path.iterdir()}
    with pytest.raises(RuntimeError,match="frozen"):
        build(tmp_path)
    assert {p.name:sha(p) for p in tmp_path.iterdir()}==before


def read_lefts():
    return [Image.open(OUT/f"left-{i:02d}.png").convert("RGBA") for i in range(1,9)]


def test_saved_frames_match_derivation_and_strip_order():
    frames=read_lefts()
    assert len({im.tobytes() for im in frames})==8
    strip=Image.open(OUT/"gu-running-left.png")
    assert strip.mode=="RGBA" and strip.size==(1536,208)
    for i,f in enumerate(frames):
        assert f.tobytes()==derive_left(read_right(i),i).tobytes()
        assert strip.crop((i*192,0,(i+1)*192,208)).tobytes()==f.tobytes()


def test_outputs_are_connected_airborne_and_have_no_extra_pixels():
    for i,frame in enumerate(read_lefts()):
        p=np.array(frame);r=np.array(read_right(i))
        assert frame.size==(192,208) and frame.mode=="RGBA"
        assert set(np.unique(p[:,:,3]))=={0,255}
        assert not p[p[:,:,3]==0,:3].any()
        assert np.array_equal((p[:,:,3]>0).sum(1),(r[:,:,3]>0).sum(1))
        assert {tuple(c) for c in p[p[:,:,3]>0]}=={tuple(c) for c in r[r[:,:,3]>0]}
        assert len(components(frame))==1
        box=frame.getbbox()
        assert box[0]>=4 and box[1]==4 and box[2]<=188 and box[3]==194


def test_cycle_and_upper_body_motion_are_continuous():
    for i in range(8):
        a=-row_offsets(i);b=-row_offsets((i+1)%8)
        assert int(np.abs(a-b).max())<=3
        assert int(np.abs(np.diff(a)).max())<=1
        assert not a[:88].any()
    for y in [110,130,150,193]:
        assert len({int(row_offsets(i)[y]) for i in range(8)})>=2


def test_all_gifs_retain_eight_frames_and_documented_timing():
    for name in ["preview.gif","preview-native.gif","idle-comparison.gif",
                 "right-left-comparison.gif","preview-slow.gif"]:
        gif=Image.open(OUT/name)
        assert gif.n_frames==8 and gif.info["loop"]==0
        for i in range(8):
            gif.seek(i)
            assert gif.info["duration"]==(500 if name=="preview-slow.gif" else 120)
    assert Image.open(OUT/"preview-native.gif").size==(192,208)


def test_sources_and_live_asset_selection_are_unchanged():
    manifest=json.loads((OUT/"source-manifest.json").read_text())
    assert not manifest["imagegenUsed"] and not manifest["resamplingUsed"]
    for name,digest in manifest["sourceHashes"].items():
        assert sha(ROOT/name)==digest
    assert "standalone-app/asset-overrides.json" in manifest["sourceHashes"]
    verify_right_source()


def test_explicit_user_approval_does_not_claim_runtime_verification():
    validation=json.loads((OUT/"validation.json").read_text())
    review=json.loads((OUT/"review-status.json").read_text())
    assert validation["checksPassed"] and validation["uniqueFrames"]==8
    assert review["status"]==validation["status"]=="GU_DRAG_LEFT_ART_APPROVED"
    assert review["userApproval"]==validation["userApproval"]=="APPROVED"
    assert review["reviewDate"]==validation["reviewDate"]=="2026-10-23"
    assert review["userFeedback"].startswith("审核通过")
    assert "no runtime integration or Feng drag approval" in review["approvedScope"]
    assert not review["runtimeIntegrated"] and not validation["runtimeIntegrated"]
    assert review["generatorLocked"]
    assert validation["dynamicPlayback"].startswith("NOT_VERIFIED")


def test_approved_frames_strip_and_gifs_are_frozen():
    review=json.loads((OUT/"review-status.json").read_text())
    expected={f"left-{i:02d}.png" for i in range(1,9)} | {
        "gu-running-left.png","preview.gif","preview-slow.gif","preview-native.gif",
        "idle-comparison.gif","right-left-comparison.gif"}
    assert set(review["sha256"])==expected
    for name,digest in review["sha256"].items():
        assert sha(OUT/name)==digest


def test_approved_default_build_aborts_without_writes():
    before={p.name:sha(p) for p in OUT.iterdir() if p.is_file()}
    with pytest.raises(RuntimeError,match="frozen"):
        build()
    assert {p.name:sha(p) for p in OUT.iterdir() if p.is_file()}==before


def test_rebuild_is_deterministic_and_does_not_modify_right(tmp_path):
    before={str(p.relative_to(RIGHT_ROOT)):sha(p) for p in RIGHT_ROOT.rglob("*") if p.is_file()}
    result=build(tmp_path)
    assert result["checksPassed"]
    for name in [*[f"left-{i:02d}.png" for i in range(1,9)],"gu-running-left.png",
                 "preview.gif","preview-slow.gif","preview-native.gif","idle-comparison.gif",
                 "right-left-comparison.gif","contact.png","seam-detail.png"]:
        assert sha(tmp_path/name)==sha(OUT/name)
    after={str(p.relative_to(RIGHT_ROOT)):sha(p) for p in RIGHT_ROOT.rglob("*") if p.is_file()}
    assert before==after
