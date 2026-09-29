import pytest

from tools import audit_feng_atlas_neutral as scan


def test_scan_every_v2_slot_without_selecting_f0():
    report, frames = scan.scan()
    assert report["atlasSha256"] == scan.FENG_ATLAS_SHA
    assert report["atlasSize"] == [1536, 2288]
    assert report["slotsScanned"] == 88
    assert len(report["records"]) == len(frames) == 88
    assert report["nonemptyFrames"] + report["emptySlots"] == 88
    assert report["records"][0]["rgbaSha256"] == report["formalIdle0RgbaSha256"]
    assert not report["F0Selected"]
    assert not report["sourcePixelsModified"]


def test_scan_keeps_baseline_and_registration_separate():
    report, _ = scan.scan()
    for entry in report["records"]:
        assert entry["registrationX"] == 96
        if entry["nonempty"]:
            assert entry["baselineY"] is not None
            assert entry["bodyBbox"] is not None
            assert entry["upperRegionBboxApprox"] is not None
        else:
            assert entry["baselineY"] is None


def test_prepare_only_creates_qa_and_refuses_overwrite(tmp_path):
    output = tmp_path / "qa"
    report = scan.prepare(output)
    assert report["slotsScanned"] == 88
    assert sorted(path.name for path in output.iterdir()) == ["all-88-slots-contact.png", "inventory.json"]
    with pytest.raises(ValueError, match="overwrite"):
        scan.prepare(output)


def test_modified_formal_atlas_stops_inventory(monkeypatch):
    actual = scan.digest
    monkeypatch.setattr(scan, "digest", lambda path: "wrong" if path == scan.FENG_ATLAS else actual(path))
    with pytest.raises(ValueError, match="changed"):
        scan.scan()
