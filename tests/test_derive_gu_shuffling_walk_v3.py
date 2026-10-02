import hashlib

import pytest
from PIL import Image

from tools.derive_gu_shuffling_walk_v3 import (
    HEAD, SHOULDERS, IDLE, IDLE_PIXELS, LOCK_END, V2,
    apply_upper_action, build, row_shift,
)


def test_rigid_upper_preserves_idle_pixels_and_v2_legs():
    idle = Image.open(IDLE).convert('RGBA')
    assert hashlib.sha256(idle.tobytes()).hexdigest() == IDLE_PIXELS
    for i, (head, shoulder) in enumerate(zip(HEAD, SHOULDERS), 1):
        source = Image.open(V2/f'frame-{i:02d}.png').convert('RGBA')
        result, offsets = apply_upper_action(idle, source, shoulder, head)
        assert len(set(offsets)) == 1 and offsets[0] == shoulder
        assert result.crop((0, LOCK_END, 192, 208)).tobytes() == source.crop((0, LOCK_END, 192, 208)).tobytes()
        for y in range(LOCK_END):
            assert row_shift(y, shoulder, head) == shoulder
            for x in range(192):
                pixel = idle.getpixel((x, y))
                if pixel[3]:
                    assert result.getpixel((x+shoulder, y)) == pixel
        assert result.getchannel('A').getbbox()[1::2] == (4, 204)
    for i in range(8):
        prev = (i-1)%8
        assert abs(SHOULDERS[i]-SHOULDERS[prev]) <= 1


def test_review_artifacts_are_eight_frames_and_unapproved(tmp_path):
    out = tmp_path/'v3'
    report = build(out)
    assert not report['runtimeReady'] and not report['artApproved']
    assert report['frameCount'] == 8
    assert report['maxHeadX'] == 2
    for name in ('running-right-preview.gif', 'running-right-slow.gif', 'before-after-motion.gif'):
        with Image.open(out/'qa'/name) as gif:
            assert gif.n_frames == 8 and gif.info['loop'] == 0
    with pytest.raises(ValueError):
        build(out)
