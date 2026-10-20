"""Candidate guardrails; no automatic assertion of user art approval."""
import hashlib
import json
import numpy as np
from PIL import Image

from tools.prepare_feng_failed_r3 import OUT, FENG, GU, ROOT
from tools.build_animation_review import cell


def test_references_match_current_approved_sources():
    manifest = json.loads((OUT / "source-manifest.json").read_text())
    for name, digest in manifest["sources"].items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest
    idle = cell(Image.open(FENG).convert("RGBA"), 0, 0)
    assert Image.open(OUT / "canonical-idle.png").tobytes() == idle.tobytes()
    assert idle.size == (192, 208)
    assert idle.getbbox() == (44, 4, 148, 204)


def test_reference_does_not_claim_runtime_or_art_approval():
    manifest = json.loads((OUT / "source-manifest.json").read_text())
    assert manifest["userApproval"] == "PENDING"
    assert not manifest["runtimeIntegrated"]
    assert manifest["frameCount"] == 8
    assert Image.open(OUT / "gu-motion-reference.gif").n_frames == 8


def test_official_atlas_freeze():
    assert hashlib.sha256(FENG.read_bytes()).hexdigest() == (
        "d697e573268b66cb0f6a062480ec87c8c11712ca34b57f8c2fc0a97ed6e2164a")
