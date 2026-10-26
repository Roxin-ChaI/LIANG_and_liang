import json
import numpy as np
import pytest
from PIL import Image

from tools.repair_feng_look_cuff_shirt import BASE, OUT, OFFSETS, EDGES, derive, strip_cell
from tools.repair_feng_look_neck_cutout import skin_mask


@pytest.fixture(scope='module')
def result():
    base = Image.open(BASE).convert('RGBA')
    frames, records = derive(base)
    return base, frames, records


@pytest.mark.parametrize('i',range(16))
def test_local_clothing_only_and_no_hand_or_cuff_damage(result,i):
    base, frames, _ = result
    old, new = np.array(strip_cell(base,i)), np.array(frames[i])
    scope = np.zeros((208,192),bool); scope[82:94,74:85] = True
    assert np.array_equal(old[~scope],new[~scope])
    assert np.array_equal(old[skin_mask(old)],new[skin_mask(old)])
    assert np.array_equal(skin_mask(old),skin_mask(new))
    assert np.array_equal(old[:,:,3],new[:,:,3])
    assert frames[i].getbbox() == strip_cell(base,i).getbbox()
    for y,edge in zip(range(82,94),EDGES):
        delta = round(OFFSETS[i]*(94-y)/12)
        # Existing white cuff and inner forearm remain untouched.
        assert np.array_equal(old[y,:edge+delta+1],new[y,:edge+delta+1])
    if not OFFSETS[i]:
        assert np.array_equal(old,new)


def test_shirt_folds_stay_registered_and_border_separates_white_fabrics(result):
    base, frames, _ = result
    donor = np.array(strip_cell(base,0))
    for i,offset in enumerate(OFFSETS):
        if not offset:continue
        p = np.array(frames[i])
        for y,edge in zip(range(82,94),EDGES):
            delta = round(offset*(94-y)/12)
            if not delta:continue
            assert np.array_equal(p[y,82:85],donor[y,82:85])
            if delta < 0:
                end = min(edge,edge+delta+(1 if y==82 else 2))
                assert p[y,edge+delta+1:end+1,:3].max() < 100
    # The 292.5 degree cuff no longer pulls white shirt into its contour.
    assert np.array(strip_cell(base,13))[84,76,:3].min() > 160
    assert np.array(frames[13])[84,76,:3].max() < 60


def test_exact_existing_colors_provenance_and_saved_review(result):
    base, frames, records = result
    donor = strip_cell(base,0)
    saved = Image.open(OUT/'feng-look-16.png')
    assert saved.mode == 'RGBA' and saved.size == (3072,208)
    report = json.loads((OUT/'validation.json').read_text())
    assert report['status'] == 'PENDING_USER_REVIEW' and not report['installed']
    for i,(frame,edits) in enumerate(zip(frames,records)):
        old,new = np.array(strip_cell(base,i)),np.array(frame)
        assert len(edits) == np.any(old!=new,axis=2).sum()
        for edit in edits:
            assert frame.getpixel(tuple(edit['xy'])) == donor.getpixel(tuple(edit['source_xy']))
        assert strip_cell(saved,i).tobytes() == frame.tobytes()
        assert set(np.unique(new[:,:,3])) <= {0,255}
        assert not new[new[:,:,3]==0].any()
    for name in ('cuff-light-preview','look-light-preview'):
        gif = Image.open(OUT/f'{name}.gif')
        assert gif.n_frames == 16
        for i in range(16):
            gif.seek(i)
            assert gif.info['duration']==400
            assert min(gif.convert('RGB').getpixel((0,0)))>230
