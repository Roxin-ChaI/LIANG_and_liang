import numpy as np
from PIL import Image
from tools.repair_feng_look_neck_cutout import SOURCE,ORIGINAL,OUT,cell,derive,skin_mask


def inputs():
    return Image.open(SOURCE).convert('RGBA'),Image.open(ORIGINAL).convert('RGBA')


def test_only_small_neck_scope_changes():
    a,b=inputs();frames,records=derive(a,b)
    assert frames[0].tobytes()==cell(a,0).tobytes()
    for i,f in enumerate(frames):
        p=np.array(f);old=np.array(cell(a,i));m=np.any(p!=old,axis=2)
        assert int(m.sum())==len(records[i])
        assert not m[:45].any() and not m[58:].any()
        assert not m[:,:65].any() and not m[:,116:].any()
        assert f.size==(192,208) and f.mode=='RGBA'


def test_added_pixels_are_exact_original_direction_pixels():
    a,b=inputs();frames,records=derive(a,b)
    for i,(f,edits) in enumerate(zip(frames,records)):
        p=np.array(f);source=np.array(cell(b,i))
        for edit in edits:
            x,y=edit['xy']
            if edit['source_xy']:
                assert np.array_equal(p[y,x],source[y,x])
            else:assert not p[y,x].any()


def test_face_skin_neck_skin_and_collar_colors_preserved():
    a,b=inputs();frames,_=derive(a,b)
    for i,f in enumerate(frames):
        old=np.array(cell(a,i));rgb=old[:,:,:3].astype(int)
        protect=skin_mask(old)|((rgb[:,:,2]>rgb[:,:,0]+8)&(old[:,:,3]>0))
        assert np.array_equal(np.array(f)[protect],old[protect])


def test_body_and_hand_seam_are_not_silently_changed():
    a,b=inputs();frames,_=derive(a,b)
    for i,f in enumerate(frames):
        assert f.crop((0,58,192,208)).tobytes()==cell(a,i).crop((0,58,192,208)).tobytes()
        assert f.getbbox()==cell(a,i).getbbox()


def test_known_dangling_neck_pixels_removed_without_new_neck_holes():
    a,b=inputs();frames,_=derive(a,b)
    for i in range(1,6):
        p=np.array(frames[i]);old=np.array(cell(a,i))
        # This location is no longer an isolated donor dot: its pixel is
        # restored from the real directional hair silhouette (or transparent
        # when the source has no hair here).
        assert np.array_equal(p[52,74],np.array(cell(b,i))[52,74])
        assert old[52,74,3]==255
        assert np.array_equal(p[54:70,85:99],old[54:70,85:99])


def test_saved_png_and_previews():
    a,b=inputs();frames,_=derive(a,b);strip=Image.open(OUT/'feng-look-16.png')
    for i,f in enumerate(frames):
        p=np.array(f)
        assert set(np.unique(p[:,:,3]))<={0,255}
        assert not p[p[:,:,3]==0].any()
        assert strip.crop((i*192,0,(i+1)*192,208)).tobytes()==f.tobytes()
    for name in ('look-light-preview','neck-light-preview'):
        gif=Image.open(OUT/f'{name}.gif');assert gif.n_frames==16
        for i in range(16):
            gif.seek(i);assert min(gif.convert('RGB').getpixel((0,0)))>230
