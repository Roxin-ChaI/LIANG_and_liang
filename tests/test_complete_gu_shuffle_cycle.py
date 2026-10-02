import pytest
from PIL import Image

from tools.complete_gu_shuffle_cycle import CYCLE, DURATIONS, IDLE, KEYS, LOCK_END, build, derive


def test_adjacent_leg_offsets_including_wrap_are_small():
    for i, pose in enumerate(CYCLE):
        nxt = CYCLE[(i+1) % 8]
        for side in ('left', 'right'):
            assert abs(pose[side][0] - nxt[side][0]) <= 2
            assert abs(pose[side][1] - nxt[side][1]) <= 1
        assert min(pose['left'][1], pose['right'][1]) == 0


def test_cycle_preserves_approved_keys_and_does_not_gain_approval(tmp_path):
    out = tmp_path / 'cycle'
    originals = [(KEYS/f'pose-{i:02d}.png').read_bytes() for i in range(1, 5)]
    r = build(out)
    assert r['approvedKeysUnmodified']
    assert not r['artApproved'] and not r['runtimeReady']
    assert originals == [(KEYS/f'pose-{i:02d}.png').read_bytes() for i in range(1, 5)]
    idle = Image.open(IDLE).convert('RGBA')
    strip = Image.open(out/'running-right.png')
    assert strip.size == (1536, 208) and strip.mode == 'RGBA'
    frames = [Image.open(out/f'frame-{i:02d}.png').convert('RGBA') for i in range(1, 9)]
    assert len({f.tobytes() for f in frames}) == 8
    for i, frame in enumerate(frames):
        assert strip.crop((i*192, 0, (i+1)*192, 208)).tobytes() == frame.tobytes()
        assert frame.crop((0, 0, 192, LOCK_END)).tobytes() == idle.crop((0, 0, 192, LOCK_END)).tobytes()
        if i % 2 == 0:
            assert frame.tobytes() == Image.open(KEYS/f'pose-{i//2+1:02d}.png').convert('RGBA').tobytes()
    for name, durations in [('running-right-preview.gif', DURATIONS), ('running-right-slow.gif', [250]*8), ('idle-vs-running-right.gif', DURATIONS)]:
        with Image.open(out/'qa'/name) as gif:
            assert gif.n_frames == 8 and gif.info['loop'] == 0
            for i, ms in enumerate(durations):
                gif.seek(i)
                assert gif.info['duration'] == ms
    assert r['adjacentPairsIncludingLoop'][-1]['to'] == 1
    with pytest.raises(ValueError):
        build(out)
