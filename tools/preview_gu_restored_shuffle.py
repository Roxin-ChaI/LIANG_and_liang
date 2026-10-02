"""Evidence-only eight-frame assembly; retain source keys, expose failed art gate."""
import hashlib
import json

from PIL import Image, ImageDraw

from tools.preview_gu_side_shuffle import ROOT, SOURCE, SHA
from tools.complete_gu_shuffle_cycle import save_gif, DURATIONS

BASE = ROOT / 'assets/rework/v0.1.0/gu-shuffle-restored-eight-v1'
INSERTS = BASE / 'inbetweens-attempt-01.png'


def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def build(out=BASE/'qa'):
    if out.exists():
        raise ValueError('refuse to overwrite evidence')
    assert digest(SOURCE) == SHA
    original = Image.open(SOURCE).convert('RGBA')
    inserts = Image.open(INSERTS).convert('RGBA')
    assert original.size == inserts.size == (2172, 724)
    out.mkdir(parents=True)
    panels, raw, records = [], [], []
    for i in range(8):
        src = original if i % 2 == 0 else inserts
        k = i//2
        frame = src.crop((k*543, 0, (k+1)*543, 724))
        frame.save(out/f'frame-{i+1:02d}-source-crop.png')
        box = frame.getchannel('A').crop((0, 0, 543, 280)).point(lambda a: 255 if a >= 128 else 0).getbbox()
        dx = round(432-(box[0]+box[2])/2)
        dy = 32
        assert 0 <= dx and dx+543 <= 864
        panel = Image.new('RGBA', (864, 784), (40, 42, 47, 255))
        panel.alpha_composite(frame, (dx, dy))
        panel = panel.resize((432, 392), Image.Resampling.NEAREST)
        label = 'ORIGINAL' if i%2 == 0 else 'NEW / UNAPPROVED'
        ImageDraw.Draw(panel).text((8, 8), f'{i+1:02d}/08 {label}', fill='white')
        if i == 3:
            ImageDraw.Draw(panel).text((8, 375), 'FAIL: WRONG SUPPORT FOOT', fill=(255, 120, 100))
        panels.append(panel)
        raw_panel = Image.new('RGBA', (544, 752), (40, 42, 47, 255))
        raw_panel.alpha_composite(frame, (0, 28))
        raw_panel = raw_panel.resize((272, 376), Image.Resampling.NEAREST)
        ImageDraw.Draw(raw_panel).text((4, 4), f'{i+1:02d}/08 RAW POSITION', fill='white')
        raw.append(raw_panel)
        records.append({'frame': i+1, 'source': str((SOURCE if i%2 == 0 else INSERTS).relative_to(ROOT)),
            'sourcePanel': k+1, 'originalKey': i%2 == 0,
            'sourceCropRgbaSha256': hashlib.sha256(frame.tobytes()).hexdigest(),
            'previewOffset': [dx, dy], 'headBandMeasurement': box,
            'partialAlphaPixels': sum(0<a<255 for a in frame.getchannel('A').tobytes()),
            'semanticGate': 'FAIL_WRONG_SUPPORT_FOOT' if i == 3 else 'NOT_APPROVED'})
    save_gif(panels, out/'eight-frame-trial.gif', DURATIONS)
    save_gif(panels, out/'eight-frame-trial-slow.gif', [250]*8)
    save_gif(raw, out/'eight-frame-raw-position.gif', DURATIONS)
    sheet = Image.new('RGBA', (1728, 784))
    for i, p in enumerate(panels):
        sheet.paste(p, ((i%4)*432, (i//4)*392))
    sheet.save(out/'contact-sheet.png')
    report = {'status': 'VISUAL_QA_FAIL_STOPPED_FOR_HUMAN_REVIEW',
        'selectedBaseline': str(SOURCE.relative_to(ROOT)), 'selectedBaselineSha256': SHA,
        'originalFourKeysPreserved': True, 'originalKeySlots': [1,3,5,7],
        'insertAttemptSha256': digest(INSERTS), 'generationCalls': 2,
        'correctionResult': 'FAIL: attempt 2 still lifts screen-right instead of screen-left foot; not used',
        'displayedAttempt': 1, 'whyDisplay': 'Show actual failed eight-frame evidence, not a passing final animation',
        'issues': ['Frame 4 support-foot logic contradicts surrounding keys',
                   'Generated upper-body pixels not guaranteed identical; identity and temporal stability unapproved',
                   'Source has partial alpha and is not a native runtime strip'],
        'frameCount': 8, 'frames': records,
        'preview': {'durationsMs': DURATIONS, 'cycleMs': 1000, 'loop': 'forever',
            'slowDurationsMs': [250]*8, 'scale': 0.5, 'resampling': 'NEAREST',
            'alignment': 'integer head-band horizontal centering, constant y offset; preview only',
            'rawPreviewIncluded': True, 'sourceAlphaUnchanged': True,
            'gifOnly': 'dark opaque background and palette conversion'},
        'artApproved': False, 'runtimeReady': False, 'appModified': False}
    (out/'validation.json').write_text(json.dumps(report, indent=2)+'\n')
    return report


if __name__ == '__main__':
    print(build()['status'])
