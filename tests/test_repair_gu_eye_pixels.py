import hashlib

import pytest
from PIL import Image

from tools.repair_gu_eye_pixels import SOURCE, SOURCE_SHA, EDITS, ROWS, cell, repair, build


def test_source_is_corrected_frozen_atlas():
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == SOURCE_SHA
    atlas = Image.open(SOURCE).convert('RGBA')
    for state, index in EDITS:
        assert cell(atlas, ROWS[state][0], index).getchannel('A').getbbox()[3]-1 == 203


@pytest.mark.parametrize('key', list(EDITS))
def test_only_eye_regions_change(key):
    atlas = Image.open(SOURCE).convert('RGBA')
    before = cell(atlas, ROWS[key[0]][0], key[1]); idle = cell(atlas, 0, 0)
    after, _, mask, changed = repair(before, idle, EDITS[key])
    assert 0 < len(changed) <= len(EDITS[key])*50
    assert before.getchannel('A').tobytes() == after.getchannel('A').tobytes()
    assert before.getchannel('A').getbbox() == after.getchannel('A').getbbox()
    assert all(a == b for a,b,m in zip(before.get_flattened_data(),after.get_flattened_data(),mask.get_flattened_data()) if m == 0)
    assert set(after.convert('RGB').get_flattened_data()) <= set(before.convert('RGB').get_flattened_data()) | set(idle.convert('RGB').get_flattened_data())


def test_unlisted_frames_and_formal_source_unchanged(tmp_path):
    report = build(tmp_path/'candidate')
    assert not report['visualApproved']
    atlas = Image.open(SOURCE).convert('RGBA')
    for state,(row,count) in ROWS.items():
        strip = Image.open(tmp_path/'candidate'/f'{state}.png')
        for index in range(count):
            if (state,index) not in EDITS:
                assert cell(strip,0,index).tobytes() == cell(atlas,row,index).tobytes()
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == SOURCE_SHA
    with pytest.raises(ValueError,match='overwrite'):
        build(tmp_path/'candidate')


def test_invalid_inputs_rejected():
    with pytest.raises(ValueError,match='RGBA'):
        repair(Image.new('RGB',(192,208)),Image.new('RGBA',(192,208)),[('left',(71,59))])
    with pytest.raises(ValueError,match='bounds'):
        repair(Image.new('RGBA',(192,208)),Image.new('RGBA',(192,208)),[('left',(190,205))])
