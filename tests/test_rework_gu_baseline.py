from PIL import Image
import json
import pytest

from tools.rework_gu_baseline import ROOT, ROWS, derive, translate_cell
from tools.build_standalone_app import source_files


def test_candidate_only_translates_named_cells_and_preserves_every_rgba_pixel(tmp_path):
    source = ROOT / "assets/builds/gu/spritesheet.webp"
    output = tmp_path / "candidate.webp"
    source_bytes = source.read_bytes()
    result = derive(source, output)
    assert len(result["changes"]) == 30
    with Image.open(source) as image:
        original = image.convert("RGBA")
    with Image.open(output) as image:
        candidate = image.convert("RGBA")
    changed = {(row, frame) for row, count in ROWS.values() for frame in range(count)}
    for row in range(11):
        for frame in range(8):
            box = (frame * 192, row * 208, (frame + 1) * 192, (row + 1) * 208)
            before, after = original.crop(box), candidate.crop(box)
            if (row, frame) in changed:
                assert after.tobytes() == translate_cell(before, 5).tobytes()
                assert after.getchannel("A").getbbox()[3] - 1 == 203
                assert before.crop((0, 0, 192, 203)).tobytes() == after.crop((0, 5, 192, 208)).tobytes()
            else:
                assert after.tobytes() == before.tobytes()
    assert source.read_bytes() == source_bytes


def test_translation_refuses_clipping():
    image = Image.new("RGBA", (192, 208))
    image.putpixel((96, 207), (10, 20, 30, 255))
    with pytest.raises(ValueError, match="clip"):
        translate_cell(image, 5)


def test_build_override_is_explicit_and_only_changes_gu_source(tmp_path):
    atlas = tmp_path / "candidate.webp"
    atlas.write_bytes(b"candidate")
    standard = source_files()
    candidate = source_files(atlas)
    assert [relative for _, relative in standard] == [relative for _, relative in candidate]
    changes = [(a, b, path) for (a, path), (b, _) in zip(standard, candidate) if a != b]
    assert len(changes) == 1
    assert changes[0][1] == atlas
    assert changes[0][2].as_posix() == "assets/builds/gu/spritesheet.webp"


def test_candidate_window_work_baselines_match_idle():
    evidence = json.loads((ROOT / "docs/visual-rework/v0.1.0/baseline/window-metrics.json").read_text())
    assert evidence["guWorkBaselinePass"] is True
    rows = evidence["forms"]["gu"]["rows"]
    canonical = set(rows["idle"]["baselinesCssPx"])
    for state in ROWS:
        assert set(rows[state]["baselinesCssPx"]) == canonical
