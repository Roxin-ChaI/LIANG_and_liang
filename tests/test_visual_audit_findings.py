import json
import pytest
from PIL import Image

from tools.audit_standalone_state_races import visual_outcome
from tools.compile_visual_findings import ROOT, dark_proxy, source_measurements


def test_state_race_summary_ignores_old_completion():
    old = {"type": "transition-complete", "operationToken": "old"}
    newest = {"type": "renderer", "row": 8, "form": "feng"}
    result = visual_outcome([old, {"type": "schedule"}, newest], after=1)
    assert result["lastRenderer"] == newest
    assert result["completions"] == []


def test_dark_proxy_does_not_use_cyan_effect_as_body_size():
    image = Image.new("RGBA", (10, 10))
    image.putpixel((0, 0), (0, 200, 255, 255))
    image.putpixel((9, 9), (255, 255, 255, 100))
    image.putpixel((3, 4), (10, 20, 40, 255))
    assert dark_proxy(image) == (3, 4, 4, 5)


@pytest.mark.xfail(reason="V-01: frozen Gu work rows use foot baseline 198 rather than Idle 203")
def test_gu_grounded_work_rows_share_idle_baseline():
    rows = source_measurements()["forms"]["gu"]["rows"]
    expected = rows["idle"]["baselines"][0]
    for name in ("waving", "failed", "waiting", "running", "review"):
        assert rows[name]["baselines"] == [expected] * len(rows[name]["baselines"])


def test_committed_pair_coverage_has_every_ordered_row_pair():
    coverage = json.loads((ROOT / "docs/visual-audit/v0.1.0/findings/state-pair-coverage.json").read_text())
    for form in ("gu", "feng"):
        pairs = coverage[form]["pairs"]
        assert len({(item["from"], item["to"]) for item in pairs}) == 81
        assert not any(item["empty"] or item["touchesWindowEdge"] for item in pairs)
