import json
import numpy as np
import pytest
from PIL import Image

from tools.repair_feng_look_cuff import BASE, OUT, ROOT, OFFSETS, derive, strip_cell
from tools.repair_feng_look_neck_cutout import skin_mask


def inputs():
    base = Image.open(BASE).convert('RGBA')
    frames, edits = derive(base)
    return base, frames, edits


def test_uses_pre_rejection_candidate_not_rejected_upper_body():
    assert BASE.parent.name == 'feng-look-hand-join-2026-10-25'
    rejected = ROOT/'assets/rework/v0.1.0/feng-look-upper-join-2026-10-25'
    assert json.loads((rejected/'review-status.json').read_text())['status'] == 'REJECTED'
    from tools.repair_feng_look_upper_join import build
    with pytest.raises(RuntimeError, match='rejected'):
        build()


@pytest.mark.parametrize('i', range(16))
def test_head_skin_shoulders_and_outside_local_wrist_are_byte_identical(i):
    base, frames, _ = inputs()
    old, new = np.array(strip_cell(base,i)), np.array(frames[i])
    allowed = np.zeros((208,192),bool)
    allowed[68:90,60:98] = True
    allowed[82:94,64:85] = True
    assert np.array_equal(old[~allowed],new[~allowed])
    assert np.array_equal(old[skin_mask(old)],new[skin_mask(old)])
    assert np.array_equal(skin_mask(old),skin_mask(new))
    assert np.array_equal(old[:,:,3],new[:,:,3])
    assert frames[i].getbbox() == strip_cell(base,i).getbbox()


def test_every_changed_color_is_exact_existing_canonical_garment_pixel():
    base, frames, edits = inputs()
    donor = strip_cell(base,0)
    for i, records in enumerate(edits):
        old, new = np.array(strip_cell(base,i)), np.array(frames[i])
        assert len(records) == np.any(old != new,axis=2).sum()
        for record in records:
            assert frames[i].getpixel(tuple(record['xy'])) == donor.getpixel(tuple(record['source_xy']))
            assert record['source_frame'] == 0
            # Forearm/cuff sampling never uses head, face or other animation.
            assert 68 <= record['source_xy'][1] <= 93


def test_cuff_alignment_regression_for_left_displaced_hands():
    base, frames, _ = inputs()
    for i in (9,10,11,13,14,15):
        old, new = np.array(strip_cell(base,i)), np.array(frames[i])
        skin = skin_mask(old)
        ys, xs = np.where(skin[74:82,60:86])
        bottom = xs[ys == ys.max()].mean()+60
        def cuff_center(p):
            rgb = p[83,60:80,:3].astype(int)
            white = (rgb.min(1)>150) & (rgb.max(1)-rgb.min(1)<70)
            return np.flatnonzero(white).mean()+60
        assert abs(cuff_center(new)-bottom) < abs(cuff_center(old)-bottom)
        assert OFFSETS[i] < 0
    # Previously the y82 hand cut returned abruptly to the front-facing cuff.
    assert strip_cell(base,13).getpixel((70,83))[:3] == (34,48,108)
    assert frames[13].getpixel((70,83))[:3] == (193,205,234)


def test_unchanged_cardinals_and_saved_strip():
    base, frames, _ = inputs()
    strip = Image.open(OUT/'feng-look-16.png')
    assert strip.mode == 'RGBA' and strip.size == (3072,208)
    for i, frame in enumerate(frames):
        assert strip_cell(strip,i).tobytes() == frame.tobytes()
        if i in (0,8,12):
            assert frame.tobytes() == strip_cell(base,i).tobytes()
        p = np.array(frame)
        assert set(np.unique(p[:,:,3])) <= {0,255}
        assert not p[p[:,:,3] == 0].any()
    for name in ('look-light-preview','cuff-light-preview'):
        gif = Image.open(OUT/f'{name}.gif')
        assert gif.n_frames == 16
        for i in range(16):
            gif.seek(i)
            assert gif.info['duration'] == 320
            assert min(gif.convert('RGB').getpixel((0,0)))>230
