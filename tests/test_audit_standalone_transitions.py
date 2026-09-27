from PIL import Image

from tools.audit_standalone_transitions import COUNTS, MODES, changed_pixel_count


def test_transition_audit_covers_both_directions_and_work_modes():
    assert COUNTS == {"gu_to_feng": 10, "feng_to_gu": 8}
    assert MODES == ("idle", "running", "hover")


def test_boundary_change_measure_detects_alpha_and_rgb_only_changes(tmp_path):
    paths = []
    for index in range(3):
        image = Image.new("RGBA", (4, 4))
        image.putpixel((1, 1), (20 + (10 if index >= 1 else 0), 30, 40, 255))
        if index == 2:
            image.putpixel((2, 2), (20, 30, 40, 255))
        path = tmp_path / f"frame-{index}.png"
        image.save(path)
        paths.append(path)
    assert changed_pixel_count(paths[0], paths[1]) == 1
    assert changed_pixel_count(paths[1], paths[2]) == 1
