from PIL import Image
import json
import pytest

from tools.prepare_transition_k1_candidate import SLOT, fixed_crop, native_geometry, prepare, prepare_reference, rejected_overlay
from tools.specify_transition_keyframes import approved_inputs


def test_reference_padding_and_fixed_crop_are_exact_without_sprite_resizing(tmp_path):
    path = tmp_path/"reference.png"
    prepare_reference(path)
    with Image.open(path) as source:
        cell,note = fixed_crop(source)
        assert source.size == (1024,1024)
    assert cell.tobytes() == approved_inputs()[0][2].tobytes()
    assert note["resizeOperations"] == 0 and note["integerRegistrationOperations"] == 0
    assert note["fixedCrop"] == list(SLOT)
    with pytest.raises(ValueError,match="overwrite"):
        prepare_reference(path)


def test_oversized_or_shifted_source_is_rejected_not_fitted_or_clipped(tmp_path):
    source = Image.new("RGBA",(1024,1024))
    source.paste(approved_inputs()[0][2],(415,400))
    cell,note = fixed_crop(source)
    assert cell is None and note["opaquePixelsOutsideFixedSlot"] > 0
    assert note["resizeOperations"] == 0
    assert fixed_crop(Image.new("RGBA",(384,416)))[0] is None


def test_candidate_qa_cannot_approve_or_generate_k2k3(tmp_path):
    source = tmp_path/"unit-fixture-only.png"
    approved_inputs()[0][2].save(source)
    result = prepare(source,tmp_path/"candidate")
    assert result["status"] == "AWAITING_INDEPENDENT_K1_REVIEW"
    assert not result["runtimeEligible"] and not result["K2K3Regenerated"]
    assert (tmp_path/"candidate/K1.png").exists()
    assert not (tmp_path/"candidate/K2.png").exists()


def test_rejected_source_never_emits_cropped_candidate(tmp_path):
    source = tmp_path/"oversized-unit-fixture-only.png"
    Image.new("RGBA",(1024,1024),(100,100,100,255)).save(source)
    result = prepare(source,tmp_path/"candidate")
    assert result["status"] == "K1_QA_FAIL" and not result["candidateEmitted"]
    assert not (tmp_path/"candidate/K1.png").exists()
    assert (tmp_path/"candidate/raw-native.png").read_bytes() == source.read_bytes()
    assert (tmp_path/"candidate/qa/rejected-native-layout-overlay.png").exists()
    assert (tmp_path/"candidate/qa/native-detail-contact-sheet.png").exists()


@pytest.mark.parametrize("attempt", (1,2))
def test_actual_native_generation_failures_are_never_scaled_into_passing_cells(attempt):
    from tools.validate_transition_k1 import ROOT
    source = ROOT / f"assets/rework/v0.1.0/transition-keyframes/k1-only/sources/K1-attempt-{attempt}-native.png"
    with Image.open(source) as image:
        cell,note = fixed_crop(image)
        geometry = native_geometry(image)
    assert cell is None
    assert note["status"] == "SOURCE_LAYOUT_FAIL"
    assert note["sourceSize"] == [1254,1254]
    assert note["resizeOperations"] == note["integerRegistrationOperations"] == 0
    assert geometry["coordinateSpace"].startswith("native source")
    assert geometry["hardAlphaBboxSizeAt128"][1] > 208  # no native fitting without forbidden scaling/clipping


def test_native_geometry_does_not_mislabel_foreground_as_anatomical_head():
    info = native_geometry(approved_inputs()[0][2])
    assert info["alphaBbox"] == [54,4,122,204]
    assert info["alphaBboxSize"] == [68,200]
    assert "headBbox" not in info


def test_qa_overlay_keeps_fixed_target_coordinates_and_never_fits_source():
    canonical = approved_inputs()[0][2]
    raw = Image.new("RGBA",(1254,1254))
    raw.paste(canonical,SLOT[:2])
    before = raw.tobytes()
    overlay = rejected_overlay(canonical,raw)
    assert overlay.size == raw.size and raw.tobytes() == before
    assert overlay.getchannel("A").getbbox() == (470,412,538,612)
    assert all(p == (255,255,255,255) for p in overlay.get_flattened_data() if p[3])


@pytest.mark.parametrize("attempt", (1,2))
def test_actual_failure_reports_retain_native_truth_and_never_open_chain(attempt):
    from tools.validate_transition_k1 import ROOT
    package = ROOT / f"assets/rework/v0.1.0/transition-keyframes/k1-only/attempt-{attempt}"
    report = json.loads((package/"qa/validation.json").read_text())
    with Image.open(package/"raw-native.png") as image:
        assert report["nativeSourceGeometry"] == native_geometry(image)
    assert report["status"] == "K1_QA_FAIL"
    assert not report["localChainAllowed"] and not report["runtimeEligible"]
    assert not report["candidateEmitted"] and not (package/"K1.png").exists()
    assert "NOT_VERIFIED" in report["headLandmarks"]
