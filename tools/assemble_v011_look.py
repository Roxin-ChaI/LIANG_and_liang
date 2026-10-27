"""Integrate the user-approved Look repairs without changing any other row."""
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.assemble_approved_actions import validate_atlas

BASE = ROOT/'assets/rework/v0.1.0/approved-actions-integration-2026-10-23'
OUT = ROOT/'assets/releases/v0.1.1'
SOURCES = {
    'gu': ROOT/'assets/rework/v0.1.0/gu-look-neck-connection-2026-10-25/gu-look-16.png',
    'feng': ROOT/'assets/rework/v0.1.0/feng-look-cuff-shirt-separation-2026-10-27/feng-look-16.png',
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build(output=OUT):
    if output.exists():
        raise FileExistsError('Release atlas output already exists')
    prepared = {}
    report = {'version':'0.1.1','spriteVersion':2,'atlasSize':[1536,2288],
              'approval':'User requested formal App integration and v0.1.1 release after reviewing final repairs.',
              'changedRows':[9,10],'otherRows':'byte-identical decoded RGBA to v0.1.0 selection',
              'limitations':'Existing semi-transparent work pixels and unused Idle slot 6 retained; scoped validator.',
              'forms':{}}
    for form,source in SOURCES.items():
        atlas = Image.open(BASE/f'{form}.webp').convert('RGBA')
        strip = Image.open(source)
        if strip.mode != 'RGBA' or strip.size != (3072,208):
            raise ValueError('Unexpected Look strip')
        pixels = np.array(strip)
        if set(np.unique(pixels[:,:,3])) - {0,255} or pixels[pixels[:,:,3]==0].any():
            raise ValueError('Look transparency is not clean')
        for i in range(16):
            frame = strip.crop((i*192,0,(i+1)*192,208))
            atlas.paste(frame,((i%8)*192,(9+i//8)*208))
        validate_atlas(atlas)
        prepared[form] = atlas
        report['forms'][form] = {'source':str(source.relative_to(ROOT)), 'sourceSha256':sha(source),
                                'base':str((BASE/f'{form}.webp').relative_to(ROOT)),
                                'baseSha256':sha(BASE/f'{form}.webp')}
    output.mkdir(parents=True)
    for form,atlas in prepared.items():
        target = output/f'{form}.webp'
        atlas.save(target,lossless=True,exact=True,method=6)
        if Image.open(target).convert('RGBA').tobytes() != atlas.tobytes():
            raise ValueError('Lossless atlas round trip failed')
        report['forms'][form]['sha256'] = sha(target)
    (output/'manifest.json').write_text(json.dumps(report,indent=2)+'\n')
    return report


if __name__ == '__main__':
    print(json.dumps(build(),indent=2))
