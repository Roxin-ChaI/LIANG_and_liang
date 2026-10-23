"""Pairwise phase and frozen-key safeguards for the eight-frame Feng walk."""
import json
import pytest
import numpy as np
from PIL import Image
from tools.prepare_feng_walk_eight import OUT, KEYS, PAIRS, prepare, sha, verify_approved_keys


def test_keys_are_approved_and_all_frozen_hashes_match():
    assert verify_approved_keys()["userApproval"]=="APPROVED"


def test_pairwise_sequence_includes_wraparound_without_reversing():
    s=json.loads((OUT/"sequence-spec.json").read_text())
    assert PAIRS==[(1,2),(2,3),(3,4),(4,1)]
    assert [m["frame"] for m in s["mapping"]]==list(range(1,9))
    assert [m["key"] for m in s["mapping"][::2]]==[1,2,3,4]
    assert [(m["fromKey"],m["toKey"]) for m in s["mapping"][1::2]]==PAIRS
    assert s["durationMs"]==[140]*8 and s["slowDurationMs"]==[450]*8
    assert not s["runtimeIntegrated"] and s["userApproval"]=="PENDING"
    assert s["frozenSourceReview"]==sha(KEYS/"review-status.json")


def test_references_preserve_exact_key_pixels():
    for i in range(1,5):
        key=Image.open(KEYS/"attempt-3-review"/f"pose-{i:02d}.png")
        reference=Image.open(OUT/f"key-{i:02d}-4x.png")
        assert reference.tobytes()==key.resize((768,832),Image.Resampling.NEAREST).tobytes()


def test_preparation_cannot_overwrite_review_work(tmp_path):
    folder=tmp_path/"candidate"
    prepare(folder)
    before={p.name:sha(p) for p in folder.iterdir()}
    with pytest.raises(FileExistsError):
        prepare(folder)
    assert before=={p.name:sha(p) for p in folder.iterdir()}


def test_eight_frame_order_keeps_approved_keys_byte_identical():
    strip=Image.open(OUT/"review/feng-running-right.png")
    assert strip.mode=="RGBA" and strip.size==(1536,208)
    frames=[Image.open(OUT/"review"/f"right-{i:02d}.png") for i in range(1,9)]
    assert len({f.tobytes() for f in frames})==8
    for i,f in enumerate(frames):
        assert f.tobytes()==strip.crop((192*i,0,192*(i+1),208)).tobytes()
        if i%2==0:
            key=Image.open(KEYS/"attempt-3-review"/f"pose-{i//2+1:02d}.png")
            assert f.tobytes()==key.tobytes()


def test_native_output_has_hard_alpha_clear_rgb_and_ground_contact():
    for i in range(1,9):
        im=Image.open(OUT/"review"/f"right-{i:02d}.png")
        a=np.array(im)
        assert im.mode=="RGBA" and im.size==(192,208)
        assert set(np.unique(a[:,:,3]))<={0,255}
        assert not np.any(a[a[:,:,3]==0,:3])
        x,y,r,b=im.getbbox()
        assert x>=2 and y>=2 and r<=190 and b==204


def test_packager_rejects_missing_and_duplicate_frames():
    from tools.build_feng_walk_eight import assemble
    im=Image.new("RGBA",(192,208))
    with pytest.raises(ValueError,match="Exactly four"):
        assemble([im]*4,{2:im})
    with pytest.raises(ValueError,match="duplicate"):
        assemble([im]*4,{i:im for i in [2,4,6,8]})


def test_original_normalization_uses_same_scale_and_records_overshoot():
    from tools.build_feng_walk_eight import normalized_source, SCALE
    record=json.loads((OUT/"review/validation.json").read_text())
    assert record["keyFramesPixelIdentical"]
    assert [p["outsideNeighbourHeight"] for p in record["pairs"]]==[0,3,4,0]
    for m in record["newFrameMetrics"]:
        i=m["frame"]
        expected,_=normalized_source(OUT/m["source"],i)
        assert m["commonScale"]==SCALE
        assert expected.tobytes()==Image.open(OUT/"review"/f"right-{i:02d}.png").tobytes()


@pytest.mark.parametrize("name,delay",[("preview.gif",140),("preview-slow.gif",450),("preview-native.gif",140),("idle-comparison.gif",140)])
def test_eight_frame_gifs_keep_order_and_uniform_timing(name,delay):
    im=Image.open(OUT/"review"/name)
    assert im.n_frames==8 and im.info["loop"]==0
    for i in range(8):
        im.seek(i);assert im.info["duration"]==delay


def test_completed_evidence_cannot_be_overwritten():
    from tools.build_feng_walk_eight import build
    with pytest.raises(FileExistsError):
        build()


def test_r2_changes_only_requested_inbetweens_and_keeps_strip_order():
    strip=Image.open(OUT/"review-r2/feng-running-right.png")
    assert strip.mode=="RGBA" and strip.size==(1536,208)
    for i in range(1,9):
        frame=Image.open(OUT/"review-r2"/f"right-{i:02d}.png")
        assert frame.tobytes()==strip.crop(((i-1)*192,0,i*192,208)).tobytes()
        previous=Image.open(OUT/"review"/f"right-{i:02d}.png")
        assert (frame.tobytes()==previous.tobytes()) == (i not in (4,6))
        pixels=np.array(frame)
        assert set(np.unique(pixels[:,:,3]))<={0,255}
        assert not np.any(pixels[pixels[:,:,3]==0,:3])
        assert frame.getbbox()[3]==204


def test_r2_provenance_is_reproducible_without_independent_fit_scaling():
    from tools.build_feng_walk_eight import normalized_source, SCALE
    report=json.loads((OUT/"review-r2/validation.json").read_text())
    assert [p["outsideNeighbourHeight"] for p in report["pairs"]]==[0,3,4,0]
    for metric in report["newFrameMetrics"]:
        i=metric["frame"]
        source=OUT/(f"source-{i:02d}-r2.png" if i in (4,6) else f"source-{i:02d}.png")
        assert metric["sourceSha256"]==sha(source)
        assert metric["commonScale"]==SCALE
        frame,_=normalized_source(source,i,belt_x=metric["beltCentreX"])
        assert frame.tobytes()==Image.open(OUT/"review-r2"/f"right-{i:02d}.png").tobytes()


@pytest.mark.parametrize("name,delay",[("preview.gif",140),("preview-slow.gif",450),("preview-native.gif",140),("idle-comparison.gif",140)])
def test_r2_gifs_preserve_eight_frames_and_timing(name,delay):
    im=Image.open(OUT/"review-r2"/name)
    assert im.n_frames==8 and im.info["loop"]==0
    for i in range(8):
        im.seek(i)
        assert im.info["duration"]==delay


@pytest.mark.parametrize("kwargs",[{"sources":{}},{"belt_centres":{}},{"sources":{2:OUT/"source-02.png"}}])
def test_revision_sources_cannot_silently_fall_back(tmp_path,kwargs):
    from tools.build_feng_walk_eight import build
    with pytest.raises(ValueError,match="Explicit complete"):
        build(tmp_path/"invalid",**kwargs)
    assert not (tmp_path/"invalid").exists()


def test_r2_visual_failure_is_not_promoted_by_structural_success():
    report=json.loads((OUT/"review-r2/self-review.json").read_text())
    assert report["verdict"]=="REWORK_REQUIRED"
    assert report["failedFrames"]==[4,6]
    assert report["userApproval"]=="PENDING"
    assert report["appTest"]=="NOT_TESTED"
    assert not report["runtimeIntegrated"]
    assert report["evidenceSha256"]["contact.png"]==sha(OUT/"review-r2/contact.png")


def test_r2_evidence_cannot_be_overwritten():
    from tools.build_feng_walk_eight import build
    with pytest.raises(FileExistsError):
        build(OUT/"review-r2")
