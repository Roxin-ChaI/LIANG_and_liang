import hashlib
from collections import deque

import numpy as np
import pytest
from PIL import Image

from tools.repair_feng_look_r3 import OUT, SOURCE, ROOT, frame, repair


@pytest.fixture(scope="module")
def originals():
    atlas = Image.open(SOURCE).convert("RGBA")
    return [frame(atlas, 9 + i // 8, i % 8) for i in range(16)]


def test_official_atlas_remains_frozen():
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == "d697e573268b66cb0f6a062480ec87c8c11712ca34b57f8c2fc0a97ed6e2164a"


@pytest.mark.parametrize("i", range(16))
def test_whole_hand_identity_and_hard_edges(originals, i):
    actual = Image.open(OUT / f"{i+1:02d}.png")
    expected, _ = repair(originals[i], originals[0])
    assert actual.mode == "RGBA" and actual.size == (192, 208)
    assert actual.tobytes() == expected.tobytes()
    assert actual.crop((62, 44, 115, 108)).tobytes() == originals[i].crop((62, 44, 115, 108)).tobytes()
    pixels = np.array(actual)
    assert set(np.unique(pixels[:, :, 3])) == {0, 255}
    assert not pixels[pixels[:, :, 3] == 0, :3].any()
    assert actual.getchannel("A").getbbox() == (42, 4, 146, 204)
    # Check connectivity, not merely a bbox: detached white/skin fragments fail.
    points = set(map(tuple, np.argwhere(pixels[:, :, 3] != 0)))
    todo = deque([points.pop()])
    while todo:
        y, x = todo.popleft()
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                p = (y + dy, x + dx)
                if p in points:
                    points.remove(p)
                    todo.append(p)
    assert not points
    palette = set(map(tuple, np.array(originals[i]).reshape(-1, 4)))
    palette.update(map(tuple, np.array(originals[0]).reshape(-1, 4)))
    assert set(map(tuple, pixels.reshape(-1, 4))) <= palette | {(0, 0, 0, 0)}


def test_strips_preserve_all_direction_indices():
    for row in (9, 10):
        strip = Image.open(OUT / f"look-row-{row}.png")
        assert strip.mode == "RGBA" and strip.size == (1536, 208)
        for i in range(8):
            standalone = Image.open(OUT / f"{(row-9)*8+i+1:02d}.png")
            assert strip.crop((192*i, 0, 192*(i+1), 208)).tobytes() == standalone.tobytes()


def test_regression_rejected_palm_cut_is_not_reused(originals):
    rejected = Image.open(ROOT / "assets/rework/v0.1.0/action-repair-2026-10-02/feng.webp")
    for i in (10, 11, 13, 14, 15):
        roi = (70, 57, 107, 91)
        broken = frame(rejected, 9+i//8, i%8).crop(roi).tobytes()
        fixed = Image.open(OUT / f"{i+1:02d}.png").crop(roi).tobytes()
        assert fixed == originals[i].crop(roi).tobytes()
        assert fixed != broken


@pytest.mark.parametrize("name,duration", [("preview.gif", 180), ("preview-slow.gif", 500)])
def test_gif_contains_every_frame(name, duration):
    gif = Image.open(OUT / name)
    assert gif.n_frames == 16
    for i in range(16):
        gif.seek(i)
        assert gif.info["duration"] == duration
