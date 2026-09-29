import json
from pathlib import Path

import pytest
from PIL import Image

from tools import audit_f0_candidate as gate


def test_actual_generated_edit_does_not_become_accepted_f0():
    report = gate.audit()
    assert report["status"] == "F0_CANDIDATE_REJECTED"
    assert report["candidateCanvas"] == [1205, 1305]
    assert not report["checks"]["native192x208"]
    assert not report["approvedF0"]
    assert not report["F0Written"]
    assert not report["nearestNeighborDownsampleAllowedAsRepair"]
    assert not (gate.OUT / "F0.png").exists()
    assert not gate.resolve(report, {"reviewedCandidateSha256":report["candidateSha256"],
                                     "reviewer":"FORGED", "verdict":"VISUAL_PASS"})["eligibleForF0Promotion"]


def test_native_geometry_is_only_a_visual_review_gate(tmp_path: Path):
    path = tmp_path / "native.png"
    image = Image.new("RGBA", (192, 208), (0, 0, 0, 0))
    image.putpixel((96, 203), (1, 2, 3, 255))
    image.save(path)
    report = gate.audit(path)
    assert report["status"] == "MANUAL_VISUAL_QA_REQUIRED"
    assert not report["approvedF0"]


def test_report_never_overwrites(tmp_path: Path):
    output = tmp_path / "qa"
    assert gate.prepare(output=output)["status"] == "F0_CANDIDATE_REJECTED"
    with pytest.raises(ValueError, match="overwrite"):
        gate.prepare(output=output)


def test_actual_independent_review_fresh_and_rejects(tmp_path: Path):
    output = tmp_path / "qa"
    gate.prepare(output=output)
    review = json.loads((gate.QA / "independent-review.json").read_text())
    (output / "independent-review.json").write_text(json.dumps(review))
    result = gate.finalize(output=output)
    assert result["status"] == "F0_CANDIDATE_REJECTED"
    assert result["independentReviewFresh"]
    assert not result["eligibleForF0Promotion"]
