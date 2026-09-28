"""Extraction proof is not animation approval; fixtures never become pet art."""
import hashlib
import json

from PIL import Image
import pytest

from tools.extract_transition_pose_regions import SOURCE, detect_regions, extract, normalize_shared_nearest


def test_actual_source_bounds_not_equal_grid_and_all_shoes_are_inside():
    with Image.open(SOURCE) as source:
        regions = detect_regions(source)
        assert len(regions) == 8
        assert regions[0]["sourceRegion"][3] == 484 != source.height // 2
        assert regions[4]["sourceRegion"][1] == 484
        rebuilt = Image.new("RGBA", source.size)
        for item in regions:
            l, t, r, b = item["sourceRegion"]
            cl, ct, cr, cb = item["subjectCoreBbox"]
            assert l <= cl < cr <= r and t <= ct < cb <= b
            rebuilt.paste(source.crop((l, t, r, b)), (l, t))
        assert rebuilt.tobytes() == source.tobytes()


def test_native_extraction_retains_every_rgba_pixel_without_resizing(tmp_path):
    before = hashlib.sha256(SOURCE.read_bytes()).hexdigest()
    output = tmp_path / "native"
    report = extract(SOURCE, output)
    assert report["sourceReconstructedExactly"] and report["resizeOperationsOnAssets"] == 0
    assert not report["sourceArtIncomplete"] and not report["runtimeEligible"]
    assert all(not item["fitsUnscaledRuntime"] for item in report["frames"])
    with Image.open(SOURCE) as source:
        for item in report["frames"]:
            crop = source.crop(item["sourceRegion"])
            x, y = item["nativePaste"]
            with Image.open(output / item["file"]) as frame:
                assert frame.crop((x, y, x + crop.width, y + crop.height)).tobytes() == crop.tobytes()
    assert before == hashlib.sha256(SOURCE.read_bytes()).hexdigest()
    with pytest.raises(ValueError, match="overwrite"):
        extract(SOURCE, output)


def test_authorized_common_scale_no_per_pose_fit_or_runtime_reapproval(tmp_path):
    report = normalize_shared_nearest(SOURCE, tmp_path / "normalized")
    assert report["sharedScale"] == 200 / 475
    assert not report["perPoseScale"] and report["redrawOperations"] == 0
    assert not report["runtimeEligible"] and not report["appIntegrated"]
    assert not report["identityApproved"] and not report["endpointContinuityApproved"]
    assert len({r["sharedScale"] for r in report["frames"]}) == 1
    for item in report["frames"]:
        assert item["normalBaselineY"] == 203 and item["foregroundLostToCanvas"] == 0
        assert 95.5 <= item["normalLowerBodyCenterX"] <= 96.5
        assert item["singleNearestResizeSize"] == [round(v * report["sharedScale"]) for v in item["sourceRegionSize"]]
        with Image.open(tmp_path / "normalized" / item["normalFile"]) as normal:
            assert normal.size == (192, 208) and normal.mode == "RGBA"
            assert normal.getchannel("A").getbbox()[3] - 1 == 203
            assert {p[3] for p in normal.get_flattened_data()} == {0, 255}
            assert not any(any(p[:3]) for p in normal.get_flattened_data() if p[3] == 0)
            with Image.open(tmp_path / "normalized" / item["runtimeFile"]) as runtime:
                assert runtime.size == (208, 224)
                assert runtime.crop((9, 14, 201, 222)).tobytes() == normal.tobytes()
    with pytest.raises(ValueError, match="overwrite"):
        normalize_shared_nearest(SOURCE, tmp_path / "normalized")


def test_ambiguous_or_edge_cut_source_fails_without_fabricating_pixels():
    with pytest.raises(ValueError, match="exactly eight"):
        detect_regions(Image.new("RGBA", (192, 208)))
    with Image.open(SOURCE) as source:
        with pytest.raises(ValueError, match="SOURCE_ART_INCOMPLETE"):
            detect_regions(source.crop((78, 0, source.width, source.height)))
    with pytest.raises(ValueError, match="RGBA"):
        detect_regions(Image.new("RGB", (192, 208)))


def test_retained_extraction_matches_tool_and_preserves_native_evidence(tmp_path):
    root = SOURCE.parents[2] / "transition-keyframes/feng-to-gu-extraction/shared-normalized"
    retained = json.loads((root / "qa/validation.json").read_text())
    repeated = normalize_shared_nearest(SOURCE, tmp_path / "repeated")
    for old, new in zip(retained["frames"], repeated["frames"]):
        assert old["normalSha256"] == new["normalSha256"]
        assert old["runtimeSha256"] == new["runtimeSha256"]
    assert (root.parent / "native-inspection-frames/feng_to_gu_00.png").exists()
