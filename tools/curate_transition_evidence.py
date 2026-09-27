#!/usr/bin/env python3
"""Select compact QA2 transition evidence without committing raw temporary traces."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.audit_standalone_transitions import changed_pixel_count


def curate(raw: Path, output: Path) -> dict:
    trace = json.loads((raw / "transition-trace.json").read_text())
    output.mkdir(parents=True, exist_ok=True)
    summary = {"captureKind": trace["captureKind"], "build": trace["build"],
               "timingNote": "frame-gated capture changes pacing; ungated timings measured separately",
               "ungatedTimings": trace["ungatedTimings"], "scenarios": []}
    for scenario in trace["scenarios"]:
        label = scenario["label"]
        for suffix in ("sheet.png", "window-recording.gif"):
            shutil.copy2(raw / f"{label}-{suffix}", output / f"{label}-{suffix}")
        for record in (scenario["before"], scenario["frames"][0],
                       scenario["frames"][-1], scenario["after"]):
            source = Path(record["file"])
            shutil.copy2(source, output / source.name)
        summary["scenarios"].append({
            "label": label, "source": scenario["source"], "target": scenario["target"],
            "mode": scenario["mode"], "frameCount": scenario["frameCount"],
            "frameTimestamps": [item["observedAt"] for item in scenario["frames"]],
            "gatedIntervalsMs": scenario["observedIntervalsMs"],
            "lastFrameToCompletionMs": scenario["lastFrameToCompletionMs"],
            "firstFrameBounds": scenario["frames"][0]["geometry"]["bbox"],
            "lastFrameBounds": scenario["frames"][-1]["geometry"]["bbox"],
            "beforeBounds": scenario["before"]["geometry"]["bbox"],
            "afterBounds": scenario["after"]["geometry"]["bbox"],
            "beforeToFirstChangedPixels": changed_pixel_count(Path(scenario["before"]["file"]),
                                                               Path(scenario["frames"][0]["file"])),
            "lastToAfterChangedPixels": changed_pixel_count(Path(scenario["frames"][-1]["file"]),
                                                              Path(scenario["after"]["file"])),
        })
    (output / "transition-timeline.json").write_text(json.dumps(summary, indent=2) + "\n")
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = curate(args.raw, args.output)
    print(json.dumps({"scenarios": [entry["label"] for entry in result["scenarios"]],
                      "output": str(args.output)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
