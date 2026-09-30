from copy import deepcopy

import pytest

from tools.review_f0_morph_chain import assess, frames, historical_review, verdict, write


def test_actual_chain_numeric_pass_never_overrides_visual_failure():
    report = assess()
    assert all(p["numericPass"] and p["reviewFresh"] for p in report["pairs"].values())
    assert [p["visualPass"] for p in report["pairs"].values()] == [True, True, True, True, False]
    assert report["status"] == "MANUAL_BRIDGE_QA_FAIL"
    assert not report["F0ArtApproved"] and not report["F0ToIdleAuditAllowed"]


def test_stale_review_or_missing_segment_blocks_chain():
    pairs = deepcopy(assess()["pairs"])
    for p in pairs.values():
        p["visualPass"] = True
    assert verdict(pairs)["F0ArtApproved"]
    pairs["KF2_F0"]["reviewFresh"] = False
    assert not verdict(pairs)["F0ArtApproved"]
    pairs.pop("KF2_F0")
    assert not verdict(pairs)["F0ArtApproved"]


def test_historical_source_hash_must_match():
    images, _ = frames()
    review = assess()["pairs"]["K3_KB1"]["visualEvidence"]
    assert historical_review(review, images["K3"], images["KB1"], "K3_KB1_STATIC_PASS")["visualPass"]
    review["sourceRgbaSha256"] = "invalid"
    assert not historical_review(review, images["K3"], images["KB1"], "K3_KB1_STATIC_PASS")["visualPass"]


def test_contact_sheet_evidence_cannot_overwrite_sources(tmp_path):
    before, _ = frames()
    output = tmp_path / "qa"
    assert write(output)["status"] == "MANUAL_BRIDGE_QA_FAIL"
    with pytest.raises(ValueError, match="overwrite"):
        write(output)
    after, _ = frames()
    assert all(before[n].tobytes() == after[n].tobytes() for n in before)
