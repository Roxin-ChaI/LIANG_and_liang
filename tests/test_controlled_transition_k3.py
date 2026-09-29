from PIL import Image
import pytest

from tools.controlled_transition_k3 import OUTPUT, assess, masks, prepare_spec, source, specification


def test_spec_records_current_user_approval_without_rewriting_k2_history():
    report = specification()
    assert "K2_ART_APPROVED" in report["sourceApproval"]
    assert report["sourceSha256"] == "565122ea1364eebd56a0d6d3b53934bef8d45d53cb1787eedf4ee1f812cdfcec"
    assert report["headSizePermittedRange"] == [[63,73],[75,85]]
    assert report["maxHeadCenterDeltaPx"] == [3,3]
    assert report["capBandGrowthTargetPx"] == [10,14]
    assert report["maxBodyWidthGrowthPx"] == 14
    assert report["generatedPoses"] == 0
    assert not report["appIntegrationAllowed"]


def test_masks_hold_full_identity_and_lower_body_including_upper_hands():
    locked, editable = masks()
    assert all(a+b == 255 for a,b in zip(locked.get_flattened_data(), editable.get_flattened_data()))
    for xy in ((54,4),(121,83),(88,96),(75,142),(110,145),(96,203),(0,0),(191,95)):
        assert locked.getpixel(xy) == 255
    assert editable.getpixel((65,105)) == 255


def test_identical_k2_cannot_be_accepted_as_new_growth_or_art_approval():
    report = assess(source())
    assert report["checks"]["lockedByteIdentical"]
    assert not report["checks"]["capGrowth10to14"]
    assert not report["checks"]["bodyWidthGrowthWithin14"]
    assert not report["technicalPass"] and not report["localChainAllowed"]


@pytest.mark.parametrize("xy,rgba", [((80,25),(0,0,0,255)),((0,0),(1,0,0,0)),((88,94),(0,0,0,0)),((75,142),(0,0,0,0)),((76,203),(0,0,0,0))])
def test_locked_identity_skin_alpha_or_transparent_bytes_cannot_change(xy,rgba):
    image = source()
    image.putpixel(xy,rgba)
    assert not assess(image)["checks"]["lockedByteIdentical"]


@pytest.mark.parametrize("image", [Image.new("RGBA",(384,416)),Image.new("RGB",(192,208))])
def test_geometry_cannot_be_silently_scaled_or_converted(image):
    with pytest.raises(ValueError,match="native"):
        assess(image)


def test_excess_body_edge_or_cap_growth_fails():
    image = source()
    for x in range(57,132):
        image.putpixel((x,95),(0,0,0,255))
    report = assess(image)
    assert not report["checks"]["bodyEdgesGradual"]
    assert not report["checks"]["capGrowth10to14"]


def test_partial_alpha_and_new_palette_fail():
    image = source()
    image.putpixel((65,105),(123,1,2,128))
    report = assess(image)
    assert not report["checks"]["binaryAlpha"]
    assert not report["checks"]["paletteFromK2"]


def test_spec_emits_only_masks_references_and_json_no_candidate(tmp_path):
    report = prepare_spec(tmp_path/"spec")
    assert report["status"] == "SPECIFICATION_ONLY"
    assert sorted(p.name for p in (tmp_path/"spec").iterdir()) == ["editable-mask.png","locked-mask.png","reference-mask-guide.png","specification.json"]
    with pytest.raises(ValueError,match="overwrite"):
        prepare_spec(tmp_path/"spec")


def test_saved_masks_match_fixed_contract():
    for name, expected in zip(("locked-mask.png","editable-mask.png"),masks()):
        with Image.open(OUTPUT/"spec"/name) as actual:
            assert actual.mode == "L" and actual.tobytes() == expected.tobytes()
