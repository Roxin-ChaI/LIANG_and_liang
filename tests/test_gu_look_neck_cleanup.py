import numpy as np
from PIL import Image
from tools.repair_gu_look_neck import SOURCE, HEAD_SOURCE, OUT, cell, derive, build


def inputs():
    return Image.open(SOURCE).convert('RGBA'), Image.open(HEAD_SOURCE).convert('RGBA')


def test_changes_are_only_traced_neck_pixel_removals():
    a, b = inputs()
    frames, masks = derive(a,b)
    for i,(frame, mask) in enumerate(zip(frames,masks)):
        old, new = np.array(cell(a,i)), np.array(frame)
        assert frame.size == (192,208) and frame.mode == 'RGBA'
        assert np.array_equal(old[~mask],new[~mask])
        assert np.all(new[mask] == 0)
        assert not mask[:70].any() and not mask[79:].any()
        assert not mask[:,:73].any() and not mask[:,114:].any()


def test_unchanged_front_view_and_body():
    a,b = inputs()
    frames,_ = derive(a,b)
    assert frames[0].tobytes() == cell(a,0).tobytes()
    for i,f in enumerate(frames):
        assert f.crop((0,79,192,208)).tobytes() == cell(a,i).crop((0,79,192,208)).tobytes()


def test_skin_interior_and_blue_clothing_preserved():
    a,b = inputs()
    _,masks = derive(a,b)
    for i,mask in enumerate(masks):
        p=np.array(cell(a,i)).astype(int)
        skin=(p[:,:,0]>140)&(p[:,:,0]>p[:,:,1]+10)&(p[:,:,1]>p[:,:,2]+8)
        blue=p[:,:,2]>p[:,:,0]+8
        assert not (mask & (skin | blue)).any()


def test_alpha_and_baseline_unchanged():
    a,b = inputs()
    frames,_ = derive(a,b)
    for i,f in enumerate(frames):
        p=np.array(f)
        assert set(np.unique(p[:,:,3])) <= {0,255}
        assert not p[p[:,:,3]==0].any()
        assert f.getbbox() == cell(a,i).getbbox()


def test_packaged_candidate_matches_derivation():
    a,b = inputs()
    frames,_ = derive(a,b)
    strip=Image.open(OUT/'gu-look-16.png')
    assert strip.size == (3072,208)
    for i,f in enumerate(frames):
        assert strip.crop((i*192,0,(i+1)*192,208)).tobytes()==f.tobytes()


def test_previews_are_light_background_and_full_direction_cycle(tmp_path):
    build(tmp_path)
    for name in ('look-light-preview','neck-light-preview'):
        gif=Image.open(tmp_path/f'{name}.gif')
        assert gif.n_frames==16
        for i in range(16):
            gif.seek(i)
            assert min(gif.convert('RGB').getpixel((0,0)))>230
