from __future__ import annotations

from tools.gate_manual_f0 import audit, resolve


def test_direct_kb2_f0_fails_conservative_head_motion_gate() -> None:
    report = audit()
    assert all(report["checks"].values())
    assert report["delta"]["headSizeDelta"] == [-6, -13]
    assert report["delta"]["headCenterDelta"] == [1.0, -6.5]
    assert not report["delta"]["numericPass"]
    assert not report["numericPass"]


def test_missing_or_stale_visual_review_cannot_approve() -> None:
    report = audit()
    for review in ({}, {"reviewer": "independent", "verdict": "PASS", "reviewedF0Sha256": "stale"},
                   {"reviewer": "independent", "verdict": "PASS", "reviewedF0Sha256": report["F0Sha256"]}):
        result = resolve(report, review)
        assert result["status"] == "F0_MANUAL_QA_FAIL"
        assert not result["F0ToIdleAuditAllowed"]
