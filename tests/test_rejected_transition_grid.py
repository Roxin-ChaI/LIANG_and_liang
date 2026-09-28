"""Actual failed generated sources must not be promoted into runtime frames."""
import hashlib
import json

from PIL import Image
import pytest

from tools.prepare_transition_animation_candidate import ENDPOINT_ROOT, harden_alpha, prepare, register

ROOT = ENDPOINT_ROOT.parent / "transition-full"


def test_reverse_generation_cannot_hide_cut_shoes_by_integer_translation(tmp_path):
    source = ROOT / "sources/feng-to-gu-generated-retry.png"
    before = hashlib.sha256(source.read_bytes()).hexdigest()
    output = tmp_path / "must-not-exist"
    with pytest.raises(ValueError, match="grid cell touches edge"):
        prepare(source, "feng_to_gu", output)
    assert not output.exists()
    assert before == hashlib.sha256(source.read_bytes()).hexdigest()
    with Image.open(source) as original:
        grid = original.resize((768, 416), Image.Resampling.NEAREST)
    for index in range(8):
        x, y = (index % 4) * 192, (index // 4) * 208
        cell, _ = harden_alpha(grid.crop((x, y, x + 192, y + 208)))
        with pytest.raises(ValueError, match="grid cell touches edge"):
            register(cell)


def test_reverse_diagnostics_are_not_playable_frames_or_live_evidence():
    output = ROOT / "feng-to-gu-rejected-grid"
    report = json.loads((output / "grid-diagnosis.json").read_text())
    review = json.loads((output / "independent-review.json").read_text())
    assert report["sourceSha256"] == hashlib.sha256((ROOT / "sources/feng-to-gu-generated-retry.png").read_bytes()).hexdigest()
    assert len(report["cells"]) == 8 and all(c["touchesCellEdge"] for c in report["cells"])
    assert all(len(c["connectedComponentSizes8"]) == 3 for c in report["cells"][4:])
    assert report["playableFramesEmitted"] == 0 and not report["runtimeEligible"]
    assert review["status"] == "VISUAL_QA_FAIL" and review["idleActualAppGate"] == "NOT_READY"
    assert not review["runningApproved"] and not (output / "frames").exists()
