"""Leftward shuffle uses the selected motion with canonical upper pixels."""
import hashlib
import json

from PIL import Image, ImageDraw

from tools.derive_gu_shuffling_walk_v2 import (
    IDLE, IDLE_PIXELS, LOCK_END, POSES as RIGHT_POSES, DURATIONS,
    OUT as RIGHT, make_frame, check_motion_step,
)
from tools.complete_gu_shuffle_cycle import save_gif
from tools.preview_gu_side_shuffle import ROOT

OUT = ROOT / 'assets/rework/v0.1.0/gu-running-left-idle-pixel-v2'
POSES = [
    {'name': p['name'].replace('right', 'TEMP').replace('left', 'right').replace('TEMP', 'left'),
     'left': (-p['right'][0], p['right'][1]),
     'right': (-p['left'][0], p['left'][1])}
    for p in RIGHT_POSES
]


def build(out=OUT):
    if out.exists():
        raise ValueError('refuse to overwrite review version')
    idle = Image.open(IDLE).convert('RGBA')
    assert hashlib.sha256(idle.tobytes()).hexdigest() == IDLE_PIXELS
    out.mkdir(parents=True)
    qa = out / 'qa'
    qa.mkdir()
    strip = Image.new('RGBA', (1536, 208))
    panels, pairs, records = [], [], []
    for i, pose in enumerate(POSES):
        frame, rows, overlaps = make_frame(idle, pose)
        right = Image.open(RIGHT / f'frame-{i+1:02d}.png').convert('RGBA')
        assert right.crop((0, 0, 192, LOCK_END)).tobytes() == frame.crop((0, 0, 192, LOCK_END)).tobytes()
        frame.save(out / f'frame-{i+1:02d}.png')
        strip.paste(frame, (i * 192, 0))
        panel = Image.new('RGBA', (384, 448), (40, 42, 47, 255))
        panel.alpha_composite(frame.resize((384, 416), Image.Resampling.NEAREST), (0, 24))
        ImageDraw.Draw(panel).text((8, 6), f'{i+1:02d}/08 {pose["name"]}', fill='white')
        panels.append(panel)
        pair = Image.new('RGBA', (768, 448), (40, 42, 47, 255))
        pair.paste(panel, (0, 0))
        pair.alpha_composite(right.resize((384, 416), Image.Resampling.NEAREST), (384, 24))
        ImageDraw.Draw(pair).text((392, 6), f'{i+1:02d}/08 rightward reference', fill='white')
        pairs.append(pair)
        records.append({'frame': i+1, 'pose': pose,
            'motionDelta': check_motion_step(POSES[i-1], pose),
            'bbox': frame.getchannel('A').getbbox(), 'baseline': 203,
            'upperBodyPixelIdentical': True, 'rowMap': rows, 'rowOverlaps': overlaps})
    strip.save(out / 'running-left.png')
    save_gif(panels, qa / 'running-left-preview.gif', DURATIONS)
    save_gif(panels, qa / 'running-left-slow.gif', [250] * 8)
    save_gif(pairs, qa / 'left-right-preview.gif', DURATIONS)
    contact = Image.new('RGBA', (1536, 896), (40, 42, 47, 255))
    for i, panel in enumerate(panels):
        contact.paste(panel, ((i % 4) * 384, (i // 4) * 448))
    contact.save(qa / 'contact-sheet.png')
    report = {'status': 'TECHNICAL_PASS_VISUAL_REVIEW_PENDING',
        'frameCount': 8, 'size': [1536, 208], 'cell': [192, 208],
        'sourceRgbaSha256': IDLE_PIXELS, 'registrationX': 96,
        'construction': 'swap screen-side foot motion and reverse horizontal offsets; copy canonical leg pixels',
        'wholeCharacterMirrored': False, 'wholeCharacterScaled': False,
        'upperBodyLockedRows': [0, LOCK_END-1], 'alpha': [0, 255],
        'newColors': 0, 'imagegenUsed': False, 'artApproved': False,
        'runtimeReady': False, 'frames': records,
        'preview': {'order': list(range(1, 9)), 'durationMs': DURATIONS,
            'cycleMs': 1000, 'loop': 'forever', 'displayScale': 2,
            'displayResampling': 'NEAREST', 'alignment': 'NONE',
            'backgroundAndPalette': 'GIF only; native PNG alpha and palette preserved'},
        'limitations': ['Local row movements need human knee/shoe silhouette review',
            'The paired GIF compares choreography; it is not live App QA']}
    (qa / 'validation.json').write_text(json.dumps(report, indent=2)+'\n')
    return report


if __name__ == '__main__':
    print(build()['status'])
