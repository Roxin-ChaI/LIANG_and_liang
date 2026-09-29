import pytest

from tools import f0_transition_endpoint_spec as f0


def test_spec_is_a_distinct_endpoint_not_an_approved_idle_replacement():
    report = f0.specification()
    assert report["status"] == "SPECIFICATION_ONLY"
    assert report["generatedImages"] == 0
    assert not report["approvedAssetsMayBeEdited"]
    assert not report["appIntegrationAllowed"]
    assert not report["fullAnimationAllowed"]
    assert report["F0TargetGuide"]["baselineY"] == 203
    assert report["F0TargetGuide"]["registrationX"] == 96
    assert report["F0TargetGuide"]["headWidthPx"] == [49, 52]
    assert report["F0TargetGuide"]["headHeightPx"] == [54, 57]
    assert report["KB2"]["headSize"] == [56, 68]
    assert report["B"]["headGuideApproximate"]
    assert report["oneDirectStepFromKB2CanMeetOldHeadGuideBudget"] is False
    assert "separate Feng entry animation" in report["F0_to_BPolicy"]


def test_prepare_never_overwrites_existing_spec(tmp_path):
    output = tmp_path / "spec"
    assert f0.prepare(output)["status"] == "SPECIFICATION_ONLY"
    with pytest.raises(ValueError, match="overwrite"):
        f0.prepare(output)


def test_changed_source_stops_specification(monkeypatch):
    original = f0.digest
    monkeypatch.setattr(f0, "digest", lambda path: "wrong" if path == f0.KB2 else original(path))
    with pytest.raises(ValueError, match="changed"):
        f0.specification()
