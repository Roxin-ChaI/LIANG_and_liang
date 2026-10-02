import hashlib

import pytest
from PIL import Image

from tools.derive_gu_shuffling_walk_v2 import (
    DURATIONS, IDLE, IDLE_PIXELS, LOCK_END, POSES, SOURCE, SHA,
    build, check_motion_step, make_frame,
)


def test_support_foot_and_cycle_continuity():
    # Explicit semantics prevent the prior wrong-foot intermediate from passing.
    assert all(p['left'][1] == 0 for p in POSES[:4])
    assert all(p['right'][1] == 0 for p in POSES[4:7])
    assert POSES[7]['left'][1] == 0
    for i, pose in enumerate(POSES):
        check_motion_step(POSES[i-1], pose)
    assert POSES[0]['right'][1] > 0
    assert POSES[4]['left'][1] > 0
    assert POSES[3]['right'][0] > POSES[0]['right'][0]
    assert POSES[5]['left'][0] > POSES[4]['left'][0]


def test_each_frame_keeps_exact_idle_upper_body_and_native_alpha(tmp_path):
    idle = Image.open(IDLE).convert('RGBA')
    assert hashlib.sha256(idle.tobytes()).hexdigest() == IDLE_PIXELS
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == SHA
    for pose in POSES:
        frame, _, _ = make_frame(idle, pose)
        assert frame.crop((0, 0, 192, LOCK_END)).tobytes() == idle.crop((0, 0, 192, LOCK_END)).tobytes()
        assert frame.getchannel('A').getbbox()[1::2] == (4, 204)
    out = tmp_path / 'candidate'
    r = build(out)
    assert r['status'] == 'TECHNICAL_PASS_VISUAL_REVIEW_PENDING'
    assert not r['artApproved'] and not r['runtimeReady']
    with Image.open(out/'running-right.png') as strip:
        assert strip.size == (1536, 208) and strip.mode == 'RGBA'
        for i in range(8):
            frame = Image.open(out/f'frame-{i+1:02d}.png')
            assert strip.crop((i*192, 0, (i+1)*192, 208)).tobytes() == frame.tobytes()
    for filename, ms in [('running-right-preview.gif', DURATIONS), ('running-right-slow.gif', [250]*8)]:
        with Image.open(out/'qa'/filename) as gif:
            assert gif.n_frames == 8
            for i in range(8):
                gif.seek(i)
                assert gif.info['duration'] == ms[i]
    with pytest.raises(ValueError):
        build(out)
