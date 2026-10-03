import hashlib
import json

import numpy as np
from PIL import Image

from tools import repair_reviewed_actions as subject


def test_original_sources_unchanged_and_selected_files_exact():
    report = json.loads((subject.OUTPUT / "report.json").read_text())
    for relative, expected in report["sources"].items():
        assert subject.digest(subject.ROOT / relative) == expected
    gu = Image.open(subject.OUTPUT / "gu.webp").convert("RGBA")
    for state, row, count in [("failed", 5, 8), ("waiting", 6, 6)]:
        source = Image.open(subject.ROOT / f"assets/rework/v0.1.0/gu-eye-repair-2026-10-01/{state}.png").convert("RGBA")
        assert gu.crop((0, row*208, count*192, (row+1)*208)).tobytes() == source.tobytes()


def test_unaffected_rows_remain_pixel_identical():
    for form in ("gu", "feng"):
        base = subject.ROOT / ("assets/rework/v0.1.0/gu/spritesheet.webp" if form == "gu" else "assets/builds/feng/spritesheet.webp")
        before = Image.open(base).convert("RGBA")
        after = Image.open(subject.OUTPUT / f"{form}.webp").convert("RGBA")
        rows = (0, 1, 2, 4, 7, 8) if form == "gu" else (0, 4, 5, 6, 7, 8)
        assert after.size == (1536, 2288)
        for row in rows:
            area = (0, row*208, 1536, (row+1)*208)
            assert before.crop(area).tobytes() == after.crop(area).tobytes()


def test_look_heads_unchanged_and_body_has_no_directional_seam():
    for form, cutoff, last in [("gu", 70, 94), ("feng", 45, 74)]:
        before = Image.open(subject.ROOT / f"assets/builds/{form}/spritesheet.webp").convert("RGBA")
        after = Image.open(subject.OUTPUT / f"{form}.webp").convert("RGBA")
        donor = subject.frame(after, 9, 0)
        for n in range(16):
            a, b = [subject.frame(im, 9+n//8, n%8) for im in [before, after]]
            assert a.crop((0, 0, 192, cutoff)).tobytes() == b.crop((0, 0, 192, cutoff)).tobytes()
            assert b.crop((0, last, 192, 208)).tobytes() == donor.crop((0, last, 192, 208)).tobytes()


def test_fringe_changes_only_remove_boundary_pixels_not_recolor():
    for form, rows in [("gu", [3]), ("feng", [1, 2, 3])]:
        base = subject.ROOT / ("assets/rework/v0.1.0/gu/spritesheet.webp" if form == "gu" else "assets/builds/feng/spritesheet.webp")
        before = Image.open(base).convert("RGBA")
        after = Image.open(subject.OUTPUT / f"{form}.webp").convert("RGBA")
        for row in rows:
            for i in range(subject.COUNTS[row]):
                a, b = [np.array(subject.frame(im, row, i)) for im in [before, after]]
                changed = np.any(a != b, axis=2)
                assert not np.any(b[changed])
                assert np.count_nonzero(b[:,:,3]) > .9 * np.count_nonzero(a[:,:,3])


def test_historical_two_copy_and_reverse_manifest_unchanged():
    for i in range(10):
        source = Image.open(subject.ROOT / f"assets/rework/v0.1.0/transition-full/gu-to-feng-retry/frames/gu_to_feng_{i:02d}.png").convert("RGBA")
        padded = Image.open(subject.OUTPUT / f"gu_to_feng/gu_to_feng_{i+1:02d}.png").convert("RGBA")
        assert padded.size == (224, 240)
        assert padded.crop((16, 18, 208, 226)).tobytes() == source.tobytes()
    for line in (subject.OUTPUT / "transform-overlay.sha256").read_text().splitlines():
        sha, relative = line.split()
        if "feng_to_gu/" in relative:
            assert subject.digest(subject.ROOT / relative) == sha
