import numpy as np
import pytest
from PIL import Image

from tools.repair_feng_look_upper_join import (
    PREVIOUS, SOURCE, OUT, START, END, cell, strip_cell, derive,
)


def inputs():
    return Image.open(PREVIOUS).convert('RGBA'), Image.open(SOURCE).convert('RGBA')


def test_complete_upper_unit_has_one_source_not_a_palm_patch():
    old, source = inputs()
    for i, frame in enumerate(derive(old, source)):
        assert frame.crop((0, START, 192, END)).tobytes() == cell(source, i).crop((0, START, 192, END)).tobytes()
        # This is intentionally an original-art recovery, not a new drawing.
        assert frame.tobytes() == cell(source, i).tobytes()


def test_head_lower_body_and_identical_join_band_are_preserved():
    old, source = inputs()
    frames = derive(old, source)
    for i, frame in enumerate(frames):
        before = strip_cell(old, i)
        for region in ((0,0,192,START), (0,END,192,208), (0,86,192,94)):
            assert frame.crop(region).tobytes() == before.crop(region).tobytes()
        assert frame.getbbox()[3] == 204
        assert frame.crop((0,90,192,208)).tobytes() == frames[0].crop((0,90,192,208)).tobytes()


def test_regression_previous_palm_patch_left_mismatched_sleeve_and_lapel():
    old, source = inputs()
    for i in (1, 4, 9, 11, 13, 14, 15):
        a, b = np.array(strip_cell(old,i)), np.array(cell(source,i))
        # Outside the old palm rectangle: source shoulder and lapel were lost.
        region = np.zeros((208,192), bool)
        region[55:84,43:122] = True
        region[68:90,60:98] = False
        assert np.any(a[region] != b[region])
        repaired = np.array(derive(old,source)[i])
        assert np.array_equal(repaired[region], b[region])


@pytest.mark.parametrize('xy', [(80,40), (80,88), (80,95)])
def test_changed_join_or_protected_region_fails_closed(xy):
    old, source = inputs()
    damaged = old.copy()
    pixel = list(damaged.getpixel(xy)); pixel[0] ^= 1
    damaged.putpixel(xy, tuple(pixel))
    with pytest.raises(ValueError): derive(damaged,source)


def test_saved_art_and_previews_match_candidate():
    old, source = inputs()
    strip = Image.open(OUT/'feng-look-16.png')
    assert strip.size == (3072,208) and strip.mode == 'RGBA'
    for i, frame in enumerate(derive(old,source)):
        assert strip_cell(strip,i).tobytes() == frame.tobytes()
        p = np.array(frame)
        assert set(np.unique(p[:,:,3])) <= {0,255}
        assert not p[p[:,:,3] == 0].any()
    for name in ('look-light-preview', 'upper-body-light-preview'):
        gif = Image.open(OUT/f'{name}.gif')
        assert gif.n_frames == 16
        for i in range(16):
            gif.seek(i)
            assert gif.info['duration'] == 320
            assert min(gif.convert('RGB').getpixel((0,0))) > 230
