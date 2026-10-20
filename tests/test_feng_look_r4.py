import hashlib

import numpy as np
from PIL import Image

from tools.repair_feng_look_r4 import SOURCE, OUT, frame, eye_mask


def test_complete_body_head_and_alpha_reuse_approved_idle():
    atlas = Image.open(SOURCE).convert("RGBA")
    canonical = np.array(frame(atlas, 0, 0))
    mask = eye_mask()
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == "d697e573268b66cb0f6a062480ec87c8c11712ca34b57f8c2fc0a97ed6e2164a"
    assert not mask[44:].any()
    for i in range(16):
        im = Image.open(OUT / f"{i+1:02d}.png")
        p = np.array(im)
        assert im.mode == "RGBA" and im.size == (192, 208)
        # Explicitly prevent recurrence of mixing hand/elbow/cuff/lapel donors.
        assert np.array_equal(p[~mask], canonical[~mask])
        assert np.array_equal(p[:, :, 3], canonical[:, :, 3])
        assert set(np.unique(p[:, :, 3])) == {0, 255}
        assert not p[p[:, :, 3] == 0, :3].any()
        assert im.getchannel("A").getbbox()[3] == 204


def test_pupils_move_inside_existing_eyelids_and_direction_slots_keep_order():
    frames = [Image.open(OUT / f"{i+1:02d}.png") for i in range(16)]
    for a, b in [(0, 8), (4, 12)]:
        assert frames[a].tobytes() != frames[b].tobytes()
    for row in (9, 10):
        strip = Image.open(OUT / f"look-row-{row}.png")
        assert strip.size == (1536, 208) and strip.mode == "RGBA"
        for i in range(8):
            assert strip.crop((192*i, 0, 192*(i+1), 208)).tobytes() == frames[(row-9)*8+i].tobytes()


def test_palette_does_not_introduce_new_colors():
    atlas = Image.open(SOURCE).convert("RGBA")
    palette = set(map(tuple, np.array(frame(atlas, 0, 0)).reshape(-1, 4)))
    for i in range(16):
        im = Image.open(OUT / f"{i+1:02d}.png")
        assert set(map(tuple, np.array(im).reshape(-1, 4))) <= palette


def test_review_gifs_keep_every_direction_and_display_duration():
    for name, duration in [("preview.gif", 180), ("preview-slow.gif", 500)]:
        im = Image.open(OUT / name)
        assert im.n_frames == 16
        for i in range(16):
            im.seek(i)
            assert im.info["duration"] == duration
