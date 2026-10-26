import hashlib
import json

import numpy as np
import pytest
from PIL import Image

from tools.repair_feng_look_face_gaps import (
    BASE, SOURCE, OUT, cell, strip_cell, derive, neck_holes, eye_samples,
)


def inputs():
    return Image.open(BASE).convert('RGBA'), Image.open(SOURCE).convert('RGBA')


@pytest.mark.parametrize('i', range(16))
def test_all_preexisting_pixels_and_entire_body_preserved(i):
    base, source = inputs(); frames,_ = derive(base,source)
    old=np.array(strip_cell(base,i));new=np.array(frames[i])
    assert np.array_equal(old[old[:,:,3]>0],new[old[:,:,3]>0])
    assert np.array_equal(old[68:],new[68:])
    allowed=neck_holes(old)
    for x,y in eye_samples(i):allowed[y,x]=True
    assert np.array_equal(old[~allowed],new[~allowed])
    assert frames[i].getbbox()==strip_cell(base,i).getbbox()
    assert set(np.unique(new[:,:,3])) <= {0,255}
    assert not new[new[:,:,3]==0].any()


@pytest.mark.parametrize('i,start',[(6,104),(7,105)])
def test_reported_down_right_broken_spectacle_row_is_closed(i,start):
    base,source=inputs();frames,_=derive(base,source)
    old=np.array(strip_cell(base,i));new=np.array(frames[i])
    # Exterior-connected transparent cuts: enclosed-hole filling alone misses them.
    assert np.all(old[46,start:113,3]==0)
    assert np.all(new[46,start:113,3]==255)
    assert np.array_equal(old[47:54],new[47:54])  # eyes/iris/bridge not redrawn


@pytest.mark.parametrize('i', [9,10,11])
def test_reported_left_down_neck_holes_are_filled(i):
    base,source=inputs();frames,_=derive(base,source)
    assert neck_holes(np.array(strip_cell(base,i))).any()
    assert not neck_holes(np.array(frames[i])).any()


def test_exact_color_provenance_and_no_whole_region_replacement():
    base,source=inputs();frames,records=derive(base,source)
    assert sum(map(len,records))==195
    for i,edits in enumerate(records):
        old=strip_cell(base,i);src=cell(source,i)
        for edit in edits:
            xy=tuple(edit['xy']);origin=tuple(edit['source_xy'])
            assert old.getpixel(xy)==(0,0,0,0)
            donor=src if edit['source']=='original same direction' else old
            assert frames[i].getpixel(xy)==donor.getpixel(origin)
        assert not neck_holes(np.array(frames[i])).any()


def test_saved_output_and_previews():
    base,source=inputs();frames,_=derive(base,source)
    sheet=Image.open(OUT/'feng-look-16.png')
    assert sheet.size==(3072,208) and sheet.mode=='RGBA'
    for i,frame in enumerate(frames):
        assert strip_cell(sheet,i).tobytes()==frame.tobytes()
    for name,count in [('look-light-preview',16),('face-light-preview',16),
                       ('down-right-eyes',8),('down-left-neck',8)]:
        gif=Image.open(OUT/f'{name}.gif');assert gif.n_frames==count
        for i in range(count):
            gif.seek(i);assert gif.info['duration']==360
            assert min(gif.convert('RGB').getpixel((0,0)))>230
    report=json.loads((OUT/'validation.json').read_text())
    assert report['status']=='PENDING_USER_REVIEW' and report['installed'] is False
    for path in (BASE,SOURCE):
        assert hashlib.sha256(path.read_bytes()).hexdigest() in report['source_hashes'].values()
