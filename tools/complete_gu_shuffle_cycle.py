"""Eight-frame review candidate; preserve four approved keyposes exactly."""
import hashlib
import json

from PIL import Image, ImageDraw

from tools.derive_gu_shuffle_keyposes import (
    IDLE, IDLE_PIXELS, LOCK_END, OUT as KEYS, POSES, ROOT, components, derive,
)

OUT = ROOT / 'assets/rework/v0.1.0/gu-running-right-idle-pixel-v1'
CYCLE = [
    POSES[0],
    {'name': 'right foot advances and lowers', 'left': (0, 0), 'right': (3, 1)},
    POSES[1],
    {'name': 'left foot begins following', 'left': (1, 1), 'right': (5, 0)},
    POSES[2],
    {'name': 'left foot lowers / feet gather', 'left': (2, 1), 'right': (3, 0)},
    POSES[3],
    {'name': 'return to right foot lift', 'left': (0, 0), 'right': (1, 1)},
]
# GIF supports 10 ms increments. Each key-to-key pair retains 250 ms.
DURATIONS = [120, 130] * 4


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save_gif(panels, path, durations):
    palette_source = Image.new('RGB', (panels[0].width * len(panels), panels[0].height))
    for i, panel in enumerate(panels):
        palette_source.paste(panel.convert('RGB'), (i * panel.width, 0))
    palette = palette_source.quantize(colors=256, dither=Image.Dither.NONE)
    encoded = [p.convert('RGB').quantize(palette=palette, dither=Image.Dither.NONE) for p in panels]
    encoded[0].save(path, save_all=True, append_images=encoded[1:], duration=durations,
                    loop=0, disposal=2, optimize=False)


def build(out=OUT):
    if out.exists():
        raise ValueError('refuse to overwrite a review version')
    idle = Image.open(IDLE).convert('RGBA')
    assert hashlib.sha256(idle.tobytes()).hexdigest() == IDLE_PIXELS
    approval = json.loads((KEYS / 'human-approval.json').read_text())
    assert approval['fourKeyposesApproved']
    for name, expected in approval['approvedFileSha256'].items():
        assert sha(KEYS / name) == expected
    out.mkdir(parents=True)
    qa = out / 'qa'
    qa.mkdir()
    frames, records, panels, comparisons = [], [], [], []
    strip = Image.new('RGBA', (1536, 208))
    source_colors = set(idle.get_flattened_data())
    for i, pose in enumerate(CYCLE):
        frame, rows, overlaps = derive(idle, pose)
        key_number = i // 2 + 1 if i % 2 == 0 else None
        if key_number is not None:
            assert frame.tobytes() == Image.open(KEYS / f'pose-{key_number:02d}.png').convert('RGBA').tobytes()
        assert frame.crop((0, 0, 192, LOCK_END)).tobytes() == idle.crop((0, 0, 192, LOCK_END)).tobytes()
        assert set(frame.get_flattened_data()) <= source_colors
        assert set(frame.getchannel('A').tobytes()) == {0, 255}
        assert len(components(frame)) == 1
        box = frame.getchannel('A').getbbox()
        assert box[1] == 4 and box[3] == 204
        frames.append(frame)
        frame.save(out / f'frame-{i+1:02d}.png')
        strip.paste(frame, (i*192, 0))
        panel = Image.new('RGBA', (384, 456), (40, 42, 47, 255))
        panel.alpha_composite(frame.resize((384, 416), Image.Resampling.NEAREST), (0, 32))
        draw = ImageDraw.Draw(panel)
        draw.text((8, 6), f'{i+1:02d}/08 ' + (f'APPROVED KEY {key_number}' if key_number else 'NEW IN-BETWEEN'), fill='white')
        draw.line((0, 440, 383, 440), fill=(65, 130, 90))
        panels.append(panel)
        comparison = Image.new('RGBA', (768, 456), (40, 42, 47, 255))
        comparison.alpha_composite(idle.resize((384, 416), Image.Resampling.NEAREST), (0, 32))
        comparison.paste(panel, (384, 0))
        ImageDraw.Draw(comparison).text((8, 6), 'IDLE / reference, not an extra frame', fill='white')
        comparisons.append(comparison)
        records.append({'frame': i+1, 'approvedKey': key_number,
            'approvedKeyByteIdentical': True if key_number else None,
            'pose': pose, 'durationMs': DURATIONS[i], 'bbox': box, 'baseline': 203,
            'logicalRegistrationX': 96, 'upperBodyByteIdentical': True,
            'alphaValues': [0, 255], 'sourcePaletteOnly': True,
            'sourceRowOverlaps': overlaps, 'sourceRowMap': rows})
    strip.save(out / 'running-right.png')
    pairs = []
    for i, frame in enumerate(frames):
        following = frames[(i+1) % 8]
        diff = Image.new('RGBA', (192, 208))
        count = 0
        for y in range(208):
            for x in range(192):
                if frame.getpixel((x, y)) != following.getpixel((x, y)):
                    diff.putpixel((x, y), (255, 70, 120, 255))
                    count += 1
        assert diff.getbbox()[1] >= LOCK_END
        diff.save(qa / f'difference-{i+1:02d}-to-{(i+1)%8+1:02d}.png')
        pairs.append({'from': i+1, 'to': (i+1)%8+1, 'changedPixels': count,
                      'differenceBounds': diff.getbbox()})
    save_gif(panels, qa / 'running-right-preview.gif', DURATIONS)
    save_gif(panels, qa / 'running-right-slow.gif', [250]*8)
    save_gif(comparisons, qa / 'idle-vs-running-right.gif', DURATIONS)
    contact = Image.new('RGBA', (1536, 912))
    legs = Image.new('RGBA', (1152, 512), (40, 42, 47, 255))
    for i, (frame, panel) in enumerate(zip(frames, panels)):
        contact.paste(panel, ((i%4)*384, (i//4)*456))
        leg = frame.crop((60, 148, 132, 208)).resize((288, 240), Image.Resampling.NEAREST)
        legs.alpha_composite(leg, ((i%4)*288, (i//4)*256+16))
        ImageDraw.Draw(legs).text(((i%4)*288+8, (i//4)*256+2), f'{i+1:02d}/08', fill='white')
    contact.save(qa / 'contact-sheet.png')
    legs.save(qa / 'legs-contact-sheet.png')
    report = {'status': 'TECHNICAL_PASS_HUMAN_REVIEW_PENDING',
        'frameCount': 8, 'size': [1536, 208], 'mode': 'RGBA',
        'source': str(IDLE.relative_to(ROOT)), 'idleRgbaSha256': IDLE_PIXELS,
        'approvedKeyframeSlotsOneBased': [1, 3, 5, 7],
        'approvedKeysUnmodified': True, 'headAndUpperBodyLockedRows': [0, 160],
        'method': 'Canonical pixel copying with integer leg-row offsets. No ImageGen, scaling or color interpolation.',
        'preview': {'durationsMs': DURATIONS, 'cycleMs': sum(DURATIONS),
            'slowDurationsMs': [250]*8, 'loop': 'forever', 'order': list(range(1, 9)),
            'displayScale': 2, 'resampling': 'NEAREST', 'alignment': 'NONE',
            'gifOnly': 'gray background and shared 256-color palette; native PNG RGBA unchanged',
            'timingIsRuntimeChange': False},
        'artApproved': False, 'runtimeReady': False,
        'visualCaveats': ['Small in-place foot return may still look like sliding; review full loop',
            'Fixed upper body is intentional; no new torso weight shift',
            'Row overlaps shorten lifted shins; numerical checks do not prove visual fluidity'],
        'frames': records, 'adjacentPairsIncludingLoop': pairs}
    (qa / 'validation.json').write_text(json.dumps(report, indent=2)+'\n')
    return report


if __name__ == '__main__':
    print(build()['status'])
