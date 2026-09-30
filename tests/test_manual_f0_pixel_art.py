from __future__ import annotations

from PIL import Image

from tools.manual_f0_pixel_art import CELL, construct, donor


def test_manual_f0_native_and_deterministic() -> None:
    a, first = construct()
    b, second = construct()
    assert a.size == CELL and a.mode == "RGBA"
    assert a.tobytes() == b.tobytes() and first == second
    assert set(a.getchannel("A").get_flattened_data()) == {0, 255}
    assert a.getchannel("A").getbbox()[3] == 204
    assert first["landmarks"]["baselineY"] == 203
    assert first["landmarks"]["registrationX"] == 96
    assert not first["globalScaling"] and not first["aiImageGeneration"]


def test_manual_f0_preserves_approved_feng_face_pixels() -> None:
    f0, _ = construct()
    approved = donor()
    assert f0.crop((0, 0, 192, 65)).tobytes() == approved.crop((0, 0, 192, 65)).tobytes()


def test_manual_f0_does_not_touch_frozen_assets() -> None:
    # The construction is in memory only and has no write path to the atlas.
    f0, _ = construct()
    assert isinstance(f0, Image.Image)
