"""Structural gates are not user visual approval of the walking artwork."""
import json
import pytest
import numpy as np
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


def test_repeated_leg_candidate_is_explicitly_rejected():
    record=json.loads((OUT/"attempt-1-review.json").read_text())
    assert record["status"] == "SELF_REJECTED"
    assert not record["runtimeIntegrated"]
    assert record["userApproval"] == "NOT_REQUESTED"
    assert len(record["visualFindings"]) == 3


def test_native_candidates_are_four_unique_hard_alpha_cells():
    frames=[Image.open(OUT/"attempt-3-review"/f"pose-{i:02d}.png") for i in range(1,5)]
    assert len({f.tobytes() for f in frames}) == 4
    for f in frames:
        assert f.mode == "RGBA" and f.size == (192,208)
        a=np.array(f)
        assert set(np.unique(a[:,:,3])) <= {0,255}
        assert not np.any(a[a[:,:,3]==0,:3])
        x0,y0,x1,y1=f.getbbox()
        assert x0>0 and y0>0 and x1<192 and y1==204


def test_shared_scale_reproduces_frames_without_per_pose_fitting():
    from tools.review_feng_walk_keyposes import HIPS, normalize
    raw=Image.open(OUT/"source-attempt-3.png")
    for i,hip in enumerate(HIPS):
        x,y=(i%2)*602,(i//2)*653
        expected,_=normalize(raw.crop((x,y,x+602,y+653)),hip)
        saved=Image.open(OUT/"attempt-3-review"/f"pose-{i+1:02d}.png")
        assert expected.tobytes() == saved.tobytes()


def test_height_regression_is_recorded_as_failure_not_hidden_by_scaling():
    record=json.loads((OUT/"attempt-3-review/validation.json").read_text())
    assert record["status"] == "SELF_REJECTED"
    assert record["heightRange"] >= 5
    assert not record["geometryGate"]["passed"]
    assert not record["visualGate"]["passed"]
    assert not record["nextStageAllowed"] and not record["runtimeIntegrated"]
    assert record["userApproval"] == "NOT_REQUESTED"
    assert len({m["sharedScale"] for m in record["metrics"]})==1


@pytest.mark.parametrize("name,duration",[("preview.gif",280),("preview-slow.gif",650),("idle-comparison.gif",400)])
def test_review_gifs_keep_four_phases_and_constant_duration(name,duration):
    im=Image.open(OUT/"attempt-3-review"/name)
    assert im.n_frames==4 and im.info["loop"]==0
    for i in range(4):
        im.seek(i)
        assert im.info["duration"]==duration


def test_completed_review_cannot_be_overwritten():
    from tools.review_feng_walk_keyposes import build
    with pytest.raises(FileExistsError,match="completed review"):
        build()
