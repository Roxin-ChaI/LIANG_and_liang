"""Separate deterministic left-derivation checks from user visual approval."""
import json

import numpy as np
import pytest
from PIL import Image

from tools.build_gu_drag_left_suspended import (
    OUT, RIGHT, RIGHT_ROOT, assert_unapproved, derive_left, verify_right_source,
)
from tools.build_gu_drag_suspended import row_offsets


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
