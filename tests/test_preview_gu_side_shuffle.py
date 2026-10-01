from PIL import Image
from tools.preview_gu_side_shuffle import build,SOURCE,digest

def test_gif_preserves_four_frames_and_source(tmp_path):
    before=digest(SOURCE);out=tmp_path/'qa';r=build(out)
    assert r['frameCount']==4 and r['order']==[1,2,3,4]
    assert r['sourceUnchanged'] and digest(SOURCE)==before
    assert not r['artApproved'] and not r['runtimeReady']
    src=Image.open(SOURCE).convert('RGBA')
    for i in range(4):
        im=Image.open(out/f'source-cell-{i+1:02d}.png')
        assert im.tobytes()==src.crop((i*543,0,(i+1)*543,724)).tobytes()
    for name,ms in [('keyposes-4-frames.gif',250),('keyposes-4-frames-slow.gif',500),('keyposes-4-frames-raw-position.gif',250)]:
        with Image.open(out/name) as gif:
            assert gif.n_frames==4 and gif.info['loop']==0
            for i in range(4):gif.seek(i);assert gif.info['duration']==ms
