"""Review-only recovery of coherent directional upper-body pixels.

The previous palm patch still combined a directional cuff with the donor
forearm/lapel. Recover the entire original directional neck/shoulder/hand
unit, ending in a byte-identical band instead of through an anatomical joint.
No generated pixels, scaling, palette changes or runtime installation.
"""
from pathlib import Path
import hashlib
import json
import sys

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.repair_feng_look_hand_join import strip_cell
from tools.repair_gu_look_neck import cell, comparison, BG

PREVIOUS = ROOT / 'assets/rework/v0.1.0/feng-look-hand-join-2026-10-25/feng-look-16.png'
SOURCE = ROOT / 'assets/builds/feng/spritesheet.webp'
OUT = ROOT / 'assets/rework/v0.1.0/feng-look-upper-join-2026-10-25'
START, END = 45, 90


def derive(previous, source):
    frames = []
    for i in range(16):
        old = np.array(strip_cell(previous, i))
        src = np.array(cell(source, i))
        # Fail closed if the source changes: neither boundary may cut through
        # different artwork. The lower band spans cuff, sleeve and chest.
        if not np.array_equal(old[:START], src[:START]):
            raise ValueError(f'Head boundary changed at direction {i}')
        if not np.array_equal(old[END-4:], src[END-4:]):
            raise ValueError(f'No identical lower join band at direction {i}')
        result = old.copy()
        result[START:END] = src[START:END]
        frames.append(Image.fromarray(result))
    return frames


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build(output=OUT):
    if (OUT/'review-status.json').exists():
        raise RuntimeError('Upper-join candidate rejected; do not regenerate or use as repair base')
    output.mkdir(parents=True, exist_ok=True)
    previous = Image.open(PREVIOUS).convert('RGBA')
    source = Image.open(SOURCE).convert('RGBA')
    frames = derive(previous, source)
    strip = Image.new('RGBA', (3072, 208))
    full, details, records = [], [], []
    contact = Image.new('RGB', (4*384, 4*444), BG)
    draw = ImageDraw.Draw(contact)
    for i, frame in enumerate(frames):
        old = strip_cell(previous, i)
        p, q = np.array(frame), np.array(old)
        delta = np.any(p != q, axis=2)
        frame.save(output / f'look-{i*225:04d}.png')
        strip.paste(frame, (i*192, 0))
        Image.fromarray(delta.astype('uint8')*255).save(output / f'difference-{i:02d}.png')
        label = f'{i*22.5:05.1f} deg'
        full.append(comparison(old, frame, label=label))
        details.append(comparison(old, frame, (38, 38, 148, 112), 4, label))
        x, y = i % 4 * 384, i // 4 * 444
        draw.text((x+8, y+8), label, fill=(30,30,30))
        enlarged = frame.resize((384,416), Image.Resampling.NEAREST)
        contact.paste(enlarged, (x,y+28), enlarged.getchannel('A'))
        ys, xs = np.where(delta)
        records.append({'angle':i*22.5, 'changed_pixels':int(delta.sum()),
                        'changed_bbox': [int(xs.min()),int(ys.min()),int(xs.max()+1),int(ys.max()+1)] if len(xs) else None,
                        'lower_join_band_exact':bool(np.array_equal(p[86:94], q[86:94])),
                        'whole_direction_source_exact': frame.tobytes() == cell(source,i).tobytes(),
                        'baseline':frame.getbbox()[3]-1})
    strip.save(output/'feng-look-16.png')
    contact.save(output/'contact-light.png')
    for name, boards in [('look-light-preview',full), ('upper-body-light-preview',details)]:
        boards[0].save(output/f'{name}.gif', save_all=True, append_images=boards[1:],
                       duration=320, loop=0, disposal=2, optimize=False)
    for page in range(4):
        sheet = Image.new('RGB', (details[0].width, details[0].height*4), BG)
        for j in range(4): sheet.paste(details[page*4+j], (0,j*details[0].height))
        sheet.save(output/f'upper-body-comparison-{page+1}.png')
    report = {
        'status':'PENDING_USER_REVIEW', 'installed':False,
        'method':'restore intact same-direction upper body from existing atlas, without resampling',
        'important':'This reverses the defective head/body compositor in the review candidate; it is not newly drawn art. The resulting full cells are identical to the original directional source.',
        'cause':'skin-only head selection and subsequent rectangular palm patch cut through different directional hand/cuff/lapel artwork',
        'source_sha256':digest(SOURCE), 'previous_sha256':digest(PREVIOUS),
        'preserved':'head y<45 and all pixels y>=90; original direction order',
        'tradeoff':'Original small directional shoulder/collar motion is retained; body above y90 is no longer claimed pixel-fixed.',
        'not_claimed':'No user approval or runtime QA. Existing source-art imperfections are not certified absent.',
        'frames':records,
    }
    (output/'validation.json').write_text(json.dumps(report, indent=2)+'\n')
    return frames


if __name__ == '__main__':
    build()
