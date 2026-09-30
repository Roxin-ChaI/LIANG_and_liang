from copy import deepcopy
import json

import pytest

from tools.gate_f0_v2 import REVIEW, audit, resolve


@pytest.fixture(scope="module")
def evidence():
    return audit(), json.loads(REVIEW.read_text())


def test_reviewed_morph_pass_only_permits_entry_audit(evidence):
    report, review = evidence
    result = resolve(report, review)
    assert result["status"] == "F0_MORPH_ENDPOINT_APPROVED"
    assert result["entryAuditAllowed"] and not result["runtimeIntegrationAllowed"]
    assert result["humanApproval"] == "PENDING"


@pytest.mark.parametrize("channel", ["face", "pants", "jacketStructure", "completedFengForm"])
def test_numeric_geometry_cannot_waive_semantic_fail(evidence, channel):
    report, review = evidence
    changed = deepcopy(review)
    changed["checks"][channel]["status"] = "FAIL"
    result = resolve(report, changed)
    assert result["status"] == "F0_V2_QA_FAIL" and not result["entryAuditAllowed"]


@pytest.mark.parametrize("key", ["sourceSha256", "candidateSha256"])
def test_review_must_bind_both_actual_images(evidence, key):
    report, review = evidence
    changed = deepcopy(review)
    changed[key] = "stale"
    assert not resolve(report, changed)["morphApproved"]


def test_failed_lock_cannot_be_approved_visually(evidence):
    report, review = evidence
    failed = {**report, "technicalPass":False}
    assert not resolve(failed, review)["morphApproved"]
