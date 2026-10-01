import hashlib

import pytest
from PIL import Image

from tools.derive_gu_shuffle_keyposes import IDLE, IDLE_PIXELS, LOCK_END, POSES, build, derive, components


@pytest.mark.parametrize('pose', POSES)
def test_pixel_derivation_keeps_identity_and_contact(pose):
    idle = Image.open(IDLE).convert('RGBA')
    frame, rows, collisions = derive(idle, pose)
    assert hashlib.sha256(idle.tobytes()).hexdigest() == IDLE_PIXELS
    assert frame.crop((0, 0, 192, LOCK_END)).tobytes() == idle.crop((0, 0, 192, LOCK_END)).tobytes()
    assert frame.getchannel('A').getbbox()[1::2] == (4, 204)
    assert set(frame.getchannel('A').tobytes()) == {0, 255}
    assert set(frame.get_flattened_data()) <= set(idle.get_flattened_data())
    assert len(components(frame)) == 1
    assert not any((r or g or b) and a == 0 for r, g, b, a in frame.get_flattened_data())
    assert len(rows) == 86
    # Reconstruct every moved pixel from the recorded source-row provenance.
    reconstructed = Image.new('RGBA', idle.size)
    reconstructed.paste(idle.crop((0, 0, 192, LOCK_END)), (0, 0))
    for row in rows:
        span = range(97) if row['side'] == 'left' else range(97, 192)
        for x in span:
            pixel = idle.getpixel((x, row['sourceY']))
            if pixel[3]:
                reconstructed.putpixel((x+row['dx'], row['sourceY']+row['dy']), pixel)
    assert frame.tobytes() == reconstructed.tobytes()


def test_output_four_native_poses_and_review_gif(tmp_path):
    out = tmp_path / 'candidate'
    before = IDLE.read_bytes()
    report = build(out)
    assert IDLE.read_bytes() == before
    assert not report['artApproved'] and not report['runtimeReady']
    with Image.open(out / 'keyposes.png') as strip:
        assert strip.size == (768, 208) and strip.mode == 'RGBA'
    assert len({Image.open(out/f'pose-{i:02d}.png').tobytes() for i in range(1, 5)}) == 4
    for name, ms in [('idle-vs-keyposes.gif', 250), ('idle-vs-keyposes-slow.gif', 500)]:
        with Image.open(out / 'qa' / name) as gif:
            assert gif.n_frames == 4
            for i in range(4):
                gif.seek(i)
                assert gif.info['duration'] == ms
    with pytest.raises(ValueError):
        build(out)
