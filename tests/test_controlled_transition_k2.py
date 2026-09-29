from PIL import Image
import pytest

from tools.controlled_transition_k2 import assess, masks, prepare_spec, source, specification


def test_spec_pins_explicitly_approved_k1_without_modifying_historical_records():
    report = specification()
    assert report["sourceSha256"] == "3fe2510fce45d2e7fb63e2018f79fe69ef9f05c470634903fa580700acc9e246"
    assert "K1_ART_APPROVED" in report["sourceApproval"]
    assert report["headSizePermittedRange"] == [[64, 72], [76, 84]]
    assert report["maxHeadCenterDeltaPx"] == [3, 3]
    assert report["maxAnatomicalShoulderGrowthPx"] == 12
    assert not report["appIntegrationAllowed"]


def test_masks_hold_whole_head_neck_collar_hands_legs_feet_and_registration():
    locked, editable = masks()
    assert all(a+b == 255 for a, b in zip(locked.get_flattened_data(), editable.get_flattened_data()))
    for xy in ((54, 4), (121, 83), (88, 96), (96, 203), (76, 157), (0, 0), (191, 95)):
        assert locked.getpixel(xy) == 255
    assert editable.getpixel((70, 110)) == 255


def test_exact_k1_is_not_an_intermediate_body_or_art_approval():
    report = assess(source())
    assert report["checks"]["lockedByteIdentical"]
    assert not report["checks"]["capGrowthWithin12"]
    assert not report["technicalPass"] and not report["localChainAllowed"]


@pytest.mark.parametrize("xy,rgba", [((80, 25), (0, 0, 0, 255)), ((0, 0), (1, 0, 0, 0)),
                                     ((88, 94), (0, 0, 0, 0)), ((76, 203), (0, 0, 0, 0))])
def test_locked_identity_color_alpha_and_transparent_bytes_cannot_change(xy, rgba):
    image = source()
    image.putpixel(xy, rgba)
    assert not assess(image)["checks"]["lockedByteIdentical"]


@pytest.mark.parametrize("image", [Image.new("RGBA", (384, 416)), Image.new("RGB", (192, 208))])
def test_geometry_cannot_be_silently_scaled_or_converted(image):
    with pytest.raises(ValueError, match="native"):
        assess(image)


def test_widened_outer_body_beyond_six_pixels_fails_even_inside_mask():
    image = source()
    image.putpixel((63, 105), (0, 0, 0, 255))
    image.putpixel((128, 105), (0, 0, 0, 255))
    assert not assess(image)["checks"]["bodyEdgesGradual"]


def test_partial_alpha_or_invented_cloth_color_fails():
    image = source()
    image.putpixel((72, 110), (123, 1, 2, 128))
    report = assess(image)
    assert not report["checks"]["binaryAlpha"]
    assert not report["checks"]["paletteFromK1"]


def test_contract_phase_emits_only_masks_and_spec_not_candidate_or_chain(tmp_path):
    report = prepare_spec(tmp_path/"spec")
    assert report["status"] == "SPECIFICATION_ONLY"
    assert sorted(p.name for p in (tmp_path/"spec").iterdir()) == ["editable-mask.png", "locked-mask.png", "mask-guide.png", "specification.json"]
    with pytest.raises(ValueError, match="overwrite"):
        prepare_spec(tmp_path/"spec")
