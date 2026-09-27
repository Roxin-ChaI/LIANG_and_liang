from PIL import Image

from tools.audit_standalone_visual import ROWS, alpha_geometry
from tools.compile_standalone_visual_evidence import alpha_metrics


def test_visual_audit_covers_all_standard_v2_rows():
    assert [row for _, row, _, _ in ROWS] == list(range(9))
    assert {name for name, _, _, _ in ROWS} >= {"idle", "running", "waiting", "review",
                                                "jumping", "running-right", "running-left"}


def test_alpha_geometry_does_not_equate_action_width_with_identity():
    image = Image.new("RGBA", (256, 256))
    for x in range(80, 160):
        for y in range(20, 220):
            image.putpixel((x, y), (10, 20, 30, 255))
    assert alpha_geometry(image) == {"bbox": (80, 20, 160, 220),
                                     "centerX": 120.0, "baseline": 219}


def test_audit_detects_baseline_jump_and_rgb_only_frame_changes(tmp_path):
    frames = {}
    for index, baseline in enumerate((203, 198, 198)):
        image = Image.new("RGBA", (192, 208))
        for x in range(70, 122):
            for y in range(10, baseline + 1):
                image.putpixel((x, y), (20, 30, 40, 255))
        if index == 2:
            image.putpixel((90, 80), (80, 90, 100, 255))
        path = tmp_path / f"{index}.png"
        image.save(path)
        frames[index] = {"file": str(path), "geometry": alpha_geometry(image)}
    result = alpha_metrics(frames, 1)
    assert result["baselinesCssPx"] == [203, 198, 198]
    assert result["adjacentDifference"][1]["rgbBbox"] == (90, 80, 91, 81)
    assert result["adjacentDifference"][1]["alphaBbox"] is None
