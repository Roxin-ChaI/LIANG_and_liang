"""Add visible upper-body weight transfer to the reviewed v2 leg sequence."""
import hashlib
import json

from PIL import Image, ImageDraw

from tools.derive_gu_shuffling_walk_v2 import (
    DURATIONS, IDLE, IDLE_PIXELS, LOCK_END, OUT as V2, POSES, ROOT,
    check_motion_step,
)
from tools.derive_gu_shuffle_keyposes import components
from tools.complete_gu_shuffle_cycle import save_gif

OUT = ROOT / 'assets/rework/v0.1.0/gu-running-right-idle-pixel-v3'
# The entire upper silhouette moves as one rigid piece. This avoids stretching
# the face, arm and jacket pixels. It pivots against the stationary lower body.
SHOULDERS = [0, 1, 2, 2, 1, 0, -1, 0]
HEAD = SHOULDERS


def row_shift(y, shoulder, head):
    assert head == shoulder
    return shoulder


def apply_upper_action(idle, v2, shoulder, head):
    out = Image.new('RGBA', (192, 208))
    out.paste(v2.crop((0, LOCK_END, 192, 208)), (0, LOCK_END))
    rows = []
    for y in range(LOCK_END):
        dx = row_shift(y, shoulder, head)
        rows.append(dx)
        for x in range(192):
            pixel = idle.getpixel((x, y))
            if pixel[3]:
                nx = x + dx
                assert 0 <= nx < 192
                out.putpixel((nx, y), pixel)
    assert len(set(rows)) == 1
    assert out.crop((0, LOCK_END, 192, 208)).tobytes() == v2.crop((0, LOCK_END, 192, 208)).tobytes()
    assert out.getchannel('A').getbbox()[3] == 204
    assert set(out.getchannel('A').tobytes()) == {0, 255}
    assert not any(a == 0 and (r or g or b) for r, g, b, a in out.get_flattened_data())
    assert len(components(out)) == 1
    return out, rows


def build(out=OUT):
    if out.exists():
        raise ValueError('refuse to overwrite candidate')
    idle = Image.open(IDLE).convert('RGBA')
    assert hashlib.sha256(idle.tobytes()).hexdigest() == IDLE_PIXELS
    v2frames = [Image.open(V2/f'frame-{i:02d}.png').convert('RGBA') for i in range(1, 9)]
    out.mkdir(parents=True)
    qa = out/'qa'; qa.mkdir()
    strip = Image.new('RGBA', (1536, 208))
    panels, reports, frames = [], [], []
    idle_colors = set(idle.get_flattened_data())
    for i, (v2, pose, shoulder, head) in enumerate(zip(v2frames, POSES, SHOULDERS, HEAD)):
        frame, rows = apply_upper_action(idle, v2, shoulder, head)
        assert set(frame.get_flattened_data()) <= idle_colors
        assert frame.getchannel('A').getbbox()[1] == 4
        previous = (i - 1) % 8
        assert abs(shoulder - SHOULDERS[previous]) <= 2
        assert abs(head - HEAD[previous]) <= 1
        step = check_motion_step(POSES[previous], pose)
        frame.save(out/f'frame-{i+1:02d}.png')
        strip.paste(frame, (i*192, 0))
        frames.append(frame)
        panel = Image.new('RGBA', (384, 448), (40, 42, 47, 255))
        panel.alpha_composite(frame.resize((384, 416), Image.Resampling.NEAREST), (0, 24))
        ImageDraw.Draw(panel).text((7, 6), f'{i+1:02d}/08 shoulder {shoulder:+d} head {head:+d}', fill='white')
        ImageDraw.Draw(panel).line((0, 440, 383, 440), fill=(70, 140, 90))
        panels.append(panel)
        reports.append({'frame': i+1, 'screenFootMotion': pose,
            'footDeltaFromPreviousOrWrap': step, 'headX': head,
            'shoulderAndArmX': shoulder, 'shoulderDelta': shoulder-SHOULDERS[previous],
            'headDelta': head-HEAD[previous], 'upperRowOffsets': rows,
            'upperRgbSource': 'canonical Idle exact pixels, integer row translation',
            'lowerBodyByteIdenticalToV2': True, 'connectedComponents': 1,
            'baselineY': 203, 'alphaValues': [0,255],
            'perFrameCheck': 'TECHNICAL_PASS; visual review pending'})
    strip.save(out/'running-right.png')
    save_gif(panels, qa/'running-right-preview.gif', DURATIONS)
    save_gif(panels, qa/'running-right-slow.gif', [250]*8)
    sheet = Image.new('RGBA', (1536, 896))
    for i, p in enumerate(panels):
        sheet.paste(p, ((i%4)*384, (i//4)*448))
    sheet.save(qa/'contact-sheet.png')
    comparison = Image.new('RGBA', (1536, 896))
    comparison_panels = []
    for i, (v2, current) in enumerate(zip(v2frames, frames)):
        cell = Image.new('RGBA', (384, 448), (40, 42, 47, 255))
        cell.alpha_composite(v2.resize((192, 208), Image.Resampling.NEAREST), (0, 112))
        cell.alpha_composite(current.resize((192, 208), Image.Resampling.NEAREST), (192, 112))
        d = ImageDraw.Draw(cell)
        d.text((7, 8), f'{i+1:02d}: before / with upper motion', fill='white')
        comparison.paste(cell, ((i%4)*384, (i//4)*448))
        moving = Image.new('RGBA', (768, 448), (40, 42, 47, 255))
        moving.alpha_composite(v2.resize((384, 416), Image.Resampling.NEAREST), (0, 24))
        moving.alpha_composite(current.resize((384, 416), Image.Resampling.NEAREST), (384, 24))
        d = ImageDraw.Draw(moving)
        d.text((7, 6), f'{i+1:02d}/08 PREVIOUS LOWER-BODY ONLY', fill='white')
        d.text((391, 6), f'{i+1:02d}/08 WITH UPPER-BODY MOTION', fill='white')
        comparison_panels.append(moving)
    comparison.save(qa/'before-after-contact.png')
    save_gif(comparison_panels, qa/'before-after-motion.gif', DURATIONS)
    upper_details = Image.new('RGBA', (1280, 664), (40, 42, 47, 255))
    for i, frame in enumerate(frames):
        crop = frame.crop((50, 80, 130, 160)).resize((320, 320), Image.Resampling.NEAREST)
        upper_details.alpha_composite(crop, ((i%4)*320, (i//4)*332+12))
        ImageDraw.Draw(upper_details).text(((i%4)*320+8, (i//4)*332+2),
            f'{i+1:02d}/08 shoulder {SHOULDERS[i]:+d} head {HEAD[i]:+d}', fill='white')
    upper_details.save(qa/'upper-body-detail-contact.png')
    report = {'status': 'TECHNICAL_PASS_VISUAL_REVIEW_PENDING',
        'frameCount': 8, 'size': [1536, 208], 'alpha': [0,255],
        'source': str(IDLE.relative_to(ROOT)),
        'legPoseSource': str(V2.relative_to(ROOT)),
        'method': 'Canonical Idle upper pixels shifted by integer row offsets; exact v2 leg pixels retained',
        'headShapeAndFacePixels': 'rigid row translation only; no scaling/redraw',
        'wholeBodyTranslation': False, 'maxHeadX': 2,
        'shoulderXSequence': SHOULDERS, 'headXSequence': HEAD,
        'upperAction': 'head, shoulders, torso and arms translate rigidly by up to two pixels while feet follow the gait',
        'preview': {'durationsMs': DURATIONS, 'loopMs': 1000, 'slowDurationMs': 250,
            'loop': 'forever', 'scale': 2, 'resampling': 'NEAREST', 'alignment': 'NONE',
            'background': 'opaque gray in GIF only'},
        'runtimeReady': False, 'artApproved': False,
        'visualCaveat': 'Rigid upper/lower junction at waist may show a pose seam; inspect every frame and loop.',
        'frames': reports}
    (qa/'validation.json').write_text(json.dumps(report, indent=2)+'\n')
    return report


if __name__ == '__main__':
    print(build()['status'])
