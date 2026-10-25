import numpy as np
from PIL import Image
from tools.repair_feng_look_hand_join import (
    PREVIOUS, ORIGINAL, OUT, UNCHANGED, cell, strip_cell, derive, skin_mask,
)


def inputs():
    return Image.open(PREVIOUS).convert('RGBA'),Image.open(ORIGINAL).convert('RGBA')


def test_directional_hand_is_copied_with_exact_pixel_provenance():
    a,b=inputs();frames,masks=derive(a,b)
    for i,(frame,m) in enumerate(zip(frames,masks)):
        old=np.array(strip_cell(a,i));new=np.array(frame);source=np.array(cell(b,i))
        assert np.array_equal(new[m],source[m])
        assert np.array_equal(new[~m],old[~m])


def test_scope_excludes_head_neck_shoulders_and_lower_body():
    a,b=inputs();frames,masks=derive(a,b)
    for i,(frame,m) in enumerate(zip(frames,masks)):
        assert not m[:68].any() and not m[90:].any()
        assert not m[:,:60].any() and not m[:,98:].any()
        old=strip_cell(a,i)
        assert frame.crop((0,0,192,68)).tobytes()==old.crop((0,0,192,68)).tobytes()
        assert frame.crop((0,90,192,208)).tobytes()==old.crop((0,90,192,208)).tobytes()


def test_old_y74_splice_reproduced_and_repaired():
    a,b=inputs();frames,_=derive(a,b)
    for i in (10,11,13,14,15):
        old=np.array(strip_cell(a,i));source=np.array(cell(b,i));new=np.array(frames[i])
        core=skin_mask(source)
        region=np.zeros((208,192),bool);region[71:81,65:93]=True
        core &= region
        assert np.any(old[core]!=source[core]), 'regression must detect original splice'
        assert np.array_equal(new[core],source[core])
        assert np.all(new[core,3]==255)


def test_skin_cross_section_spans_original_cut_without_transparent_holes():
    a,b=inputs();frames,_=derive(a,b)
    for i in range(16):
        if i in UNCHANGED:continue
        source=np.array(cell(b,i));new=np.array(frames[i])
        for y in range(70,82):
            xs=np.flatnonzero(skin_mask(source)[y,64:93])+64
            if len(xs):
                assert np.array_equal(new[y,xs],source[y,xs])


def test_unchanged_cardinals_geometry_and_alpha():
    a,b=inputs();frames,_=derive(a,b)
    for i,frame in enumerate(frames):
        old=strip_cell(a,i);p=np.array(frame)
        if i in UNCHANGED:assert frame.tobytes()==old.tobytes()
        assert frame.getbbox()==old.getbbox()
        assert frame.size==(192,208) and frame.mode=='RGBA'
        assert set(np.unique(p[:,:,3]))<={0,255}
        assert not p[p[:,:,3]==0].any()


def test_saved_sequence_and_light_previews():
    a,b=inputs();frames,_=derive(a,b);strip=Image.open(OUT/'feng-look-16.png')
    for i,frame in enumerate(frames):
        assert strip_cell(strip,i).tobytes()==frame.tobytes()
    for name in ('hand-light-preview','look-light-preview'):
        gif=Image.open(OUT/f'{name}.gif');assert gif.n_frames==16
        for i in range(16):
            gif.seek(i);assert min(gif.convert('RGB').getpixel((0,0)))>230
