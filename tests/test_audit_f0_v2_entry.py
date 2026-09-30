import json

import pytest

from tools import audit_f0_v2_entry as entry


def test_actual_idle_connection_requires_separate_entry():
    report = entry.audit()
    review = json.loads((entry.OUT/"visual-review.json").read_text())
    result = entry.resolve_entry(report,review)
    assert result["status"] == "FENG_ENTRY_ANIMATION_REQUIRED"
    assert not result["directConnectionPass"] and not result["entryArtApproved"]
    assert report["delta"]["headSize"] == [-1,-1]
    assert report["delta"]["feetCenterX"] == {"left":-17.0,"right":18.5}
    assert report["entryPlan"]["plannedPoseCount"] == 4
    assert report["entryPlan"]["generatedPoses"] == 0
    assert not report["entryPlan"]["isPartOfMorphBudget"]


def test_entry_cannot_run_without_fresh_morph_pass(monkeypatch):
    monkeypatch.setattr(entry,"resolve",lambda *args:{"entryAuditAllowed":False})
    with pytest.raises(ValueError,match="Morph PASS"):
        entry.audit()


def test_stale_entry_review_is_not_an_audit_result():
    report = entry.audit()
    review = json.loads((entry.OUT/"visual-review.json").read_text())
    review["targetSha256"] = "old-B"
    result = entry.resolve_entry(report,review)
    assert result["status"] == "ENTRY_AUDIT_NOT_VERIFIED"
    assert not result["directConnectionPass"]
