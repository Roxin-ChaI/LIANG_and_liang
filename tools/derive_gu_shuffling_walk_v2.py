"""Review-only Gu side-shuffle with frame-by-frame motion and Idle gates."""
import hashlib
import json

from PIL import Image, ImageDraw

from tools.derive_gu_shuffle_keyposes import IDLE, IDLE_PIXELS, LOCK_END, derive, components
from tools.complete_gu_shuffle_cycle import save_gif
from tools.preview_gu_side_shuffle import ROOT, SOURCE, SHA

OUT = ROOT / 'assets/rework/v0.1.0/gu-running-right-idle-pixel-v2'
# Each value is (horizontal shoe travel, vertical foot lift), in native pixels.
# Names refer to SCREEN sides. The approved older sheet provides the choreography
# of a clearly visible rightward shuffle, not source RGBA for the final art.
POSES = [
    {'name': 'right foot lifts',      'left': (0, 0), 'right': (2, 4)},
    {'name': 'right foot reaches',     'left': (0, 0), 'right': (6, 3)},
    {'name': 'right foot nearly down', 'left': (0, 0), 'right': (10, 1)},
    {'name': 'right foot plants',      'left': (0, 0), 'right': (12, 0)},
    {'name': 'left foot lifts',       'left': (3, 4), 'right': (12, 0)},
    {'name': 'left foot follows',     'left': (7, 3), 'right': (10, 0)},
    {'name': 'left foot plants',      'left': (7, 0), 'right': (7, 0)},
    {'name': 'feet return',           'left': (3, 0), 'right': (4, 2)},
]
DURATIONS = [120, 130] * 4


def footprint(frame, screen_side):
    """Bottom-half occupied x spans, for technical checks only."""
    xmin, xmax, ymin, ymax = 192, -1, 208, -1
    for y in range(185, 204):
        span = range(48, 98) if screen_side == 'left' else range(98, 145)
        for x in span:
            if frame.getpixel((x, y))[3]:
                xmin = min(xmin, x); xmax = max(xmax, x)
                ymin = min(ymin, y); ymax = max(ymax, y)
    return [xmin, ymin, xmax + 1, ymax + 1] if xmax >= xmin else None


def make_frame(idle, pose):
    frame, rowmap, overlaps = derive(idle, pose)
    assert frame.crop((0, 0, 192, LOCK_END)).tobytes() == idle.crop((0, 0, 192, LOCK_END)).tobytes()
    assert frame.getchannel('A').getbbox()[1::2] == (4, 204)
    assert set(frame.getchannel('A').tobytes()) == {0, 255}
    assert set(frame.get_flattened_data()) <= set(idle.get_flattened_data())
    assert len(components(frame)) == 1
    assert not any(a == 0 and (r or g or b) for r, g, b, a in frame.get_flattened_data())
    assert min(pose['left'][1], pose['right'][1]) == 0
    return frame, rowmap, overlaps


def check_motion_step(previous, current):
    deltas = {}
    for side in ('left', 'right'):
        before, after = previous[side], current[side]
        deltas[side] = [after[0] - before[0], after[1] - before[1]]
        assert abs(deltas[side][0]) <= 4
        assert abs(deltas[side][1]) <= 4
    return deltas


def build(out=OUT):
    if out.exists():
        raise ValueError('refuse to overwrite existing review version')
    idle = Image.open(IDLE).convert('RGBA')
    assert hashlib.sha256(idle.tobytes()).hexdigest() == IDLE_PIXELS
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == SHA
    out.mkdir(parents=True)
    qa = out/'qa'; qa.mkdir()
    strip = Image.new('RGBA', (1536, 208))
    frames, reports, panels = [], [], []
    for i, pose in enumerate(POSES):
        # Do not create the next frame until this frame passes all mechanical
        # gates; the human visual gate is a separate release decision.
        frame, rows, overlaps = make_frame(idle, pose)
        frame.save(out/f'frame-{i+1:02d}.png')
        strip.paste(frame, (192*i, 0))
        frames.append(frame)
        previous = POSES[i-1] if i else POSES[-1]
        deltas = check_motion_step(previous, pose)
        report = {'frame': i+1, 'pose': pose, 'fromPreviousOrWrap': deltas,
            'idleLockedUpperPixels': True, 'sourceOnlyColors': True,
            'alphaValues': [0, 255], 'baselineY': 203,
            'registrationX': 96, 'connectedComponents': 1,
            'screenLeftFootBbox': footprint(frame, 'left'),
            'screenRightFootBbox': footprint(frame, 'right'),
            'rowOverlaps': overlaps, 'rowMap': rows,
            'technicalGate': 'PASS', 'visualGate': 'PENDING_HUMAN_REVIEW'}
        reports.append(report)
        panel = Image.new('RGBA', (384, 448), (40, 42, 47, 255))
        panel.alpha_composite(frame.resize((384, 416), Image.Resampling.NEAREST), (0, 24))
        ImageDraw.Draw(panel).text((7, 6), f'{i+1:02d}/08 {pose["name"]}', fill='white')
        ImageDraw.Draw(panel).line((0, 440, 383, 440), fill=(70, 140, 90))
        panels.append(panel)
    strip.save(out/'running-right.png')
    save_gif(panels, qa/'running-right-preview.gif', DURATIONS)
    save_gif(panels, qa/'running-right-slow.gif', [250]*8)
    contact = Image.new('RGBA', (1536, 896))
    for i, panel in enumerate(panels):
        contact.paste(panel, ((i%4)*384, (i//4)*448))
    contact.save(qa/'contact-sheet.png')
    legs = Image.new('RGBA', (1152, 512), (40, 42, 47, 255))
    for i, frame in enumerate(frames):
        part = frame.crop((60, 148, 132, 208)).resize((288, 240), Image.Resampling.NEAREST)
        legs.alpha_composite(part, ((i%4)*288, (i//4)*256+16))
        ImageDraw.Draw(legs).text(((i%4)*288+8, (i//4)*256+2), f'{i+1:02d}/08', fill='white')
    legs.save(qa/'legs-contact-sheet.png')
    report = {'status': 'TECHNICAL_PASS_VISUAL_REVIEW_PENDING',
        'selection': 'User preferred earlier 4-pose source over low-motion v1',
        'motionReference': str(SOURCE.relative_to(ROOT)),
        'pixelSource': str(IDLE.relative_to(ROOT)),
        'note': 'Reconstructed native artwork based on original choreography; original source PNG frames not reused byte-for-byte',
        'nativeSize': [1536, 208], 'frameCount': 8,
        'lockedRegionRows': [0, LOCK_END-1], 'headFaceGlassesUpperBody': 'pixel-identical to canonical Idle',
        'frozenMaterialModified': False, 'artApproved': False, 'runtimeReady': False,
        'preview': {'frameDurationsMs': DURATIONS, 'loopMs': 1000,
            'slowFrameDurationMs': 250, 'loop': 'forever',
            'scale': 2, 'resampling': 'NEAREST', 'alignment': 'NONE',
            'background': 'opaque gray in GIF only; source PNG alpha remains 0/255'},
        'limitations': ['Integer row deformation may make knees or cuffs unnatural despite technical pass',
                        'Fixed upper body still needs gait review',
                        'This candidate has not been accepted by the user'],
        'frames': reports}
    (qa/'validation.json').write_text(json.dumps(report, indent=2)+'\n')
    return report


if __name__ == '__main__':
    print(build()['status'])
