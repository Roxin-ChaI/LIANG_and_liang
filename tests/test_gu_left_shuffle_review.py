from PIL import Image
import pytest

from tools.derive_gu_left_shuffle_review import build, POSES, RIGHT_POSES, LOCK_END, IDLE


def test_left_cycle_reverses_motion_without_mirroring_head(tmp_path):
    for left, right in zip(POSES, RIGHT_POSES):
        assert left['left'] == (-right['right'][0], right['right'][1])
        assert left['right'] == (-right['left'][0], right['left'][1])
    out = tmp_path / 'candidate'
    report = build(out)
    idle = Image.open(IDLE).convert('RGBA')
    strip = Image.open(out / 'running-left.png')
    assert strip.size == (1536, 208) and strip.mode == 'RGBA'
    for i in range(8):
        frame = Image.open(out / f'frame-{i+1:02d}.png')
        assert frame.crop((0, 0, 192, LOCK_END)).tobytes() == idle.crop((0, 0, 192, LOCK_END)).tobytes()
        assert strip.crop((i*192, 0, (i+1)*192, 208)).tobytes() == frame.tobytes()
        assert frame.getchannel('A').getbbox()[3] == 204
    assert not report['artApproved'] and not report['runtimeReady']
    with Image.open(out / 'qa/left-right-preview.gif') as gif:
        assert gif.n_frames == 8
    with pytest.raises(ValueError):
        build(out)
