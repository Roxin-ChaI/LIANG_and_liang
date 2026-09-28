import copy

from tools.validate_transition_ack_trace import validate


def example(direction="gu_to_feng"):
    """Synthetic validator fixture only, never used as live QA evidence."""
    count = 10 if direction == "gu_to_feng" else 8
    events = []
    for index in range(count):
        base = {"operationToken": "op", "transitionId": direction}
        events.extend([{**base, "type": "state", "visualMode": "TRANSITIONING", "frameIndex": index},
                       {**base, "type": "renderer", "visualMode": "TRANSITIONING", "transitionFrame": index},
                       {**base, "type": "transition-dwell-start", "frame": index, "configuredDwellMs": 140},
                       {**base, "type": "transition-dwell-end", "frame": index, "elapsedMs": 140.2}])
    events.append({"type": "transition-complete", "operationToken": "op", "transitionId": direction,
                   "form": "feng" if count == 10 else "gu", "normalState": "running"})
    return events


def test_complete_sequences_do_not_imply_artwork_pass():
    for direction in ("gu_to_feng", "feng_to_gu"):
        result = validate(example(direction))
        assert result["status"] == "PAINT_DWELL_COMPLETION_PASS"
        assert result["operations"][0]["restoredState"] == "running"
        assert result["visualArtworkApproved"] is False


def test_frame4_missing_ack_or_timer_is_not_pass():
    for kind in ("renderer", "transition-dwell-start", "transition-dwell-end"):
        trace = [e for e in example() if not (e["type"] == kind
                 and e.get("transitionFrame", e.get("frame")) == 4)]
        assert validate(trace)["status"] == "PAINT_DWELL_COMPLETION_FAIL"


def test_duplicate_completion_short_dwell_and_renderer_error_fail():
    original = example()
    duplicate = copy.deepcopy(original) + [original[-1]]
    short = copy.deepcopy(original)
    next(e for e in short if e["type"] == "transition-dwell-end")["elapsedMs"] = 80
    for trace in (duplicate, short, original + [{"type": "renderer-error", "message": "failure"}], []):
        assert validate(trace)["status"] == "PAINT_DWELL_COMPLETION_FAIL"


def test_timer_before_paint_or_completion_before_last_dwell_fails():
    swapped = example()
    swapped[1], swapped[2] = swapped[2], swapped[1]
    early = example()
    early[-1], early[-2] = early[-2], early[-1]
    assert validate(swapped)["status"] == "PAINT_DWELL_COMPLETION_FAIL"
    assert validate(early)["status"] == "PAINT_DWELL_COMPLETION_FAIL"
