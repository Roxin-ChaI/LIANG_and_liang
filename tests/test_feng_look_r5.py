import hashlib
from collections import deque

import numpy as np
from PIL import Image

from tools.repair_feng_look_r5 import OUT, SOURCE, frame, masks, semantic_head_bbox


def test_complete_idle_body_and_foreground_hand_are_immutable():
    idle=frame(Image.open(SOURCE).convert("RGBA"),0,0)
    p=np.array(idle)
    _,foreground=masks(idle)
    for i in range(16):
        im=Image.open(OUT/f"{i+1:02d}.png")
        q=np.array(im)
        assert im.size==(192,208) and im.mode=="RGBA"
        assert im.getchannel("A").getbbox()==idle.getchannel("A").getbbox()==(44,4,148,204)
        assert np.array_equal(p[61:],q[61:])
        assert np.array_equal(p[foreground],q[foreground])
        # All suit/shirt pixels beneath the chin, including the high collar,
        # must retain the Idle value: this catches R3's cross-pose color seams.
        rgb=p[:,:,:3].astype(int)
        clothing=(rgb[:,:,2]>rgb[:,:,0]+12) | ((rgb.min(2)>180)&(rgb.max(2)-rgb.min(2)<65))
        clothing[:52]=False
        assert np.array_equal(p[clothing],q[clothing])
        box=semantic_head_bbox(idle,im)
        assert (box[2]-box[0],box[3]-box[1])==(49,57)
        assert abs((box[0]+box[2])/2-88.5)<=1


def test_actual_head_motion_not_eyes_only_and_original_palette():
    idle=frame(Image.open(SOURCE).convert("RGBA"),0,0)
    p=np.array(idle)
    palette=set(map(tuple,p.reshape(-1,4)))
    frames=[np.array(Image.open(OUT/f"{i+1:02d}.png")) for i in range(16)]
    assert len({q.tobytes() for q in frames})==16
    for q in frames:
        assert set(map(tuple,q.reshape(-1,4))) <= palette | {(0,0,0,0)}
        delta=np.any(p!=q,axis=2)
        delta[33:45,67:115]=False
        assert delta.sum()>200
        assert set(np.unique(q[:,:,3]))=={0,255}
        assert not q[q[:,:,3]==0,:3].any()


def test_no_detached_pixels_or_cropped_body():
    for i in range(16):
        p=np.array(Image.open(OUT/f"{i+1:02d}.png"))
        points=set(map(tuple,np.argwhere(p[:,:,3]!=0)))
        queue=deque([points.pop()])
        while queue:
            y,x=queue.popleft()
            for dy in (-1,0,1):
                for dx in (-1,0,1):
                    pos=(y+dy,x+dx)
                    if pos in points:
                        points.remove(pos)
                        queue.append(pos)
        assert not points, f"detached pixels in frame {i+1}"


def test_strip_and_preview_direction_order():
    for row in (9,10):
        strip=Image.open(OUT/f"look-row-{row}.png")
        assert strip.size==(1536,208) and strip.mode=="RGBA"
        for i in range(8):
            assert strip.crop((i*192,0,(i+1)*192,208)).tobytes()==Image.open(OUT/f"{(row-9)*8+i+1:02d}.png").tobytes()
    for name,duration in [("preview.gif",180),("preview-slow.gif",500)]:
        im=Image.open(OUT/name)
        assert im.n_frames==16
        for i in range(16):
            im.seek(i)
            assert im.info["duration"]==duration


def test_official_atlas_remains_frozen():
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()=="d697e573268b66cb0f6a062480ec87c8c11712ca34b57f8c2fc0a97ed6e2164a"
