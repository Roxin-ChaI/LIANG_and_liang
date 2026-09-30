from PIL import Image

from tools.idle_appearance_contract import canonical, mechanical_gate, measure, palette


def test_formal_idle_reference_pixels_and_real_geometry():
    refs = canonical()
    for image in refs.values():
        info = measure(image)
        assert info["actualHeight"] == 200
        assert info["actualBaseline"] == 203
        assert info["actualAlphaBbox"][1] == 4
        assert info["alphaValues"] == [0, 255]
        assert info["hiddenRgbPixels"] == 0
    assert measure(refs["gu"])["actualAlphaBbox"] == [54, 4, 122, 204]
    assert measure(refs["feng"])["actualAlphaBbox"] == [44, 4, 148, 204]


def test_idle_copies_cannot_pad_transition_count():
    refs = canonical()
    for image in refs.values():
        result = mechanical_gate(image, refs)
        assert not result["checks"]["notIdlePadding"]
        assert not result["mechanicalPass"]
        assert not result["artApproved"]


def test_smaller_same_palette_character_cannot_pass_by_foot_alignment():
    refs = canonical()
    smaller = refs["gu"].resize((180, 196), Image.Resampling.NEAREST)
    altered = Image.new("RGBA", (192, 208))
    altered.paste(smaller, (6, 12))
    result = mechanical_gate(altered, refs)
    assert result["checks"]["usesOnlyApprovedIdleSubjectColors"]
    assert not result["checks"]["subjectHeightExactly200"]
    assert not result["mechanicalPass"]


def test_partial_alpha_hidden_background_and_new_colors_are_rejected():
    refs = canonical()
    altered = refs["gu"].copy()
    altered.putpixel((0, 0), (1, 2, 3, 0))
    altered.putpixel((85, 48), (1, 2, 3, 128))
    result = mechanical_gate(altered, refs)
    assert not result["checks"]["alphaOnly0And255"]
    assert not result["checks"]["noHiddenBackgroundRgb"]
    assert not result["mechanicalPass"]


def test_correct_bbox_and_palette_never_approve_a_changed_eye():
    refs = canonical()
    altered = refs["gu"].copy()
    point = (85, 48)
    assert altered.getpixel(point)[3] == 255
    color = next(c for c in sorted(palette(refs["gu"])) if c != altered.getpixel(point)[:3])
    altered.putpixel(point, (*color, 255))
    result = mechanical_gate(altered, refs)
    assert result["mechanicalPass"]
    assert result["styleIdentityAnatomyGate"] == "UNVERIFIED"
    assert not result["artApproved"]
