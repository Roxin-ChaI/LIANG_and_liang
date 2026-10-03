import json
import hashlib
from tools.rework_action_candidates import OUT, ROOT


def test_full_trace_confirms_look_tear_predates_r2():
    report=json.loads((OUT/"diagnosis/rejected-r2-seams/trace.json").read_text())
    assert report["status"]=="VISUAL_QA_FAIL"
    assert len(report["look"])==16
    assert all(row["r1ToR2HandRoiChanged"]==0 for row in report["look"])
    assert all(row["r1BelowY74EqualsFixedUp"] for row in report["look"])
    assert report["failedOrdinalToPlannedRuntimeFrame"]==[1,4,5,8]
    assert report["dynamicPlaybackObserved"].startswith("NOT_VERIFIED")
    for path,sha in report["sourceHashes"].items():
        assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==sha
