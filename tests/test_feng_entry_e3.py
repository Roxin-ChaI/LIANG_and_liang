import json
from copy import deepcopy

from tools.gate_feng_entry_e3 import REVIEW,audit,resolve
from tools.manual_feng_entry_e3 import construct,assess


def test_e3_local_pixels_are_valid_but_not_visual_approval():
    image,_=construct()
    report=assess(image)
    assert report["technicalPass"],report["checks"]
    assert report["landmark"]["headSize"]==[50,55]
    assert report["landmark"]["baselineY"]==203
    assert not report["entryApproved"]


def test_target_leg_volume_gap_and_endpoint_failure_are_preserved():
    r=audit()
    assert r["opaqueLegWidthsByRow"]["E3"]["150"]==[13,13]
    assert r["opaqueLegWidthsByRow"]["B"]["150"]==[21,25]
    verdict=resolve(r,json.loads(REVIEW.read_text()))
    assert verdict["status"]=="ENTRY_QA_FAIL"
    assert verdict["visualPairPass"]=={"E2_E3":True,"E3_B":False}
    assert not verdict["fullChainAllowed"]


def test_hash_or_semantic_failure_never_approves_final_cut():
    r=audit();review=json.loads(REVIEW.read_text())
    stale=deepcopy(review);stale["E3Sha256"]="stale"
    assert not resolve(r,stale)["entryApproved"]
    unknown=deepcopy(review);unknown["pairs"]["E3_B"]["checks"]["pantsVolume"]="NOT_PROVEN"
    assert not resolve(r,unknown)["entryApproved"]
