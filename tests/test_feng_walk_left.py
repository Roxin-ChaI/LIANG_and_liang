import json
import shutil

import numpy as np
import pytest
from PIL import Image

from tools.build_feng_walk_left import OUT, SOURCE, build, mirror_frames, verified_frames
from tools.build_animation_review import sha256


def test_exact_mirror_and_same_frame_order():
    originals = verified_frames()
    strip = Image.open(OUT / "feng-running-left.png")
    assert strip.mode == "RGBA" and strip.size == (1536, 208)
    for i, frame in enumerate(originals):
        left = Image.open(OUT / f"left-{i+1:02d}.png")
        assert np.array_equal(np.array(left), np.array(frame)[:, ::-1])
        assert left.tobytes() == strip.crop((i*192, 0, (i+1)*192, 208)).tobytes()
        assert left.transpose(Image.Transpose.FLIP_LEFT_RIGHT).tobytes() == frame.tobytes()


def test_alpha_margins_baseline_and_geometry():
    for i, source in enumerate(verified_frames(), 1):
        frame = Image.open(OUT / f"left-{i:02d}.png")
        a = np.array(frame)
        assert frame.mode == "RGBA" and frame.size == (192, 208)
        assert set(np.unique(a[:, :, 3])) == {0, 255}
        assert not np.any(a[a[:, :, 3] == 0, :3])
        x, y, r, b = source.getbbox()
        assert frame.getbbox() == (192-r, y, 192-x, b)
        assert b == 204 and y >= 2 and x >= 2 and r <= 190


@pytest.mark.parametrize("name,delay,size", [
    ("preview.gif", 140, (384, 416)), ("preview-slow.gif", 450, (384, 416)),
    ("preview-native.gif", 140, (192, 208)), ("right-left-comparison.gif", 140, (768, 416))])
def test_previews(name, delay, size):
    im = Image.open(OUT / name)
    assert im.n_frames == 8 and im.info["loop"] == 0 and im.size == size
    for i in range(8):
        im.seek(i)
        assert im.info["duration"] == delay


def test_report_and_all_eight_temporal_edges():
    report = json.loads((OUT / "validation.json").read_text())
    assert report["structuralStatus"] == "PASS" and report["userApproval"] == "PENDING"
    assert not report["runtimeIntegrated"] and report["appTest"] == "NOT_TESTED"
    assert report["sourceApprovalSha256"] == sha256(SOURCE / "review-status.json")
    assert [(e["from"], e["to"]) for e in report["edges"]] == [(i+1, (i+1)%8+1) for i in range(8)]
    right = verified_frames()
    for i, edge in enumerate(report["edges"]):
        a = np.array(right[i]); b = np.array(right[(i+1)%8])
        assert edge["changedPixels"] == int(np.any(a != b, axis=2).sum())
    for path, digest in report["sha256"].items():
        assert sha256(OUT / path) == digest


def test_reject_overwrite():
    with pytest.raises(FileExistsError):
        build()


def test_reject_invalid_frame_count():
    with pytest.raises(ValueError):
        mirror_frames(verified_frames()[:4])


def test_reject_tampered_source(tmp_path):
    source = tmp_path / "source"
    shutil.copytree(SOURCE / "review-r2", source / "review-r2")
    shutil.copyfile(SOURCE / "review-status.json", source / "review-status.json")
    (source / "review-r2/right-01.png").write_bytes(b"tampered")
    with pytest.raises(ValueError, match="Frozen source changed"):
        verified_frames(source)
