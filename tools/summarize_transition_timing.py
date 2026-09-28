#!/usr/bin/env python3
"""Separate measured publish/paint acknowledgment latency from transition dwell."""
import argparse
import json
from pathlib import Path


def summarize(trace: dict) -> dict:
    cases = []
    for case in trace["ungatedTimings"]:
        events = case.get("dwellDiagnostics", [])
        starts = [e for e in events if e["type"] == "transition-dwell-start"]
        ends = [e for e in events if e["type"] == "transition-dwell-end"]
        def span(values):
            values = [value for value in values if value is not None]
            return [min(values), max(values)] if values else None
        cases.append({"transitionId": case["transitionId"],
                      "frameTimestamps": case["frameTimestamps"],
                      "rendererIntervalMs": span(case["observedIntervalsMs"]),
                      "publishToPaintAckMs": span(e.get("publishToAckMs") for e in starts),
                      "ackToTimerFireMs": span(e.get("elapsedMs") for e in ends),
                      "visibility": sorted({e.get("visibility", "unknown") for e in starts}),
                      "configuredDwellMs": sorted({e["configuredDwellMs"] for e in starts}),
                      "ackCount": len(starts), "timerCount": len(ends),
                      "diagnostics": events})
    return {"captureKind": "live ungated Electron IPC and monotonic timer trace; not optical timing",
            "status": "DIAGNOSED_NOT_FIXED", "cases": cases}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trace", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = summarize(json.loads(args.trace.read_text()))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"output": str(args.output), "status": result["status"]}))


if __name__ == "__main__":
    main()
