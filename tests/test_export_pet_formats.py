import io
import json
import zipfile

import numpy as np
import pytest
from PIL import Image

from tools.export_pet_formats import (
    SOURCE, COUNTS, PET_ID, PROFILES, archive, build, digest, normalize,
)


@pytest.fixture(scope='module')
def exported(tmp_path_factory):
    output = tmp_path_factory.mktemp('pet-formats')/'exports'
    before = {f:digest((SOURCE/f'{f}.webp').read_bytes()) for f in ('gu','feng')}
    report = build(output)
    assert before == {f:digest((SOURCE/f'{f}.webp').read_bytes()) for f in ('gu','feng')}
    return output,report


@pytest.mark.parametrize('profile',PROFILES)
@pytest.mark.parametrize('form',('gu','feng'))
def test_every_export_preserves_active_frames_and_clears_unused_cells(exported,profile,form):
    output,report = exported
    rows = PROFILES[profile]
    folder = output/profile/form/PET_ID
    pet = json.loads((folder/'pet.json').read_text())
    assert pet['id'] == PET_ID and pet['spritesheetPath'] == 'spritesheet.webp'
    assert pet['spriteVersionNumber'] == (2 if rows==11 else 1)
    im = Image.open(folder/pet['spritesheetPath']).convert('RGBA')
    src = Image.open(SOURCE/f'{form}.webp').convert('RGBA')
    assert im.size == (1536,rows*208)
    for row,count in enumerate(COUNTS[:rows]):
        for col in range(8):
            box = (col*192,row*208,(col+1)*192,(row+1)*208)
            frame = im.crop(box)
            if col < count:
                assert frame.tobytes() == src.crop(box).tobytes()
                bounds = frame.getbbox()
                assert bounds and bounds[0]>0 and bounds[1]>0 and bounds[2]<192 and bounds[3]<208
            else:
                assert not any(frame.tobytes())
    p = np.array(im)
    assert not p[p[:,:,3]==0].any()
    assert Image.open(folder.parent/'spritesheet.png').tobytes() == im.tobytes()
    record = next(r for r in report['packages'] if r['profile']==profile and r['form']==form)
    assert record['frames'] == sum(COUNTS[:rows])
    assert record['sha256'] == digest((output/record['file']).read_bytes())
    with zipfile.ZipFile(output/record['file']) as z:
        assert z.testzip() is None
        assert sorted(z.namelist()) == [f'{PET_ID}/pet.json',f'{PET_ID}/spritesheet.webp']
        for name in z.namelist():
            assert z.read(name) == (folder.parent/name).read_bytes()


def test_compatible_v2_packages_are_identical_and_total_archive_is_complete(exported):
    output,report = exported
    for form in ('gu','feng'):
        names = [output/f'LIANG_and_liang-v0.1.1-{profile}-{form}.zip'
                 for profile in ('codex-v2','dsh-v2')]
        assert names[0].read_bytes() == names[1].read_bytes()
    assert report['runtimeImport'] == 'NOT_TESTED'
    with zipfile.ZipFile(output/'LIANG_and_liang-v0.1.1-pet-formats.zip') as z:
        assert z.testzip() is None
        assert len(z.namelist()) == 9
        for record in report['packages']:
            assert digest(z.read(record['file'])) == record['sha256']
        assert json.loads(z.read('validation.json')) == report
    for line in (output/'SHA256SUMS.txt').read_text().splitlines():
        checksum,name = line.split('  ')
        assert digest((output/name).read_bytes()) == checksum


def test_archive_is_deterministic():
    assert archive({'b':b'B','a':b'A'}) == archive({'a':b'A','b':b'B'})
    with zipfile.ZipFile(io.BytesIO(archive({'pet.json':b'{}'}))) as z:
        assert z.getinfo('pet.json').external_attr >> 16 == 0o100644


def test_refuse_overwriting_existing_exports(exported):
    output,_ = exported
    with pytest.raises(FileExistsError):build(output)


@pytest.mark.parametrize('im,rows',[
    (Image.new('RGB',(1536,2288)),11),
    (Image.new('RGBA',(192,208)),11),
    (Image.new('RGBA',(1536,2288)),10),
])
def test_reject_unsupported_input(im,rows):
    with pytest.raises(ValueError):normalize(im,rows)
