"""Export v0.1.1 art for native Codex and Codex-compatible DSH pet plugins.

No installation, animation retiming, image resampling or runtime sidecars.
"""
import hashlib
import io
import json
from pathlib import Path
import sys
import zipfile

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.assemble_approved_actions import COUNTS, validate_atlas

SOURCE = ROOT/'assets/releases/v0.1.1'
OUT = ROOT/'dist/exports/v0.1.1'
PET_ID = 'liang-no-henshin'
PROFILES = {'codex-v2':11, 'dsh-v2':11, 'dsh-v1-legacy':9}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def normalize(source, rows):
    if source.mode != 'RGBA' or source.size != (1536,2288) or rows not in (9,11):
        raise ValueError('Expected RGBA v2 source and 9/11 output rows')
    validate_atlas(source)
    image = source.crop((0,0,1536,rows*208))
    # Remove unused runtime cells, notably the inherited seventh Idle cell.
    # Every valid frame stays byte-identical, including existing partial alpha.
    for row,count in enumerate(COUNTS[:rows]):
        image.paste((0,0,0,0),(count*192,row*208,1536,(row+1)*208))
    return image


def archive(files):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer,'w',compression=zipfile.ZIP_DEFLATED) as z:
        for name,data in sorted(files.items()):
            item = zipfile.ZipInfo(name,date_time=(2026,10,27,0,0,0))
            item.compress_type = zipfile.ZIP_DEFLATED
            item.external_attr = 0o100644 << 16
            z.writestr(item,data)
    return buffer.getvalue()


def build(output=OUT):
    if output.exists():
        raise FileExistsError('Refusing to overwrite an existing export')
    freeze = json.loads((SOURCE/'manifest.json').read_text())
    images = {}
    for form in ('gu','feng'):
        data = (SOURCE/f'{form}.webp').read_bytes()
        if digest(data) != freeze['forms'][form]['sha256']:
            raise ValueError('Release source checksum mismatch')
        images[form] = Image.open(io.BytesIO(data)).convert('RGBA')
    records = []
    all_files = {}
    for profile,rows in PROFILES.items():
        for form,source in images.items():
            im = normalize(source,rows)
            version = 2 if rows==11 else 1
            webp = io.BytesIO();im.save(webp,format='WEBP',lossless=True,exact=True,method=6)
            png = io.BytesIO();im.save(png,format='PNG')
            if Image.open(io.BytesIO(webp.getvalue())).convert('RGBA').tobytes() != im.tobytes():
                raise ValueError('WebP roundtrip changed pixels')
            pet = {'id':PET_ID,'displayName':'Liang no Henshin',
                   'description':f'Liang {"Wengu" if form=="gu" else "Wenfeng"} — v0.1.1 {form} artwork; single static form.',
                   'spriteVersionNumber':version,'spritesheetPath':'spritesheet.webp'}
            meta = (json.dumps(pet,ensure_ascii=False,indent=2)+'\n').encode()
            folder = output/profile/form/PET_ID
            folder.mkdir(parents=True)
            (folder/'pet.json').write_bytes(meta)
            (folder/'spritesheet.webp').write_bytes(webp.getvalue())
            # PNG is a separate lossless convenience export, not a second
            # runtime asset referenced by the package manifest.
            (folder.parent/'spritesheet.png').write_bytes(png.getvalue())
            name = f'LIANG_and_liang-v0.1.1-{profile}-{form}.zip'
            payload = archive({f'{PET_ID}/pet.json':meta,
                               f'{PET_ID}/spritesheet.webp':webp.getvalue()})
            (output/name).write_bytes(payload);all_files[name] = payload
            pixels = np.array(im)
            records.append({'profile':profile,'form':form,'spriteVersionNumber':version,
                            'size':list(im.size),'frames':sum(COUNTS[:rows]),'file':name,
                            'sha256':digest(payload),'spritesheetSha256':digest(webp.getvalue()),
                            'sourceSha256':freeze['forms'][form]['sha256'],
                            'activePixels':'byte-identical to v0.1.1','unusedCells':'RGBA zero',
                            'preservedPartialAlphaPixels':int(((pixels[:,:,3]>0)&(pixels[:,:,3]<255)).sum())})
    report = {'status':'FORMAT_AND_PIXEL_VALIDATED','runtimeImport':'NOT_TESTED',
              'petId':PET_ID,'profiles':PROFILES,'packages':records}
    report_bytes = (json.dumps(report,indent=2)+'\n').encode()
    (output/'validation.json').write_bytes(report_bytes)
    readme = (ROOT/'docs/pet-format-exports.md').read_bytes()
    (output/'README.md').write_bytes(readme)
    sums = ''.join(f'{digest(data)}  {name}\n' for name,data in sorted(all_files.items())).encode()
    (output/'SHA256SUMS.txt').write_bytes(sums)
    combined = archive({**all_files,'README.md':readme,'validation.json':report_bytes,'SHA256SUMS.txt':sums})
    (output/'LIANG_and_liang-v0.1.1-pet-formats.zip').write_bytes(combined)
    return report


if __name__ == '__main__':
    print(json.dumps(build(),indent=2))
