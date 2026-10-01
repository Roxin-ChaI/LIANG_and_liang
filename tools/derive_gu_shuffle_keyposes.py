"""Four review-only poses using canonical pixels and integer leg-row offsets."""
import hashlib
import json
from collections import deque

from PIL import Image, ImageDraw

from tools.audit_gu_shuffle_native_readiness import IDLE, IDLE_PIXELS
from tools.preview_gu_side_shuffle import ROOT, write_gif

OUT = ROOT / 'assets/rework/v0.1.0/gu-drag-idle-pixel-keyposes-v1'
LOCK_END = 161  # Hair, face, torso, arms and hands remain byte-identical.
SPLIT = 97  # Transparent inter-leg gap at the first editable row.
# Anatomical left/right are intentionally not inferred: these are screen sides.
POSES = [
    {'name': 'right foot lift / left support', 'left': (0, 0), 'right': (1, 2)},
    {'name': 'right foot opens / left support', 'left': (0, 0), 'right': (5, 0)},
    {'name': 'left foot follows / right support', 'left': (3, 2), 'right': (5, 0)},
    {'name': 'feet gather / settle', 'left': (1, 0), 'right': (2, 0)},
]


def components(im):
    remaining = {(x, y) for y in range(im.height) for x in range(im.width)
                 if im.getpixel((x, y))[3]}
    sizes = []
    while remaining:
        seed = remaining.pop()
        queue = deque([seed])
        n = 0
        while queue:
            x, y = queue.popleft()
            n += 1
            for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1),
                           (-1, -1), (1, -1), (-1, 1), (1, 1)):
                point = (x + dx, y + dy)
                if point in remaining:
                    remaining.remove(point)
                    queue.append(point)
        sizes.append(n)
    return sorted(sizes, reverse=True)


def derive(idle, pose):
    frame = Image.new('RGBA', idle.size)
    frame.paste(idle.crop((0, 0, 192, LOCK_END)), (0, 0))
    records, provenance = [], {}
    collisions = 0
    for side, x0, x1 in [('left', 0, SPLIT), ('right', SPLIT, 192)]:
        shift, lift = pose[side]
        for y in range(LOCK_END, 204):
            # Integer row relocation, never color interpolation or sprite scaling.
            dx = (shift * min(y - LOCK_END, 29) + 14) // 29
            dy = -(lift * max(0, min(y - 176, 16)) // 16)
            records.append({'side': side, 'sourceY': y, 'dx': dx, 'dy': dy})
            for x in range(x0, x1):
                pixel = idle.getpixel((x, y))
                if not pixel[3]:
                    continue
                dest = (x + dx, y + dy)
                assert 0 <= dest[0] < 192 and LOCK_END <= dest[1] < 208
                # Shortening the bent shin overlaps at most two rows. Lower
                # source row wins; every retained pixel has an exact origin.
                collisions += dest in provenance
                provenance[dest] = (x, y)
                frame.putpixel(dest, pixel)
    assert frame.crop((0, 0, 192, LOCK_END)).tobytes() == idle.crop((0, 0, 192, LOCK_END)).tobytes()
    for dest, src in provenance.items():
        assert frame.getpixel(dest) == idle.getpixel(src)
    return frame, records, collisions


def build(out=OUT):
    if out.exists():
        raise ValueError('refuse to overwrite a review candidate')
    idle = Image.open(IDLE).convert('RGBA')
    assert hashlib.sha256(idle.tobytes()).hexdigest() == IDLE_PIXELS
    out.mkdir(parents=True)
    qa = out / 'qa'
    qa.mkdir()
    strip = Image.new('RGBA', (768, 208))
    lock = Image.new('L', (192, 208))
    ImageDraw.Draw(lock).rectangle((0, 0, 191, LOCK_END - 1), fill=255)
    lock.save(qa / 'locked-region-mask.png')
    panels, frames, reports = [], [], []
    idle_colors = set(idle.get_flattened_data())
    source_connected = components(idle)
    for i, pose in enumerate(POSES):
        frame, rows, collisions = derive(idle, pose)
        frames.append(frame)
        frame.save(out / f'pose-{i+1:02d}.png')
        strip.paste(frame, (192 * i, 0))
        diff = Image.new('RGBA', idle.size)
        changed = []
        for y in range(208):
            for x in range(192):
                if idle.getpixel((x, y)) != frame.getpixel((x, y)):
                    diff.putpixel((x, y), (255, 70, 120, 255))
                    changed.append((x, y))
        diff.save(qa / f'difference-{i+1:02d}.png')
        overlay = Image.new('RGBA', idle.size)
        for im in (idle, frame):
            layer = im.copy()
            layer.putalpha(layer.getchannel('A').point(lambda a: a // 2))
            overlay.alpha_composite(layer)
        overlay.save(qa / f'overlay-{i+1:02d}.png')
        panel = Image.new('RGBA', (768, 456), (40, 42, 47, 255))
        panel.alpha_composite(idle.resize((384, 416), Image.Resampling.NEAREST), (0, 32))
        panel.alpha_composite(frame.resize((384, 416), Image.Resampling.NEAREST), (384, 32))
        draw = ImageDraw.Draw(panel)
        draw.text((8, 8), 'CANONICAL IDLE (reference only)', fill='white')
        draw.text((392, 8), f'{i+1}/4 {pose["name"]}', fill='white')
        draw.line((0, 440, 767, 440), fill=(65, 130, 90))
        panels.append(panel)
        box = frame.getchannel('A').getbbox()
        sizes = components(frame)
        assert box[1] == 4 and box[3] == 204
        assert set(frame.getchannel('A').tobytes()) == {0, 255}
        assert set(frame.get_flattened_data()) <= idle_colors
        assert len(sizes) == len(source_connected) == 1
        assert min(y for _, y in changed) >= LOCK_END
        reports.append({'frame': i+1, 'pose': pose, 'alphaBbox': box,
            'baseline': box[3]-1, 'logicalRegistrationX': 96,
            'registrationMethod': 'unchanged canonical upper body; no recentering',
            'lockedRegionByteIdentical': True, 'lockedRegion': [0, 0, 192, LOCK_END],
            'lockedRgbaSha256': hashlib.sha256(frame.crop((0, 0, 192, LOCK_END)).tobytes()).hexdigest(),
            'differenceBbox': diff.getbbox(), 'changedPixels': len(changed),
            'partialAlphaPixels': 0, 'hiddenRgbPixels': 0,
            'newColors': 0, 'connectedComponents8': sizes,
            'sourcePixelOverlaps': collisions, 'sourceRowMap': rows,
            'sourcePixelRule': 'same RGBA at (x-dx,y-dy); lower row wins recorded overlaps'})
    strip.save(out / 'keyposes.png')
    write_gif(panels, qa / 'idle-vs-keyposes.gif', 250)
    write_gif(panels, qa / 'idle-vs-keyposes-slow.gif', 500)
    contact = Image.new('RGBA', (768, 1824))
    for i, panel in enumerate(panels):
        contact.paste(panel, (0, i*456))
    contact.save(qa / 'contact-sheet.png')
    legs = Image.new('RGBA', (1440, 256), (40, 42, 47, 255))
    for i, frame in enumerate([idle] + frames):
        legs.alpha_composite(frame.crop((60, 148, 132, 208)).resize((288, 240), Image.Resampling.NEAREST), (i*288, 16))
        ImageDraw.Draw(legs).text((i*288+8, 2), 'IDLE' if i == 0 else f'POSE {i}', fill='white')
    legs.save(qa / 'legs-contact-sheet.png')
    report = {'status': 'TECHNICAL_PASS_VISUAL_REVIEW_PENDING',
        'method': 'deterministic local canonical-pixel derivation; no ImageGen',
        'source': str(IDLE.relative_to(ROOT)), 'sourceRgbaSha256': IDLE_PIXELS,
        'nativeCanvas': [192, 208], 'stripSize': [768, 208], 'frameCount': 4,
        'lockedRegion': [0, 0, 192, LOCK_END], 'sourcePalettePreserved': True,
        'frameResampling': 'NONE; integer leg-row moves only',
        'preview': {'durationMs': 250, 'slowDurationMs': 500, 'loop': 'forever',
            'order': [1, 2, 3, 4], 'displayScale': 2, 'resampling': 'NEAREST',
            'alignment': 'NONE', 'background': 'opaque gray; GIF palette quantization only',
            'timing': 'keypose review, not final eight-frame animation timing'},
        'artApproved': False, 'runtimeReady': False,
        'limitations': ['Local shin shortening overlaps source rows; examine knees/cuffs visually',
            'First pose is whole-foot lift, not articulated heel rotation',
            'Fixed torso and four sparse poses need human gait and loop review',
            'Connectivity and exact head pixels do not prove anatomical quality'],
        'frames': reports}
    (qa / 'validation.json').write_text(json.dumps(report, indent=2) + '\n')
    return report


if __name__ == '__main__':
    print(build()['status'])
