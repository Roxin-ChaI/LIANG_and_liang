"""Review-only Gu eye repair: integer copies of canonical Idle eye pixels."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'assets/rework/v0.1.0/gu/spritesheet.webp'
SOURCE_SHA = 'b5b6b6b4fd437164282c5ba4c3b1de8f4b74e0184148eba344118e5e0fa97968'
OUT = ROOT / 'assets/rework/v0.1.0/gu-eye-repair-2026-10-01'
ROWS = {'failed': (5, 8), 'waiting': (6, 6)}
# Coordinates are native 192x208 cell coordinates. Left means viewer-left.
# Each 10x5 patch includes the eye interior and its bottom eyelid termination;
# glasses rims, bridge, eyebrows and facial silhouette are outside these masks.
DONORS = {'left': (70, 53, 80, 58), 'right': (92, 53, 102, 58)}
EDITS = {
    ('failed', 1): [('left', (71, 59))],
    ('failed', 7): [('left', (71, 59)), ('right', (94, 59))],
    ('waiting', 1): [('left', (75, 58)), ('right', (95, 59))],
    ('waiting', 2): [('left', (76, 59)), ('right', (97, 60))],
    ('waiting', 4): [('left', (77, 59)), ('right', (97, 60))],
    ('waiting', 5): [('left', (78, 59)), ('right', (99, 59))],
}


def cell(atlas, row, index):
    return atlas.crop((index * 192, row * 208, (index + 1) * 192, (row + 1) * 208))


def repair(frame, idle, edits):
    if frame.mode != 'RGBA' or idle.mode != 'RGBA' or frame.size != (192, 208) or idle.size != (192, 208):
        raise ValueError('native RGBA cells required')
    result = frame.copy()
    allowed = Image.new('L', frame.size)
    for eye, (x, y) in edits:
        patch = idle.crop(DONORS[eye])
        if not (0 <= x <= 192 - patch.width and 0 <= y <= 208 - patch.height):
            raise ValueError('patch out of bounds')
        # Waiting already has alpha 253/254 inside the face. Preserve it exactly;
        # fixing pre-existing alpha is outside this eye-only repair scope.
        patch.putalpha(frame.getchannel('A').crop((x, y, x+patch.width, y+patch.height)))
        result.paste(patch, (x, y))
        allowed.paste(255, (x, y, x + patch.width, y + patch.height))
    changed = [i for i, (a, b) in enumerate(zip(frame.get_flattened_data(), result.get_flattened_data())) if a != b]
    if not changed or any(not allowed.getpixel((i % 192, i // 192)) for i in changed):
        raise ValueError('unexpected edit extent')
    if frame.getchannel('A').tobytes() != result.getchannel('A').tobytes():
        raise ValueError('alpha changed')
    diff = Image.new('RGBA', frame.size)
    for i in changed:
        diff.putpixel((i % 192, i // 192), (255, 64, 128, 255))
    return result, diff, allowed, changed


def build(output=OUT):
    if output.exists():
        raise ValueError('refuse to overwrite review candidate')
    source_hash = hashlib.sha256(SOURCE.read_bytes()).hexdigest()
    if source_hash != SOURCE_SHA:
        raise ValueError('baseline-corrected source changed')
    atlas = Image.open(SOURCE).convert('RGBA')
    idle = cell(atlas, 0, 0)
    output.mkdir(parents=True)
    qa = output / 'qa'; qa.mkdir()
    report = {'status': 'CANDIDATE_REQUIRES_USER_VISUAL_REVIEW', 'source': str(SOURCE.relative_to(ROOT)),
              'sourceSha256': source_hash, 'method': 'canonical Idle 10x5 eye-region pixel copies; integer translation only',
              'leftConvention': 'viewer-left; failed 02 viewer-right remains byte-identical',
              'runtimeOrFormalAtlasModified': False, 'visualApproved': False, 'frames': []}
    sheet = Image.new('RGBA', (3 * 432, len(EDITS) * 440), (36, 38, 43, 255))
    draw = ImageDraw.Draw(sheet)
    n = 0
    for state, (row, count) in ROWS.items():
        strip = Image.new('RGBA', (count * 192, 208))
        for index in range(count):
            before = cell(atlas, row, index)
            after = before.copy()
            if (state, index) in EDITS:
                edits = EDITS[state, index]
                after, diff, mask, changed = repair(before, idle, edits)
                name = f'{state}-{index+1:02d}'
                after.save(output / f'{name}.png')
                diff.save(qa / f'{name}-difference.png')
                mask.save(qa / f'{name}-allowed-mask.png')
                for col, (label, img) in enumerate([('BEFORE', before), ('CANDIDATE', after), ('DIFFERENCE', diff)]):
                    sheet.alpha_composite(img.crop((52, 25, 124, 93)).resize((432, 408), Image.Resampling.NEAREST), (col*432, n*440+30))
                    draw.text((col*432+5, n*440+7), f'{name} / {label}', fill='white')
                report['frames'].append({'state': state, 'frameNumber': index+1, 'index': index,
                    'edits': [{'eye': eye, 'donorRect': DONORS[eye], 'destination': xy} for eye, xy in edits],
                    'changedPixels': len(changed), 'outsideMaskIdentical': True, 'alphaIdentical': True,
                    'baselineBefore': before.getchannel('A').getbbox()[3]-1, 'baselineAfter': after.getchannel('A').getbbox()[3]-1,
                    'changedCoordinates': [[i%192, i//192] for i in changed]})
                n += 1
            strip.paste(after, (index*192, 0))
        strip.save(output / f'{state}.png')
    sheet.save(qa / 'before-after-difference.png')
    sheet.crop((0, 0, 1296, 880)).save(qa / 'failed-before-after.png')
    sheet.crop((0, 880, 1296, 2640)).save(qa / 'waiting-before-after.png')
    for state, (row, count) in ROWS.items():
        repaired_strip = Image.open(output / f'{state}.png').convert('RGBA')
        preview = []
        for index in range(count):
            canvas = Image.new('RGBA', (384, 234), (36, 38, 43, 255))
            canvas.alpha_composite(cell(atlas, row, index), (0, 26))
            canvas.alpha_composite(cell(repaired_strip, 0, index), (192, 26))
            label = ImageDraw.Draw(canvas)
            label.text((4, 4), f'BEFORE {index+1:02d}', fill='white')
            label.text((196, 4), f'CANDIDATE {index+1:02d}', fill='white')
            preview.append(canvas.convert('RGB'))
        durations = ([140]*(count-1)+[240]) if state == 'failed' else ([150]*(count-1)+[260])
        preview[0].save(qa / f'{state}-before-after.gif', save_all=True, append_images=preview[1:], duration=durations, loop=0, disposal=2)
    report['existingIssuesOutsideScope'] = ['Waiting face contains existing alpha 253/254, preserved byte-for-byte.',
        'Canonical-eye reuse regularizes gaze; waiting side-glance intent must be assessed in human review.',
        'GIF is a background-composited, palette-limited review preview, not replacement source art.']
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == source_hash
    (qa / 'validation.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps({'status':report['status'], 'frames':len(report['frames']), 'changedPixels':[f['changedPixels'] for f in report['frames']]}, ensure_ascii=False))
    return report


if __name__ == '__main__':
    build()
