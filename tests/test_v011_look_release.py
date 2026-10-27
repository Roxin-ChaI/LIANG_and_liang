import json
import pytest
from PIL import Image
from tools.assemble_v011_look import BASE, OUT, SOURCES, ROOT, build, sha
from tools.assemble_approved_actions import validate_atlas
from tools.build_standalone_app import source_files


@pytest.mark.parametrize('form',('gu','feng'))
def test_release_only_replaces_look_with_exact_final_pixels(form):
    old = Image.open(BASE/f'{form}.webp').convert('RGBA')
    new = Image.open(OUT/f'{form}.webp').convert('RGBA')
    strip = Image.open(SOURCES[form])
    validate_atlas(new)
    assert old.crop((0,0,1536,9*208)).tobytes() == new.crop((0,0,1536,9*208)).tobytes()
    for i in range(16):
        x,y = i%8*192,(9+i//8)*208
        assert new.crop((x,y,x+192,y+208)).tobytes() == strip.crop((i*192,0,(i+1)*192,208)).tobytes()
    record = json.loads((OUT/'manifest.json').read_text())['forms'][form]
    assert sha(OUT/f'{form}.webp') == record['sha256']
    assert sha(SOURCES[form]) == record['sourceSha256']
    selected = {str(logical):path for path,logical in source_files()}
    assert selected[f'assets/builds/{form}/spritesheet.webp'] == OUT/f'{form}.webp'


def test_frozen_release_and_version():
    with pytest.raises(FileExistsError):build()
    assert json.loads((ROOT/'standalone-app/package.json').read_text())['version']=='0.1.1'
