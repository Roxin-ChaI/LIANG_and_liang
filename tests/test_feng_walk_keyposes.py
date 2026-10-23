"""Structural gates are not user visual approval of the walking artwork."""
import json
import pytest
from PIL import Image
from tools.prepare_feng_walk_keyposes import ROOT, OUT, ATLAS, prepare, sha


def test_reference_is_exact_formal_idle():
    idle = Image.open(OUT / "canonical-idle.png")
    atlas = Image.open(ATLAS).convert("RGBA")
    assert idle.mode == "RGBA" and idle.size == (192,208)
    assert idle.tobytes() == atlas.crop((0,0,192,208)).tobytes()
    assert idle.getbbox() == (44,4,148,204)


def test_scaffold_is_only_nearest_neighbour_reference_not_new_art():
    target = Image.open(OUT / "edit-target-four-idles.png")
    reference = Image.open(OUT / "canonical-idle.png").resize((768,832), Image.Resampling.NEAREST)
    for i in range(4):
        x,y=(i%2)*768,(i//2)*832
        assert target.crop((x,y,x+768,y+832)).tobytes() == reference.tobytes()


def test_protected_sources_unchanged_and_review_pending():
    record=json.loads((OUT/"source-manifest.json").read_text())
    assert record["frameCount"] == 4
    assert record["userApproval"] == "PENDING" and not record["runtimeIntegrated"]
    assert record["sourceOrder"] == ["N-contact", "N-support-F-passing", "F-contact", "F-support-N-passing"]
    for path,digest in record["sources"].items():
        assert sha(ROOT/path) == digest


def test_preparation_refuses_to_overwrite(tmp_path):
    target=tmp_path/"new"
    prepare(target)
    before={p.name:sha(p) for p in target.iterdir()}
    with pytest.raises(FileExistsError):
        prepare(target)
    assert before == {p.name:sha(p) for p in target.iterdir()}
