"""Pairwise phase and frozen-key safeguards for the eight-frame Feng walk."""
import json
import pytest
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
