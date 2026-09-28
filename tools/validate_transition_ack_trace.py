"""Validate live paint → dwell → completion, never infer visual art approval."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

COUNTS = {"gu_to_feng": 10, "feng_to_gu": 8}


def validate(events: list[dict]) -> dict:
    errors = [e for e in events if e.get("type") in (
        "renderer-error", "renderer-gone", "renderer-load-failed", "frame-capture-error", "test-error")]
    tokens = list(dict.fromkeys(e.get("operationToken") for e in events
                               if e.get("type") == "state" and e.get("visualMode") == "TRANSITIONING"))
    operations = []
    for token in tokens:
        owned = [e for e in events if e.get("operationToken") == token]
        complete = [e for e in owned if e.get("type") == "transition-complete"]
        direction = next(e["transitionId"] for e in owned if e.get("transitionId") in COUNTS)
        painted = list(dict.fromkeys(e.get("transitionFrame") for e in owned
                                     if e.get("type") == "renderer" and e.get("visualMode") == "TRANSITIONING"))
        starts = [e for e in owned if e.get("type") == "transition-dwell-start"]
        ends = [e for e in owned if e.get("type") == "transition-dwell-end"]
        expected = list(range(COUNTS[direction]))
        ordered = True
        previous_end = -1
        for index in expected:
            def locate(kind, field):
                return next((n for n, e in enumerate(owned) if e.get("type") == kind
                             and e.get(field) == index), -1)
            paint_at = locate("renderer", "transitionFrame")
            start_at = locate("transition-dwell-start", "frame")
            end_at = locate("transition-dwell-end", "frame")
            ordered &= previous_end < paint_at < start_at < end_at
            previous_end = end_at
        completed_after_dwell = bool(complete) and owned.index(complete[0]) > previous_end
        valid = (painted == expected and [e.get("frame") for e in starts] == expected
                 and [e.get("frame") for e in ends] == expected and len(complete) == 1
                 and ordered and completed_after_dwell
                 and complete[0].get("form") == direction.split("_to_")[1]
                 and all(e.get("configuredDwellMs") == 140 for e in starts)
                 and all(e.get("elapsedMs", -1) >= 139 for e in ends))
        operations.append({"operationToken": token, "direction": direction,
                           "orderedPaintedFrames": painted, "dwellFrames": [e.get("frame") for e in ends],
                           "completionCount": len(complete), "pass": valid,
                           "finalForm": complete[0].get("form") if complete else None,
                           "restoredState": complete[0].get("normalState") if complete else None,
                           "frame4PaintObserved": 4 in painted})
    return {"status": "PAINT_DWELL_COMPLETION_PASS" if operations and not errors
            and all(e["pass"] for e in operations) else "PAINT_DWELL_COMPLETION_FAIL",
            "visualArtworkApproved": False, "errors": errors, "operations": operations}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trace", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    value = json.loads(args.trace.read_text())
    result = validate(value if isinstance(value, list) else value["events"])
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"status": result["status"], "operations": len(result["operations"])}))
    return 0 if result["status"].endswith("_PASS") else 1


if __name__ == "__main__":
    raise SystemExit(main())
