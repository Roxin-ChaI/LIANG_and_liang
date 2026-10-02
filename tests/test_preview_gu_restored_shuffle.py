import pytest
from PIL import Image

from tools.preview_gu_restored_shuffle import SOURCE, INSERTS, build, digest, DURATIONS


def test_restored_keys_preserved_and_failed_inbetween_not_approved(tmp_path):
    before = (digest(SOURCE), digest(INSERTS))
    out = tmp_path/'qa'
    r = build(out)
    assert (digest(SOURCE), digest(INSERTS)) == before
    assert r['originalFourKeysPreserved'] and not r['artApproved'] and not r['runtimeReady']
    assert r['status'] == 'VISUAL_QA_FAIL_STOPPED_FOR_HUMAN_REVIEW'
    assert r['frames'][3]['semanticGate'] == 'FAIL_WRONG_SUPPORT_FOOT'
    for i in range(8):
        source = Image.open(SOURCE if i%2 == 0 else INSERTS).convert('RGBA')
        expected = source.crop(((i//2)*543, 0, (i//2+1)*543, 724))
        assert Image.open(out/f'frame-{i+1:02d}-source-crop.png').tobytes() == expected.tobytes()
    for name, durations in [('eight-frame-trial.gif', DURATIONS), ('eight-frame-trial-slow.gif', [250]*8), ('eight-frame-raw-position.gif', DURATIONS)]:
        with Image.open(out/name) as gif:
            assert gif.n_frames == 8
            for i, duration in enumerate(durations):
                gif.seek(i)
                assert gif.info['duration'] == duration
    with pytest.raises(ValueError):
        build(out)
