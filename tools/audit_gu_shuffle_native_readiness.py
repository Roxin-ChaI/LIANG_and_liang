"""Read-only source gate plus disclosed same-scale review, not runtime art."""
import hashlib
import json
from collections import Counter
from pathlib import Path

from PIL import Image, ImageDraw

from tools.preview_gu_side_shuffle import BASE, ROOT, SHA, SOURCE, digest, write_gif

IDLE = ROOT / 'assets/rework/v0.1.0/idle-appearance-contract-2026-10-01/gu-idle-native.png'
IDLE_PIXELS = 'e12f8f315e36d704a910406d1a8b9a0a9ea7779b3b61b3a92443cdf7b3be72fb'
OUT = BASE / 'qa-native-readiness'
SCALE = 0.3


def inspect(frame):
    counts = Counter(frame.getchannel('A').tobytes())
    return {
        'size': list(frame.size),
        'alphaBounds': frame.getchannel('A').getbbox(),
        'alphaValueCount': len(counts),
        'partialAlphaPixels': sum(n for a, n in counts.items() if 0 < a < 255),
        'opaquePixels': counts[255],
        'hiddenRgbPixels': sum(a == 0 and (r, g, b) != (0, 0, 0)
                               for r, g, b, a in frame.get_flattened_data()),
    }


def build(out=OUT):
    if out.exists():
        raise ValueError('refuse to overwrite QA evidence')
    assert digest(SOURCE) == SHA
    source = Image.open(SOURCE).convert('RGBA')
    idle = Image.open(IDLE).convert('RGBA')
    assert hashlib.sha256(idle.tobytes()).hexdigest() == IDLE_PIXELS
    out.mkdir(parents=True)
    panels, records = [], []
    reference = Image.new('RGBA', (400, 240))
    reference.paste(idle, (104, 16))
    for i in range(4):
        frame = source.crop((i * 543, 0, (i + 1) * 543, 724))
        # This threshold measures alignment only, never changes source alpha.
        head_band = frame.getchannel('A').crop((0, 0, 543, 280)).point(
            lambda a: 255 if a >= 128 else 0).getbbox()
        center = (head_band[0] + head_band[2]) / 2
        dx = 192 - SCALE * center
        dy = 219 - SCALE * 688
        # All source pixels' extent remains in the review canvas, including haze.
        assert 0 <= dx and dx + 543 * SCALE <= 400
        assert 0 <= dy and dy + 724 * SCALE <= 240
        preview = frame.transform((400, 240), Image.Transform.AFFINE,
            (1 / SCALE, 0, -dx / SCALE, 0, 1 / SCALE, -dy / SCALE),
            resample=Image.Resampling.NEAREST)
        panel = Image.new('RGBA', (800, 240), (40, 42, 47, 255))
        panel.alpha_composite(reference)
        panel.alpha_composite(preview, (400, 0))
        draw = ImageDraw.Draw(panel)
        draw.text((8, 4), 'CANONICAL IDLE / unchanged', fill='white')
        draw.text((408, 4), f'POSE {i+1}/4 / QA scale 0.3 / NOT RUNTIME ART', fill='white')
        draw.line((0, 220, 799, 220), fill=(80, 140, 90))
        panels.append(panel)
        overlay = Image.new('RGBA', (400, 240), (40, 42, 47, 255))
        # Preview-only opacity to inspect silhouette; no altered art is exported.
        a = reference.copy()
        b = preview.copy()
        a.putalpha(a.getchannel('A').point(lambda v: v // 2))
        b.putalpha(b.getchannel('A').point(lambda v: v // 2))
        overlay.alpha_composite(a)
        overlay.alpha_composite(b)
        overlay.save(out / f'idle-pose-{i+1:02d}-overlay.png')
        records.append({'frame': i + 1, 'source': inspect(frame),
            'reviewTransform': {'scale': SCALE, 'offset': [dx, dy]},
            'reviewOnly': inspect(preview)})
    write_gif(panels, out / 'idle-vs-keyposes.gif', 250)
    write_gif(panels, out / 'idle-vs-keyposes-slow.gif', 500)
    contact = Image.new('RGBA', (800, 960))
    for i, panel in enumerate(panels):
        contact.paste(panel, (0, i * 240))
    contact.save(out / 'idle-vs-keyposes-contact.png')
    report = {
        'status': 'NATIVE_ART_GATE_FAIL_MOTION_APPROVAL_RETAINED',
        'sourceSha256': SHA, 'idleRgbaSha256': IDLE_PIXELS,
        'sourceUnchanged': digest(SOURCE) == SHA,
        'sourceMetrics': inspect(source), 'canonicalMetrics': inspect(idle),
        'frames': records, 'sourceAlphaModified': False,
        'productionFramesWritten': False, 'motionApproved': True,
        'runtimeReady': False, 'exactIdleAppearance': 'FAIL_VISUAL_REVIEW',
        'visualFindings': [
            'Generated face, glasses geometry and pixel texture differ from canonical Idle',
            'Common nearest-neighbor display scaling preserves source partial alpha',
            'Alignment and total-height similarity do not establish identity or anatomy compliance'
        ],
        'preview': {'frames': 4, 'order': [1, 2, 3, 4], 'durationMs': 250,
            'slowDurationMs': 500, 'loop': 'forever',
            'idle': 'reference panel only, not an additional animation frame',
            'alignment': 'head-band center to canonical x=88 plus panel offset; not anatomical measurement',
            'baseline': 'common source y=688 to canonical y=203 plus panel offset',
            'sourceRawPositionPreview': '../qa-motion/keyposes-4-frames-raw-position.gif',
            'background': 'dark gray, shared GIF palette without dithering; original PNG unchanged'},
        'nextDecision': 'Use approved motion as a guide for native Idle-pixel derivation; requires review before art edits'
    }
    (out / 'validation.json').write_text(json.dumps(report, indent=2) + '\n')
    return report


if __name__ == '__main__':
    print(build()['status'])
