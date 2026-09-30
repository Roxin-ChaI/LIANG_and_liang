from copy import deepcopy

import pytest

from tools import review_gu_feng_entry_chain as chain
from tools.prepare_transition_animation_candidate import digest


def test_full_chain_exposes_final_failed_link_without_erasing_morph_approval():
    report = chain.assess()
    assert len(report["frames"]) == 13
    assert len(report["pairs"]) == 12
    assert report["morphStaticPass"]
    assert not report["entryStaticPass"]
    assert report["status"] == "VISUAL_QA_FAIL"
    assert report["blockingPairs"] == ["E3_Idle B"]
    assert not report["runtimeIntegrationAllowed"]
    assert all(all(checks.values()) for checks in report["frameChecks"].values())
    assert all(pair["baselineDelta"] == 0 for pair in report["pairs"].values())


def test_visual_failure_cannot_be_overridden_by_matching_landmarks():
    report = chain.assess()
    assert report["pairs"]["E3_Idle B"]["headSizeDelta"] == [-1, -1]
    assert not chain.verdict(report["pairs"])["fullChainApproved"]
    missing = deepcopy(report["pairs"])
    del missing["E3_Idle B"]
    with pytest.raises(KeyError):
        chain.verdict(missing)


def test_source_hashes_are_required_for_static_review(monkeypatch):
    derived = dict(chain.DERIVED)
    path, _ = derived["E3"]
    derived["E3"] = (path, "0" * 64)
    monkeypatch.setattr(chain, "DERIVED", derived)
    with pytest.raises(ValueError, match="reviewed E3 changed"):
        chain.frames()


def test_evidence_export_is_read_only_on_sources_and_refuses_overwrite(tmp_path):
    images, paths = chain.frames()
    before = {name: digest(path) for name, path in paths.items()}
    report = chain.write(tmp_path / "qa")
    assert report["status"] == "VISUAL_QA_FAIL"
    assert (tmp_path / "qa/contact-sheet.png").exists()
    assert (tmp_path / "qa/contact-sheet-nearest3x.png").exists()
    assert len(list((tmp_path / "qa").glob("*-overlay.png"))) == 12
    assert {name: digest(path) for name, path in paths.items()} == before
    with pytest.raises(ValueError, match="refuse to overwrite"):
        chain.write(tmp_path / "qa")
