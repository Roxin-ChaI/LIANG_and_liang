from PIL import Image
import pytest

from tools.locked_transition_k1 import HEAD, assess, masks, masked_bytes, prepare_spec, specification
from tools.specify_transition_keyframes import approved_inputs


def test_masks_are_binary_complementary_and_conservatively_lock_identity_and_feet():
    locked,editable = masks()
    assert locked.size == (192,208)
    assert set(locked.get_flattened_data()) == {0,255}
    assert all(a+b == 255 for a,b in zip(locked.get_flattened_data(),editable.get_flattened_data()))
    for x,y in ((0,0),(54,4),(121,83),(85,97),(96,203),(0,150),(191,150)):
        assert locked.getpixel((x,y)) == 255
    assert editable.getpixel((72,130)) == 255


def test_exact_a_passes_numeric_gate_but_never_self_approves_art():
    report = assess(approved_inputs()[0][2])
    assert report["technicalPass"]
    assert report["headBbox"] == list(HEAD)
    assert report["headCenterDelta"] == [0,0]
    assert report["lockedByteComparison"]["differentBytes"] == 0
    assert not report["localChainAllowed"] and not report["runtimeEligible"]


@pytest.mark.parametrize("xy,rgba", [((70,20),(0,0,0,255)),((80,60),(0,0,0,0)),
                                    ((0,0),(1,0,0,0)),((87,95),(255,255,255,255)),
                                    ((76,203),(0,0,0,0))])
def test_any_locked_color_alpha_or_transparent_rgb_change_fails(xy,rgba):
    a = approved_inputs()[0][2].copy()
    a.putpixel(xy,rgba)
    report = assess(a)
    assert not report["technicalPass"]
    assert report["lockedByteComparison"]["changedLockedPixels"] == 1


@pytest.mark.parametrize("image", [Image.new("RGBA",(384,416)),Image.new("RGB",(192,208))])
def test_geometry_or_mode_is_never_normalized(image):
    with pytest.raises(ValueError,match="native"):
        assess(image)


def test_masked_comparison_includes_transparent_bytes():
    a = approved_inputs()[0][2]
    locked,_ = masks()
    assert len(masked_bytes(a,locked)) == specification()["lockedPixelCount"]*4


def test_spec_emits_masks_only_not_k1_or_other_poses(tmp_path):
    report = prepare_spec(tmp_path/"spec")
    assert report["status"] == "SPECIFICATION_ONLY"
    assert report["effectiveHeadDeltaRequired"] == 0
    assert not (tmp_path/"spec/K1.png").exists()
    assert not (tmp_path/"spec/K2.png").exists()
    with pytest.raises(ValueError,match="overwrite"):
        prepare_spec(tmp_path/"spec")


def test_body_growth_beyond_edge_budget_fails_without_relaxing_mask():
    a = approved_inputs()[0][2].copy()
    for x in range(121,126):
        a.putpixel((x,132),(0,0,0,255))
    assert not assess(a)["checks"]["bodyRightWithin3"]


def test_partial_alpha_in_editable_area_fails():
    a = approved_inputs()[0][2].copy()
    rgba = a.getpixel((74,130))
    a.putpixel((74,130),(*rgba[:3],127))
    assert not assess(a)["checks"]["binaryAlpha"]
