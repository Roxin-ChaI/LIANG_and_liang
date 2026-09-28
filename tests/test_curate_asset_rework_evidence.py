from PIL import Image
import pytest

from tools.curate_asset_rework_evidence import sheet


def test_full_window_sheet_preserves_oversized_edges_with_nearest_only(tmp_path):
    source = tmp_path / "window.png"
    image = Image.new("RGBA", (512, 512), (0, 0, 0, 0))
    for x, y in ((0, 0), (510, 510)):
        image.putpixel((x, y), (200, 10, 200, 255))
        image.putpixel((x + 1, y + 1), (200, 10, 200, 255))
    image.save(source)
    output = tmp_path / "sheet.png"
    sheet([("full viewport", source)], output, 1)
    with Image.open(output) as result:
        assert result.getpixel((0, 28)) == (200, 10, 200, 255)
        assert result.getpixel((255, 283)) == (200, 10, 200, 255)
        assert result.size == (256, 284)


def test_unknown_capture_geometry_is_not_silently_rescaled(tmp_path):
    source = tmp_path / "window.png"
    Image.new("RGBA", (500, 500)).save(source)
    with pytest.raises(ValueError, match="dimensions"):
        sheet([("invalid", source)], tmp_path / "sheet.png", 1)
