import pytest
from PIL import Image

from tools.audit_gu_shuffle_native_readiness import build, SOURCE, digest


def test_native_gate_does_not_turn_motion_approval_into_pixel_approval(tmp_path):
    before = digest(SOURCE)
    out = tmp_path / 'qa'
    report = build(out)
    assert digest(SOURCE) == before
    assert report['motionApproved'] and not report['runtimeReady']
    assert not report['productionFramesWritten']
    assert not report['sourceAlphaModified']
    assert report['sourceMetrics']['partialAlphaPixels'] == 453863
    assert report['canonicalMetrics']['partialAlphaPixels'] == 0
    assert all(f['reviewOnly']['partialAlphaPixels'] > 0 for f in report['frames'])
    for name, ms in [('idle-vs-keyposes.gif', 250), ('idle-vs-keyposes-slow.gif', 500)]:
        with Image.open(out / name) as gif:
            assert gif.n_frames == 4
            for i in range(4):
                gif.seek(i)
                assert gif.info['duration'] == ms
    with pytest.raises(ValueError):
        build(out)
