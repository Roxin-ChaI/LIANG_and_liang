"""Structural checks do not grant human art approval."""
import json
import pytest
from PIL import Image

from tools.prepare_gu_drag_suspended import OUT, ROOT, GU, prepare, sha, assert_unapproved
from tools.build_animation_review import cell


def test_references_are_exact_idle_pixels():
    canonical = cell(Image.open(GU).convert("RGBA"), 0, 0)
    assert Image.open(OUT / "canonical-idle.png").tobytes() == canonical.tobytes()
    assert canonical.getbbox() == (54, 4, 122, 204)
    enlarged = Image.open(OUT / "idle-reference-4x.png")
    assert enlarged.resize((192, 208), Image.Resampling.NEAREST).tobytes() == canonical.tobytes()


def test_source_hashes_unchanged_and_scope_is_only_gu_right():
    manifest = json.loads((OUT / "source-manifest.json").read_text())
    for name, digest in manifest["sources"].items():
        assert sha(ROOT / name) == digest
    assert manifest["scope"] == "gu-running-right-only"
    assert manifest["frameCount"] == 8
    assert manifest["userApproval"] == "PENDING"
    assert not manifest["runtimeIntegrated"]
    assert "feng-look-intermediates" in manifest["deferred"]


def test_approval_freeze_guard(tmp_path):
    (tmp_path / "review-status.json").write_text('{"generatorLocked":true}')
    with pytest.raises(RuntimeError, match="frozen"):
        assert_unapproved(tmp_path)
