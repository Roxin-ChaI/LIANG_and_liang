import json

import pytest

from tools import rank_feng_endpoint_candidates as rank


def test_shortlist_is_three_actual_unmodified_formal_atlas_cells():
    report, cells = rank.collect()
    assert report["shortlistCount"] == 3
    assert len(cells) == 5
    assert [(r["row"], r["frame"]) for r in report["shortlist"]] == [(8, 4), (1, 6), (3, 0)]
    assert all(r["baselineY"] == 203 and r["registrationX"] == 96 for r in report["shortlist"])
    assert not report["candidateSourceCellsModified"]
    assert report["approvedF0"] is None


def test_shortlist_contains_head_and_body_guides_but_no_auto_art_approval():
    report, _ = rank.collect()
    for entry in report["shortlist"]:
        assert entry["headBboxGuideApprox"]
        assert entry["headCenterGuideApprox"]
        assert entry["bodyBbox"]
        assert entry["armPose"] == "INDEPENDENT_VISUAL_REVIEW_REQUIRED"


def test_focused_contact_refuses_overwrite(tmp_path):
    output = tmp_path / "ranking"
    assert rank.prepare(output)["shortlistCount"] == 3
    assert sorted(p.name for p in output.iterdir()) == ["candidate-technical.json", "three-candidates-contact.png", "three-candidates-nearest3x.png"]
    with pytest.raises(ValueError, match="overwrite"):
        rank.prepare(output)


def test_actual_independent_review_blocks_static_chain():
    report, _ = rank.collect()
    review = json.loads((rank.QA / "independent-review.json").read_text())
    result = rank.resolve(report, review)
    assert result["status"] == "NO_EXISTING_FENG_ENDPOINT"
    assert result["independentReviewFresh"]
    assert not result["selectedStaticChainAllowed"]
    assert not result["newBridgeAllowed"]


def test_stale_or_conflicting_review_cannot_qualify(tmp_path):
    output = tmp_path / "ranking"
    report = rank.prepare(output)
    review = json.loads((rank.QA / "independent-review.json").read_text())
    assert rank.resolve(report, {**review, "sourceAtlasSha256": "stale"})["status"] == "VISUAL_RANKING_NOT_VERIFIED"
    forged = json.loads(json.dumps(review))
    forged["rankedCandidates"][0]["qualified"] = True
    assert rank.resolve(report, forged)["status"] == "VISUAL_RANKING_NOT_VERIFIED"
    (output / "independent-review.json").write_text(json.dumps(review))
    assert rank.finalize(output)["status"] == "NO_EXISTING_FENG_ENDPOINT"
