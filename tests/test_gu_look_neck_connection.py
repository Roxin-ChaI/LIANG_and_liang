import numpy as np
from PIL import Image
from tools.repair_gu_look_neck_connection import (
    PREVIOUS, HEAD_SOURCE, OUT, NECK_SPANS, derive, previous_cell, cell, skin_mask,
)


def inputs():
    return Image.open(PREVIOUS).convert('RGBA'), Image.open(HEAD_SOURCE).convert('RGBA')


def test_exact_source_pixel_provenance_and_local_scope():
    prev,original=inputs(); frames,records=derive(prev,original)
    for i,(frame,edits) in enumerate(zip(frames,records)):
        p=np.array(frame);old=np.array(previous_cell(prev,i));s=np.array(cell(original,i))
        mask=np.any(p!=old,axis=2)
        assert int(mask.sum())==len(edits)
        assert not mask[:74].any() and not mask[90:].any()
        assert not mask[:,:85].any() and not mask[:,105:].any()
        for edit in edits:
            x,y=edit['xy'];sx,sy=edit['source_xy']
            assert np.array_equal(p[y,x],s[sy,sx])
        assert np.all(p[mask,3]==255)


def test_neck_interior_has_no_transparent_cutout_slits():
    prev,original=inputs();frames,_=derive(prev,original)
    old_holes=0
    for i in range(1,16):
        skin=skin_mask(np.array(cell(original,i)))
        old=np.array(previous_cell(prev,i));p=np.array(frames[i])
        for y,l,r in NECK_SPANS:
            if skin[y,85:105].any():
                old_holes+=int((old[y,l:r,3]==0).sum())
                assert np.all(p[y,l:r,3]==255)
    assert old_holes>0  # Regression actually detects the rejected candidate.


def test_front_head_and_body_are_unchanged():
    prev,original=inputs();frames,_=derive(prev,original)
    assert frames[0].tobytes()==previous_cell(prev,0).tobytes()
    for i,frame in enumerate(frames):
        old=previous_cell(prev,i)
        assert frame.crop((0,0,192,74)).tobytes()==old.crop((0,0,192,74)).tobytes()
        assert frame.crop((0,90,192,208)).tobytes()==old.crop((0,90,192,208)).tobytes()
        assert frame.getbbox()==old.getbbox()


def test_clean_alpha_and_no_external_jaw_restoration():
    prev,original=inputs();frames,_=derive(prev,original)
    for i,frame in enumerate(frames):
        p=np.array(frame);old=np.array(previous_cell(prev,i))
        assert set(np.unique(p[:,:,3])) <= {0,255}
        assert not p[p[:,:,3]==0].any()
        assert np.array_equal(p[70:79,:85],old[70:79,:85])
        assert np.array_equal(p[70:79,105:],old[70:79,105:])


def test_saved_frames_and_light_gif():
    prev,original=inputs();frames,_=derive(prev,original)
    strip=Image.open(OUT/'gu-look-16.png')
    for i,frame in enumerate(frames):
        assert previous_cell(strip,i).tobytes()==frame.tobytes()
    for name in ('neck-light-preview','look-light-preview'):
        gif=Image.open(OUT/f'{name}.gif');assert gif.n_frames==16
        for i in range(16):
            gif.seek(i);assert min(gif.convert('RGB').getpixel((0,0)))>230
