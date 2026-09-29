import json

import pytest

from tools import audit_controlled_k3_chain as audit


def review(report):
    return {"reviewer": "TEST FIXTURE ONLY", "verdict": "B_TRANSITION_BRIDGE_REQUIRED", "K2_K3": "PASS", "K3_B": "FAIL",
            "reviewedK3RgbaSha256": report["K3RgbaSha256"], "reviewedBRgbaSha256": report["BRgbaSha256"]}


def test_read_only_chain_is_gated_and_reports_unforced_endpoint_gap(tmp_path):
    report = audit.prepare(tmp_path/"chain")
    assert report["K2_K3"] == "K2_K3_STATIC_PASS"
    assert report["K3Sha256"] == audit.K3_SHA
    assert report["K3_B"]["headSize"]["deltaApprox"] == [-19,-26]
    assert report["K3_B"]["headCenter"]["deltaApprox"] == [0.5,-13]
    assert report["K3_B"]["bodyBandBbox"]["delta"] == [-16,0,19,0]
    assert report["K3_B"]["bodyBandBbox"]["widthDelta"] == 35
    assert report["K3_B"]["shoulderCapBand"]["widthDelta"] == 31
    assert report["K3_B"]["baselineDelta"] == 0
    assert report["newPosesGenerated"] == 0 and not report["BModified"]
    assert not (tmp_path/"chain/B.png").exists()
    assert not (tmp_path/"chain/frames").exists()
    with pytest.raises(ValueError,match="overwrite"):
        audit.prepare(tmp_path/"chain")


@pytest.mark.parametrize("evidence", [{},{"reviewer": "fixture","verdict": "K2_K3_STATIC_PASS","reviewedRgbaSha256": "stale"},
                                     {"reviewer": "fixture","verdict": "MANUAL_PIXEL_ART_REQUIRED"}])
def test_no_b_audit_after_missing_stale_or_failed_incoming_review(tmp_path,evidence):
    path = tmp_path/"incoming.json"
    path.write_text(json.dumps(evidence))
    with pytest.raises(ValueError,match="STATIC_PASS"):
        audit.prepare(tmp_path/"chain",path)
    assert not (tmp_path/"chain").exists()


def test_metrics_alone_or_stale_review_never_claim_bridge_or_art_approval(tmp_path):
    report = audit.prepare(tmp_path/"chain")
    assert audit.resolve_chain(report,{})["status"] == "CHAIN_NOT_VERIFIED"
    evidence = review(report)
    evidence["reviewedBRgbaSha256"] = "stale"
    assert audit.resolve_chain(report,evidence)["status"] == "CHAIN_NOT_VERIFIED"


def test_only_paired_static_pass_allows_art_gate_and_failure_needs_bridge_not_pose_edits(tmp_path):
    report = audit.prepare(tmp_path/"chain")
    evidence = review(report)
    final = audit.resolve_chain(report,evidence)
    assert final["status"] == "B_TRANSITION_BRIDGE_REQUIRED"
    assert final["bridgeFramesRequired"] and final["bridgeFramesGenerated"] == 0
    assert not final["K1K2K3BModifiedForOutgoingMatch"] and not final["runtimeEligible"]
    evidence.update({"K3_B": "PASS", "verdict": "K3_ART_APPROVED"})
    assert audit.resolve_chain(report,evidence)["status"] == "K3_ART_APPROVED"
    evidence["K2_K3"] = "UNKNOWN"
    assert audit.resolve_chain(report,evidence)["status"] == "CHAIN_NOT_VERIFIED"


def test_finalization_rechecks_report_hashes_before_writing_verdict(tmp_path):
    output = tmp_path/"chain"
    report = audit.prepare(output)
    path = tmp_path/"outgoing.json"
    path.write_text(json.dumps(review(report)))
    report["BRgbaSha256"] = "stale"
    (output/"landmark-report.json").write_text(json.dumps(report))
    with pytest.raises(ValueError,match="stale"):
        audit.finalize(output,path)
    assert not (output/"final-verdict.json").exists()


def test_finalization_cannot_ignore_changed_actual_k3(tmp_path,monkeypatch):
    output = tmp_path/"chain"
    report = audit.prepare(output)
    path = tmp_path/"outgoing.json"
    path.write_text(json.dumps(review(report)))
    original_digest = audit.digest
    monkeypatch.setattr(audit,"digest",lambda path: "changed" if path == audit.CANDIDATE/"K3.png" else original_digest(path))
    with pytest.raises(ValueError,match="K3 changed"):
        audit.finalize(output,path)
    assert not (output/"final-verdict.json").exists()
